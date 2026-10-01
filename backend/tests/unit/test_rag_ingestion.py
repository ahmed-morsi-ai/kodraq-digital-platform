from concurrent.futures import ThreadPoolExecutor
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import app
from app.models.document import Document, DocumentChunk
from app.models.track import Lesson, Track, TrackModule
from app.services import rag_ingestion as ingestion
from app.services.rag_ingestion import chunk_text, ingest_text, prepare_text


@pytest.fixture
def curriculum(db_session):
    tracks = [Track(name=f"RAG {uuid4().hex}", slug=uuid4().hex) for _ in range(2)]
    modules = [TrackModule(track=track, title="Module") for track in tracks]
    lessons = [
        Lesson(module=modules[0], title=f"Lesson {number}") for number in range(2)
    ]
    lessons.append(Lesson(module=modules[1], title="Other lesson"))
    db_session.add_all(tracks + modules + lessons)
    db_session.flush()
    return SimpleNamespace(tracks=tracks, modules=modules, lessons=lessons)


def ingest(db, curriculum, **kwargs):
    return ingest_text(
        db,
        **dict(
            {
                "track_id": curriculum.tracks[0].id,
                "raw_text": "A lesson on database transactions. " * 40,
                "title": "Transactions",
                "chunk_size": 150,
                "chunk_overlap": 30,
            },
            **kwargs,
        ),
    )


def test_canonical_text_hash_preserves_code_whitespace():
    original = "\ufeff  cafe\u0301\r\n    indented code\rnext\n"
    expected = "  caf\u00e9\n    indented code\nnext\n"
    content, digest = prepare_text(original)
    assert content == expected
    assert digest == hashlib.sha256(expected.encode()).hexdigest()
    assert prepare_text(expected) == (content, digest)
    assert prepare_text(expected + " ")[1] != digest
    assert prepare_text(expected.upper())[1] != digest


@pytest.mark.parametrize("value", [None, b"text", "", " \n\t", "a\x00b", "\ud800"])
def test_invalid_text_rejected(value):
    with pytest.raises(ValueError):
        prepare_text(value)


def test_text_and_chunk_limits(monkeypatch):
    monkeypatch.setattr(ingestion, "MAX_TEXT_CHARACTERS", 20)
    with pytest.raises(ValueError, match="exceeds"):
        prepare_text("a" * 21)
    with pytest.raises(ValueError, match="exceeds"):
        chunk_text("a" * 21)
    monkeypatch.setattr(ingestion, "MAX_CHUNKS", 3)
    with pytest.raises(ValueError, match="increase chunk_size"):
        chunk_text("abcdef", chunk_size=2, chunk_overlap=1)


@pytest.mark.parametrize(
    "size,overlap",
    [
        (0, 0),
        (-1, 0),
        (True, 0),
        (1.5, 0),
        (20_001, 0),
        (5, -1),
        (5, 5),
        (5, 6),
        (5, True),
        (5, 1.5),
    ],
)
def test_invalid_chunk_configuration(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("Some text", chunk_size=size, chunk_overlap=overlap)


@pytest.mark.parametrize(
    "content",
    [
        "x",
        "x" * 200,
        "words in a sentence. " * 20,
        "Paragraph one\n\nParagraph two\nLine three. " * 10,
        "\u0645\u0631\u062d\u0628\u0627 \U0001f680\n" * 50,
        "start" + " " * 120 + "end",
    ],
)
def test_chunks_are_bounded_deterministic_overlapping_and_lossless(content):
    for size, overlap in [(1, 0), (10, 0), (10, 3), (10, 9), (50, 10)]:
        chunks = chunk_text(content, chunk_size=size, chunk_overlap=overlap)
        assert chunks == chunk_text(content, chunk_size=size, chunk_overlap=overlap)
        assert chunks[0].start_offset == 0
        assert chunks[-1].end_offset == len(content)
        rebuilt = chunks[0].content
        for index, chunk in enumerate(chunks):
            assert 0 < len(chunk.content) <= size
            assert chunk.content == content[chunk.start_offset : chunk.end_offset]
            if index:
                previous = chunks[index - 1]
                assert chunk.start_offset == previous.end_offset - overlap
                assert chunk.end_offset > previous.end_offset
                rebuilt += chunk.content[overlap:]
        assert rebuilt == content


def test_chunking_prefers_logical_boundaries():
    content = (
        "First paragraph ends here.\n\nSecond paragraph is longer than this window."
    )
    chunks = chunk_text(content, chunk_size=40, chunk_overlap=5)
    assert chunks[0].content == "First paragraph ends here.\n\n"
    assert chunks[1].content[:5] == chunks[0].content[-5:]
    assert len(chunk_text("short", chunk_size=10, chunk_overlap=3)) == 1


def test_document_creation_relationships_metadata_and_null_vectors(
    db_session, curriculum
):
    metadata = {"language": "en", "tags": ["sql"]}
    document = ingest(
        db_session,
        curriculum,
        lesson_id=curriculum.lessons[0].id,
        file_name="lesson.txt",
        file_url="https://example.test/lesson.txt",
        metadata=metadata,
    )
    metadata["tags"].append("changed")
    db_session.expire_all()
    assert document.track is curriculum.tracks[0]
    assert document.lesson is curriculum.lessons[0]
    assert document in curriculum.tracks[0].documents
    assert document in curriculum.lessons[0].documents
    assert document.source_type == "text"
    assert document.file_name == "lesson.txt"
    assert document.file_url == "https://example.test/lesson.txt"
    assert document.metadata_json == {"language": "en", "tags": ["sql"]}
    assert document.created_at and document.updated_at
    assert len(document.content_hash) == 64
    assert len(document.chunks) > 1
    assert [chunk.chunk_index for chunk in document.chunks] == list(
        range(len(document.chunks))
    )
    for chunk in document.chunks:
        assert chunk.document is document
        assert chunk.content == document.raw_text[chunk.start_offset : chunk.end_offset]
        assert chunk.embedding is None
        assert chunk.metadata_json == {}
        assert chunk.created_at and chunk.updated_at


def test_lesson_only_resolves_track(db_session, curriculum):
    document = ingest(
        db_session, curriculum, track_id=None, lesson_id=curriculum.lessons[0].id
    )
    assert document.track_id == curriculum.tracks[0].id


@pytest.mark.parametrize("scope", ["track", "lesson"])
def test_duplicate_ingestion_keeps_first_source_and_chunks(
    db_session, curriculum, scope
):
    kwargs = {"lesson_id": curriculum.lessons[0].id} if scope == "lesson" else {}
    first = ingest(
        db_session, curriculum, raw_text="First line\r\nSecond line", **kwargs
    )
    chunk_ids = [chunk.id for chunk in first.chunks]
    second = ingest(
        db_session,
        curriculum,
        raw_text="First line\nSecond line",
        title="Other title",
        chunk_size=50,
        chunk_overlap=0,
        **kwargs,
    )
    assert second.id == first.id
    assert second.title == "Transactions"
    assert second.chunk_size == 150
    assert [chunk.id for chunk in second.chunks] == chunk_ids
    assert db_session.scalar(select(func.count()).select_from(Document)) == 1


def test_deduplication_is_scoped_and_changed_content_creates_new_document(
    db_session, curriculum
):
    documents = [
        ingest(db_session, curriculum),
        ingest(db_session, curriculum, track_id=curriculum.tracks[1].id),
        ingest(db_session, curriculum, lesson_id=curriculum.lessons[0].id),
        ingest(db_session, curriculum, lesson_id=curriculum.lessons[1].id),
        ingest(db_session, curriculum, raw_text="Changed course content."),
    ]
    assert len({document.id for document in documents}) == 5
    assert len({document.content_hash for document in documents[:4]}) == 1


@pytest.mark.parametrize(
    "kwargs,exception",
    [
        ({"track_id": None}, ValueError),
        ({"track_id": 9999999}, LookupError),
        ({"lesson_id": 9999999}, LookupError),
        ({"track_id": 0}, ValueError),
        ({"lesson_id": True}, ValueError),
        ({"title": " "}, ValueError),
        ({"file_name": "x" * 256}, ValueError),
        ({"source_type": ""}, ValueError),
        ({"metadata": []}, ValueError),
        ({"metadata": {"score": float("nan")}}, ValueError),
    ],
)
def test_invalid_ingestion_leaves_no_documents(
    db_session, curriculum, kwargs, exception
):
    with pytest.raises(exception):
        ingest(db_session, curriculum, **kwargs)
    assert db_session.scalar(select(func.count()).select_from(Document)) == 0


def test_mismatched_lesson_track_rejected(db_session, curriculum):
    with pytest.raises(ValueError, match="does not belong"):
        ingest(db_session, curriculum, lesson_id=curriculum.lessons[2].id)


@pytest.mark.parametrize("target", ["document", "lesson", "track", "orm_document"])
def test_deletion_cascades_chunks_without_deleting_other_documents(
    db_session, curriculum, target
):
    document = ingest(db_session, curriculum, lesson_id=curriculum.lessons[0].id)
    unrelated = ingest(db_session, curriculum, track_id=curriculum.tracks[1].id)
    document_id, other_id = document.id, unrelated.id
    if target == "orm_document":
        assert document.chunks
        db_session.delete(document)
    elif target == "document":
        db_session.execute(delete(Document).where(Document.id == document_id))
    elif target == "lesson":
        db_session.execute(delete(Lesson).where(Lesson.id == curriculum.lessons[0].id))
    else:
        db_session.execute(delete(Track).where(Track.id == curriculum.tracks[0].id))
    db_session.flush()
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == other_id)
        )
        > 0
    )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE document_chunks SET chunk_index=-1 WHERE document_id=:id",
        "UPDATE document_chunks SET start_offset=-1 WHERE document_id=:id",
        "UPDATE document_chunks SET end_offset=start_offset WHERE document_id=:id",
        "UPDATE documents SET content_hash='bad' WHERE id=:id",
        "UPDATE documents SET chunk_overlap=chunk_size WHERE id=:id",
        "UPDATE documents SET track_id=9999999 WHERE id=:id",
        "UPDATE documents SET lesson_id=9999999 WHERE id=:id",
    ],
)
def test_database_constraints(db_session, curriculum, statement):
    document = ingest(db_session, curriculum)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(text(statement), {"id": document.id})


def test_vector_column_is_native_and_round_trips(db_session, curriculum):
    chunk = ingest(db_session, curriculum).chunks[0]
    chunk.embedding = [1, 2, 3]
    db_session.flush()
    db_session.expire(chunk)
    assert chunk.embedding.tolist() == [1, 2, 3]
    assert (
        db_session.scalar(
            select(DocumentChunk.embedding.l2_distance([1, 2, 3])).where(
                DocumentChunk.id == chunk.id
            )
        )
        == 0
    )
    assert (
        db_session.scalar(
            text(
                "SELECT udt_name FROM information_schema.columns WHERE table_name='document_chunks' AND column_name='embedding'"
            )
        )
        == "vector"
    )


def test_chunk_failure_rolls_back_document_but_not_callers_transaction(
    db_session, curriculum, monkeypatch
):
    original = db_session.flush

    def failing_flush(*args, **kwargs):
        if any(isinstance(item, DocumentChunk) for item in db_session.new):
            raise RuntimeError("Chunk write failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", failing_flush)
    with pytest.raises(RuntimeError, match="Chunk write failed"):
        ingest(db_session, curriculum)
    monkeypatch.setattr(db_session, "flush", original)
    assert db_session.scalar(select(func.count()).select_from(Document)) == 0
    assert db_session.get(Track, curriculum.tracks[0].id) is not None
    assert ingest(db_session, curriculum).chunks


def test_ingestion_does_not_commit_callers_transaction(test_engine):
    with Session(test_engine) as db:
        track = Track(name=uuid4().hex, slug=uuid4().hex)
        db.add(track)
        db.flush()
        document = ingest_text(
            db, track_id=track.id, title="Rollback", raw_text="Caller-owned transaction"
        )
        document_id = document.id
        db.rollback()
    with Session(test_engine) as db:
        assert db.get(Document, document_id) is None


def test_concurrent_duplicates_create_exactly_one_complete_document(test_engine):
    with Session(test_engine) as db:
        track = Track(name=uuid4().hex, slug=uuid4().hex)
        db.add(track)
        db.commit()
        track_id = track.id

    def worker(_):
        with Session(test_engine) as db, db.begin():
            document = ingest_text(
                db,
                track_id=track_id,
                title="Concurrent",
                raw_text="Concurrent transactions and deduplication. " * 100,
            )
            return document.id, len(document.chunks)

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(worker, range(4)))
        assert len(set(results)) == 1
        assert results[0][1] > 1
        with Session(test_engine) as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Document)
                    .where(Document.track_id == track_id)
                )
                == 1
            )
    finally:
        with Session(test_engine) as db, db.begin():
            db.execute(delete(Track).where(Track.id == track_id))


def test_placeholder_rag_query_route_is_retired():
    assert "/api/v1/rag/query" not in app.openapi()["paths"]
