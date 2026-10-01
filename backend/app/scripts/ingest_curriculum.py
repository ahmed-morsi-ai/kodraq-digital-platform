"""Ingest the four curriculum modules atomically using local multilingual embeddings."""

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.track import Track
from app.services.embeddings import EmbeddingError, LocalEmbeddings
from app.services.rag_ingestion import ingest_text, prepare_text

CURRICULUM_DIR = Path(__file__).resolve().parents[3] / "docs" / "curriculum"
MODULE_FILES = tuple(f"module-{index:02}.md" for index in range(4))


@dataclass(frozen=True)
class CurriculumModule:
    filename: str
    title: str
    content: str


@dataclass(frozen=True)
class IngestionResult:
    filename: str
    document_id: int
    chunks: int
    embedded: int


def load_modules(directory: Path) -> list[CurriculumModule]:
    modules = []
    for filename in MODULE_FILES:
        content, _ = prepare_text((directory / filename).read_text(encoding="utf-8"))
        heading = content.splitlines()[0]
        if not heading.startswith("# ") or not heading[2:].strip():
            raise ValueError(f"{filename} must begin with a Markdown title.")
        modules.append(CurriculumModule(filename, heading[2:].strip(), content))
    return modules


def resolve_track(
    db: Session, *, track_id: int | None, create_track: str | None, slug: str
) -> Track:
    if track_id is not None:
        track = db.get(Track, track_id)
        if track is None:
            raise ValueError("Track not found; select an existing track ID.")
        return track
    if not create_track or not create_track.strip() or len(create_track) > 255:
        raise ValueError("Provide a track ID or a nonblank track name (max 255 chars).")
    if (
        not slug
        or len(slug) > 255
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug)
    ):
        raise ValueError("Track slug must use lowercase letters, digits and hyphens.")
    track = db.scalar(select(Track).where(Track.slug == slug))
    if track is not None:
        if track.name != create_track.strip():
            raise ValueError("Track slug already belongs to a differently named track.")
        return track
    if db.scalar(select(Track.id).where(Track.name == create_track.strip())):
        raise ValueError("Track name already exists; use its track ID.")
    track = Track(name=create_track.strip(), slug=slug, is_active=False)
    db.add(track)
    db.flush()
    return track


def embed_document(
    db: Session,
    document: Document,
    embedder: LocalEmbeddings,
    *,
    reembed: bool = False,
) -> int:
    # Serialize concurrent embedding runs for the same deduplicated document.
    db.refresh(document, with_for_update=True)
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
            .execution_options(populate_existing=True)
        )
    )
    if not chunks:
        raise ValueError("Document has no chunks; repair ingestion before embedding.")
    profile = embedder.profile
    pending = []
    for chunk in chunks:
        digest = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        expected = {**profile, "content_hash": digest}
        if chunk.embedding is not None and not reembed:
            if (
                document.metadata_json.get("embedding") != profile
                or chunk.metadata_json.get("embedding") != expected
                or len(chunk.embedding) != embedder.dimensions
            ):
                raise ValueError("Embedding profile/content mismatch; use --reembed.")
        else:
            pending.append((chunk, expected))
    for start in range(0, len(pending), embedder.batch_size):
        batch = pending[start : start + embedder.batch_size]
        vectors = embedder.embed([chunk.content for chunk, _ in batch])
        for (chunk, metadata), vector in zip(batch, vectors, strict=True):
            # pgvector loads numpy arrays. Explicit SQL avoids ambiguous ORM array
            # equality when replacing a stored vector (including dimension changes).
            db.execute(
                DocumentChunk.__table__.update()
                .where(DocumentChunk.id == chunk.id)
                .values(
                    embedding=vector,
                    metadata_json={**chunk.metadata_json, "embedding": metadata},
                )
            )
            db.expire(chunk, ["embedding", "metadata_json"])
    document.metadata_json = {**document.metadata_json, "embedding": profile}
    db.flush()
    return len(pending)


def ingest_modules(
    db: Session,
    modules: list[CurriculumModule],
    *,
    track_id: int,
    embedder: LocalEmbeddings,
    reembed: bool = False,
) -> list[IngestionResult]:
    """The caller commits; a failed batch leaves no partly embedded curriculum."""
    results = []
    with db.begin_nested():
        for module in modules:
            document = ingest_text(
                db,
                raw_text=module.content,
                title=module.title,
                track_id=track_id,
                source_type="markdown",
                file_name=module.filename,
                metadata={
                    "source_path": f"docs/curriculum/{module.filename}",
                    "curriculum_module": Path(module.filename).stem,
                    "content_status": "draft",
                    "languages": ["ar", "en"],
                },
            )
            embedded = embed_document(db, document, embedder, reembed=reembed)
            results.append(
                IngestionResult(
                    module.filename, document.id, len(document.chunks), embedded
                )
            )
    return results


def search_curriculum(
    db: Session,
    *,
    track_id: int,
    query: str,
    embedder: LocalEmbeddings,
    limit: int = 3,
) -> list:
    """Operator-only smoke query, scoped to a track and matching embedding profile.

    A future HTTP caller must authorize track access before using this function.
    """
    if not 1 <= limit <= 20:
        raise ValueError("Search limit must be between 1 and 20.")
    vector = embedder.embed([query])[0]
    # MATERIALIZED filters incompatible dimensions before pgvector evaluates distance.
    eligible = (
        select(
            Document.file_name,
            DocumentChunk.chunk_index,
            DocumentChunk.embedding,
        )
        .join(DocumentChunk)
        .where(
            Document.track_id == track_id,
            Document.metadata_json["embedding"] == embedder.profile,
            DocumentChunk.embedding.is_not(None),
            func.vector_dims(DocumentChunk.embedding) == embedder.dimensions,
        )
        .cte("eligible")
        .prefix_with("MATERIALIZED")
    )
    distance = eligible.c.embedding.cosine_distance(vector).label("distance")
    return list(
        db.execute(
            select(eligible.c.file_name, eligible.c.chunk_index, distance)
            .order_by(distance, eligible.c.file_name, eligible.c.chunk_index)
            .limit(limit)
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=CURRICULUM_DIR)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--track-id", type=int)
    scope.add_argument(
        "--create-track", help="Create/reuse a draft track by name and slug"
    )
    parser.add_argument("--track-slug", default="backend-engineering-foundations")
    parser.add_argument("--reembed", action="store_true")
    parser.add_argument(
        "--verify-query", help="Run a scoped pgvector search after commit"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use cached model files without network access",
    )
    args = parser.parse_args(argv)
    engine = None
    try:
        from app.core.config import settings

        modules = load_modules(args.source_dir)
        embedder = LocalEmbeddings(local_files_only=args.offline)
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as connection:
            if not {"documents", "document_chunks"}.issubset(
                inspect(connection).get_table_names()
            ):
                raise ValueError(
                    "RAG tables are missing; run alembic upgrade head first."
                )
            if not connection.scalar(
                text("SELECT 1 FROM pg_extension WHERE extname='vector'")
            ):
                raise ValueError("pgvector is missing; run alembic upgrade head first.")
        embedder.load()
        with Session(engine) as db:
            with db.begin():
                track = resolve_track(
                    db,
                    track_id=args.track_id,
                    create_track=args.create_track,
                    slug=args.track_slug,
                )
                track_id = track.id
                results = ingest_modules(
                    db,
                    modules,
                    track_id=track_id,
                    embedder=embedder,
                    reembed=args.reembed,
                )
            print(
                f"COMMITTED track_id={track_id} model={embedder.model} dimensions={embedder.dimensions}"
            )
            for result in results:
                print(
                    f"{result.filename}: document_id={result.document_id} chunks={result.chunks} "
                    f"embedded={result.embedded} reused={result.chunks - result.embedded}"
                )
            print(
                f"READY documents={len(results)} chunks={sum(r.chunks for r in results)} "
                f"embedded={sum(r.embedded for r in results)}"
            )
            if args.verify_query:
                for hit in search_curriculum(
                    db,
                    track_id=track_id,
                    query=args.verify_query,
                    embedder=embedder,
                ):
                    print(
                        f"MATCH {hit.file_name} chunk={hit.chunk_index} cosine_distance={hit.distance:.6f}"
                    )
        return 0
    except (EmbeddingError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
    except (OSError, SQLAlchemyError):
        # Database exceptions may include connection secrets or document parameters.
        print(
            "ERROR: File/database operation failed; check paths, migrations and connection settings.",
            file=sys.stderr,
        )
    finally:
        if engine is not None:
            engine.dispose()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
