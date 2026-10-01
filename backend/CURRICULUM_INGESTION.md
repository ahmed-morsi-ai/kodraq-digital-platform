# Curriculum ingestion and embeddings

The four UTF-8 files in `docs/curriculum/module-00.md` through `module-03.md`
contain original Arabic/English course drafts. The cited external course documents
were not supplied. Review these drafts before publishing them as the official
curriculum. Ingestion stores `content_status: draft`, source paths and languages.

`app/scripts/ingest_curriculum.py` loads all four files before writing, reuses
`rag_ingestion.py` for canonical SHA-256 deduplication and overlapping chunks, then
runs Sentence Transformers on the local CPU. `app/services/embeddings.py` uses
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, producing normalized
384-dimensional vectors. This multilingual MiniLM model suits the Arabic/English
curriculum; its [model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
documents the architecture and Apache-2.0 license. Its revision is pinned to
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42` for reproducible downloads. Model loading
uses CPU, safetensors, no authentication token and `trust_remote_code=False`.

The model has a 128-token limit. Long chunks are subdivided at word boundaries
(or character boundaries for unbroken text) until each segment fits. Every source
character is preserved. Segment embeddings are averaged using token counts as
weights and normalized again. The same algorithm embeds queries. This avoids
silently dropping the ends of 1000-character curriculum chunks. The pooling
strategy is versioned in the embedding profile.

No schema migration is needed: the existing pgvector column accepts 384 dimensions.
Existing incompatible vectors are never mixed with new ones.

## Run locally

Embeddings require **no API key, paid service, or GPU**. Install the optional local
CPU dependencies from `backend/` with `pip install -r requirements-rag.txt`.
That requirements file targets Windows/Linux CPU wheels. Keeping the ML runtime
separate from `requirements.txt` avoids adding PyTorch to the Vercel API bundle.
The first run downloads public model files from Hugging Face. Inference does not
send course text to a hosted API. Model files are cached under
`backend/.cache/sentence-transformers/`, excluded from Git and Docker builds.

The unrelated AI completion gateway may still use `OPENAI_API_KEY`; the embedding
adapter and curriculum command never read it.

Use the existing local database configuration. If selecting a different database,
set `DATABASE_URL` deliberately before migrating or ingesting. Set `DEBUG=false`
if the host has an unrelated non-boolean DEBUG variable.

```powershell
$env:DEBUG = 'false'
.\.venv\Scripts\python.exe -m pip install -r requirements-rag.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.scripts.ingest_curriculum --create-track "Backend Engineering Foundations" --verify-query "HTTP routing paths and 404 diagnosis"
```

After the initial download, add `--offline` to load only cached model files and
perform ingestion/search without network access. `HF_HUB_OFFLINE=1` can additionally
enforce the Hugging Face library's offline mode. If the cache is missing, the command
fails clearly; it never substitutes synthetic vectors or calls a hosted provider.
Keep the model cache on persistent disk for repeat runs. Downloading/loading the
model happens before the write transaction begins.

For an existing curriculum track, use `--track-id ID` instead of `--create-track`.
The default slug for a newly created track is `backend-engineering-foundations`;
override it with `--track-slug`. New tracks are inactive drafts. Existing tracks
are not renamed or republished. Rerunning with the same name/slug reuses the track.
This command creates track-scoped RAG documents, not lesson/module UI records.

All four documents, chunks, embeddings and any new track commit together. A
model/file/database failure returns exit code 1 and rolls back database writes.
No hosted embedding client, API quota handling, or synthetic fallback remains.

Successful output begins with `COMMITTED`, followed by per-file chunk counts and
`READY documents=4 ...`. Reruns with unchanged content and the same embedding
profile report `embedded=0` and reuse existing vectors without re-encoding them.
An optional `--verify-query` computes one local query embedding.

Each chunk records its source content hash and embedding library/model/revision,
dimensions, normalization and pooling strategy.
Mismatched stored vectors are refused; use `--reembed` deliberately to regenerate
all vectors for these documents. New source content creates a new document version
under the base ingestion contract; older versions are retained. Review/remove
superseded source versions explicitly before serving changed curricula to learners.

## Retrieval boundary

`--verify-query` performs a real pgvector cosine-distance search restricted to the
selected track and compatible document embedding profile/dimensions. It reports
source filenames, chunk numbers and distances. It runs **after ingestion commits**:
if query encoding fails, the preceding `COMMITTED` data remains saved and the
command exits 1. A retry reuses that data.

This is an operator command, not a public API or a completed AI Tutor chat UI.
A future learner-facing caller must authorize enrollment/instructor track access
before retrieval and disclose the content's draft status. The current small corpus
uses exact vector search; an approximate nearest-neighbor index can be added when
corpus size justifies it. Do not compare vectors from different embedding models.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_curriculum_ingestion.py tests/unit/test_rag_ingestion.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests alembic
```

Unit tests stub local inference, so the normal backend suite needs no model download.
They use real PostgreSQL/pgvector for persistence, deduplication, rollback, profile
changes and track-scoped search, and verify lossless segmentation and weighted
pooling. They also execute the curriculum's Python examples. Verify real model
inference separately with the command above, a repeat `--offline` run, and database
counts confirming every chunk has a 384-dimensional embedding.
