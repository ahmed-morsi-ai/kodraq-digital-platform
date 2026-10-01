# RAG infrastructure (Epic 6.1)

`app/models/document.py` defines `Document` and `DocumentChunk`, backed by
`documents` and `document_chunks`. Each document belongs to a track and may also
belong to a lesson. Ingestion resolves the lesson's track and rejects inconsistent
references. Chunks inherit curriculum scope through their document rather than
duplicating a potentially conflicting track ID. Deleting a document, its lesson,
or its track cascades to its chunks.

Source title, type, optional file name/URL, canonical text, SHA-256 content hash,
chunk parameters, JSONB metadata, and timestamps are retained. Each ordered chunk
stores text, start/end character offsets, JSONB metadata, timestamps, and a nullable
native pgvector `vector` column. The unique `(document_id, chunk_index)` index also
supports ordered chunk lookup. Partial unique indexes enforce deduplication within
a track-level scope or a lesson-level scope, including track documents with no lesson.

The embedding column permits different dimensions at the storage layer. Base text
ingestion creates SQL NULL embeddings. The separate curriculum command now validates
local multilingual MiniLM embeddings at 384 dimensions, records their profile, and supports a
track-scoped exact vector search smoke check. See [CURRICULUM_INGESTION.md](CURRICULUM_INGESTION.md)
for execution and model-cache prerequisites. There are no hash substitutes or public
vector search endpoints. The native type and SQLAlchemy integration follow the
[pgvector](https://github.com/pgvector/pgvector) and
[pgvector Python](https://github.com/pgvector/pgvector-python) documentation.

## Ingestion contract

```python
from app.services.rag_ingestion import ingest_text

# Authorize this track/lesson before invoking the internal service.
with session.begin():
    document = ingest_text(
        session,
        track_id=track_id,
        lesson_id=lesson_id,  # optional; alone it is enough to resolve the track
        title="Transactions",
        raw_text=source_text,
        source_type="text",
        file_name="transactions.txt",
        metadata={"language": "en"},
        chunk_size=1000,
        chunk_overlap=150,
    )
```

The service does not fetch URLs, parse files, authorize actors, or commit the caller's
transaction. A savepoint and database uniqueness make document/chunk creation atomic
and safe under concurrent duplicate requests. Repeated content returns the original
document, source metadata, and chunk configuration. New content creates a new document;
the service does not silently replace an existing source. Identical text in different
tracks or lessons remains separate.

Preparation removes one leading Unicode BOM, normalizes CRLF/CR to LF and Unicode
to NFC, then hashes UTF-8 bytes. It preserves case, indentation, and leading/trailing
whitespace. Empty/whitespace-only text, NUL characters, invalid Unicode, and input
over two million characters are rejected. Metadata must be a serializable JSON object.

Chunking defaults to 1000 characters with exactly 150 overlapping characters. It
prefers paragraph, line, sentence, and word boundaries within the latter portion
of a window, then falls back to character boundaries for long unbroken text. Offsets
refer to canonical text, use Unicode character positions (not bytes or tokens), and
have an exclusive end. Every character remains recoverable. Sizes must be 1..20000,
overlap must be 0..size-1, and at most 10000 chunks may be created per document.

## PostgreSQL and migration

Install Python dependencies with `python -m pip install -r requirements.txt`.
`pgvector==0.4.2` provides the SQLAlchemy type; PostgreSQL separately needs the server
extension installed. `docker-compose.yml` now builds `backend/docker/postgres.Dockerfile`
from the same PostgreSQL 16 Alpine family, adding pgvector 0.8.6. No volume, port,
credentials, authentication, or application database URL configuration changed.

For a fresh local stack, `docker compose up -d --build db` creates the required image.
On an existing stack, rebuilding/recreating the DB service requires a maintenance
window and keeps the existing named volume. Do not remove that volume. In this task,
the built extension files were installed into the already-running local PostgreSQL
container without recreating it. No compiler toolchain was installed in the running
database container.

Migration `f16100000001` first executes `CREATE EXTENSION IF NOT EXISTS vector;`,
then creates the new tables and indexes. Use `alembic upgrade head` against the
explicitly selected deployment database with a role allowed to enable the extension.
An unavailable extension causes an atomic migration failure, not a JSON fallback.
The extension remains installed during downgrade because other tables may use it.

Legacy `knowledge_documents` / `knowledge_chunks` are renamed with an `_archive`
suffix. Their source text, JSON embeddings, metadata, IDs, and internal relationships
are preserved. Track foreign keys are detached so deleting current curriculum cannot
erase archived evidence. Re-ingest original sources explicitly; unverified legacy
vectors are not copied into the new embedding column. Downgrade restores the old
names and foreign keys, and fails if their referenced tracks no longer exist.

Downgrade refuses to discard any new documents. Export and explicitly remove new
RAG documents before reverting this revision. The migration tests verify this refusal
is transactional and leaves documents, chunks, and the revision intact.

Migration round trips are applied to temporary local PostgreSQL databases. During
curriculum setup, the empty local application DB was upgraded from `8e2435463795`
to `f16100000001` so ingestion can use the native vector tables. Supabase was not
modified. Deployment requires applying the migration chain to the intended target.

## Cleanup and verification

Removed the legacy JSON knowledge ORM, the hash-based RAG retrieval engine, its
query router and schemas, and the dashboard's nonfunctional AI Tutor action. The
existing real AI provider gateway is separate from this scaffold and remains in place.
Historical Alembic revisions remain intact for existing installations and rollback.

Run in the backend virtual environment, with `DEBUG=false` if the host defines an
unrelated DEBUG value. Tests use only the guarded `kodraq_test_db` local database:

```text
python -m pytest tests/unit/test_rag_ingestion.py tests/integration/test_rag_migration.py -q -s
python -m pytest -q
python -m ruff check app tests alembic
```

Tests cover canonical hashing, Unicode/whitespace preservation, logical boundaries,
exact overlap and lossless reconstruction, validation limits, source metadata,
bidirectional relationships, ownership checks, scoped and concurrent deduplication,
transaction rollback, cascade deletion, native vector storage, and populated legacy
migration round trips. Test database setup enables the extension before ORM tables
are created and removes the two retired scaffold tables left by old test runs.
