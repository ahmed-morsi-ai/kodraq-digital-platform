"""Transactional, curriculum-scoped text ingestion; no embedding or provider calls."""

from dataclasses import dataclass
import hashlib
import json
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.track import Lesson, Track, TrackModule

MAX_TEXT_CHARACTERS = 2_000_000
MAX_CHUNKS = 10_000


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class TextChunk:
    content: str
    start_offset: int
    end_offset: int


def prepare_text(raw_text: str) -> tuple[str, str]:
    """Canonicalize encoding differences while preserving meaningful whitespace."""
    if not isinstance(raw_text, str):
        raise ValueError("Document text must be a string.")
    if len(raw_text) > MAX_TEXT_CHARACTERS:
        raise ValueError(f"Document exceeds {MAX_TEXT_CHARACTERS} characters.")
    normalized = unicodedata.normalize(
        "NFC", raw_text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    )
    if not normalized.strip():
        raise ValueError("Document text must not be empty.")
    if "\x00" in normalized:
        raise ValueError("Document text must not contain null characters.")
    try:
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    except UnicodeEncodeError as error:
        raise ValueError("Document text must contain valid Unicode.") from error
    return normalized, digest


def chunk_text(
    text: str, *, chunk_size: int = 1000, chunk_overlap: int = 150
) -> list[TextChunk]:
    """Split canonical text at paragraph, line, sentence, or word boundaries.

    Offsets are Python/PostgreSQL Unicode character positions, end-exclusive.
    Every source character is retained, including code indentation and whitespace.
    Overlap is exact; an unbroken token falls back to bounded character windows.
    """
    if not _is_integer(chunk_size) or not 1 <= chunk_size <= 20_000:
        raise ValueError("chunk_size must be an integer between 1 and 20000.")
    if not _is_integer(chunk_overlap) or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be an integer smaller than chunk_size.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Chunk text must not be empty.")
    if len(text) > MAX_TEXT_CHARACTERS:
        raise ValueError(f"Document exceeds {MAX_TEXT_CHARACTERS} characters.")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            minimum_end = start + max(chunk_overlap + 1, chunk_size // 2)
            for separator in ("\n\n", "\n", ". ", "? ", "! ", " ", "\t"):
                boundary = text.rfind(separator, minimum_end - len(separator), end)
                if boundary >= start and boundary + len(separator) >= minimum_end:
                    end = boundary + len(separator)
                    break
        chunks.append(TextChunk(text[start:end], start, end))
        if len(chunks) > MAX_CHUNKS:
            raise ValueError(
                f"Document exceeds {MAX_CHUNKS} chunks; increase chunk_size."
            )
        if end == len(text):
            break
        start = end - chunk_overlap
    return chunks


def _source_value(
    value: str | None, name: str, maximum: int, *, required: bool = False
):
    if value is None and not required:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or "\x00" in value
    ):
        raise ValueError(
            f"{name} must be nonblank text of at most {maximum} characters."
        )
    return value.strip()


def ingest_text(
    db: Session,
    *,
    raw_text: str,
    title: str,
    track_id: int | None = None,
    lesson_id: int | None = None,
    source_type: str = "text",
    file_name: str | None = None,
    file_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> Document:
    """Return the existing document on a scoped duplicate; the caller commits.

    The unique indexes arbitrate concurrent ingestions. A savepoint keeps document
    and chunk creation atomic without committing or rolling back unrelated work.
    The first successful ingestion retains its source metadata and chunk settings.
    This is an internal service; callers must authorize curriculum access first.
    """
    content, digest = prepare_text(raw_text)
    chunks = chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    title = _source_value(title, "title", 255, required=True)
    source_type = _source_value(source_type, "source_type", 32, required=True)
    file_name = _source_value(file_name, "file_name", 255)
    file_url = _source_value(file_url, "file_url", 1024)
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object.")
    try:
        metadata_copy = json.loads(json.dumps(metadata or {}, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ValueError("metadata must contain valid JSON values.") from error
    for identifier in (track_id, lesson_id):
        if identifier is not None and (not _is_integer(identifier) or identifier <= 0):
            raise ValueError("Track and lesson IDs must be positive integers.")
    if lesson_id is not None:
        lesson_track = db.scalar(
            select(TrackModule.track_id).join(Lesson).where(Lesson.id == lesson_id)
        )
        if lesson_track is None:
            raise LookupError("Lesson not found.")
        if track_id is not None and track_id != lesson_track:
            raise ValueError("Lesson does not belong to the specified track.")
        track_id = lesson_track
    if track_id is None:
        raise ValueError("A track or lesson is required.")
    if db.get(Track, track_id) is None:
        raise LookupError("Track not found.")

    with db.begin_nested():
        document_id = db.scalar(
            insert(Document)
            .values(
                track_id=track_id,
                lesson_id=lesson_id,
                title=title,
                source_type=source_type,
                file_name=file_name,
                file_url=file_url,
                raw_text=content,
                content_hash=digest,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                metadata_json=metadata_copy,
            )
            .on_conflict_do_nothing()
            .returning(Document.id)
        )
        if document_id is None:
            return db.scalars(
                select(Document).where(
                    Document.track_id == track_id,
                    Document.lesson_id == lesson_id,
                    Document.content_hash == digest,
                )
            ).one()
        db.add_all(
            [
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=index,
                    content=chunk.content,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    metadata_json={},
                    embedding=None,
                )
                for index, chunk in enumerate(chunks)
            ]
        )
        db.flush()
        return db.get(Document, document_id)
