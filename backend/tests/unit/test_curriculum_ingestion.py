"""Local inference is stubbed here; persistence and vector search use PostgreSQL."""

import re
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import func, select

from app.models.document import Document, DocumentChunk
from app.models.track import Track
from app.scripts.ingest_curriculum import (
    CURRICULUM_DIR,
    MODULE_FILES,
    CurriculumModule,
    embed_document,
    ingest_modules,
    load_modules,
    main,
    resolve_track,
    search_curriculum,
)
from app.services import embeddings
from app.services.embeddings import (
    EmbeddingError,
    LocalEmbeddings,
    MODEL_NAME,
    MODEL_REVISION,
)


def vector(index=0, dimensions=384):
    values = [0.0] * dimensions
    values[index] = 1.0
    return values


class StubTokenizer:
    def num_special_tokens_to_add(self, pair):
        assert pair is False
        return 2

    def encode(self, text, **kwargs):
        assert kwargs == {
            "add_special_tokens": False,
            "truncation": False,
            "verbose": False,
        }
        return list(text)


class StubEncoder:
    max_seq_length = 128
    tokenizer = StubTokenizer()

    def __init__(self):
        self.calls = []

    def get_sentence_embedding_dimension(self):
        return 384

    def encode(self, texts, **kwargs):
        assert kwargs == {
            "batch_size": 32,
            "convert_to_numpy": True,
            "normalize_embeddings": True,
            "show_progress_bar": False,
        }
        assert all(len(text) <= 126 for text in texts)
        self.calls.append(list(texts))
        return np.asarray(
            [vector(index % 384) for index in range(len(texts))], dtype=np.float32
        )


@pytest.fixture
def provider(monkeypatch):
    model = StubEncoder()
    loads, calls = [], []

    def loader(cache_dir, local_files_only):
        loads.append((cache_dir, local_files_only))
        return model

    monkeypatch.setattr(embeddings, "_load_sentence_transformer", loader)
    embedder = LocalEmbeddings(local_files_only=True)
    original = embedder.embed

    def embed(texts):
        calls.append(list(texts))
        return original(texts)

    monkeypatch.setattr(embedder, "embed", embed)
    return SimpleNamespace(embedder=embedder, calls=calls, model=model, loads=loads)


@pytest.fixture
def track(db_session):
    track = Track(name=uuid4().hex, slug=uuid4().hex)
    db_session.add(track)
    db_session.flush()
    return track


def module(content="# Example\n\nCurriculum transactions."):
    return CurriculumModule("module-00.md", "Example", content)


def test_embedding_shape_order_and_cached_load_without_key(provider, monkeypatch):
    assert provider.embedder.embed(["first", "second"]) == [vector(), vector(1)]
    assert provider.embedder.embed(["again"]) == [vector()]
    assert len(provider.loads) == 1
    assert provider.loads[0][1] is True
    assert provider.embedder.profile["revision"] == MODEL_REVISION
    assert provider.embedder.profile["provider"] == "sentence-transformers"


@pytest.mark.parametrize(
    "inputs",
    [
        [],
        ["a"] * 33,
        "text",
        b"text",
        None,
        [""],
        ["   "],
        [None],
        ["a" * 20001],
        ["a\x00b"],
        ["\ud800"],
    ],
)
def test_invalid_inputs_never_load_model(provider, inputs):
    with pytest.raises(ValueError):
        LocalEmbeddings().embed(inputs)
    assert provider.loads == []
    assert provider.model.calls == []


@pytest.mark.parametrize("error", [ImportError, OSError, RuntimeError, ValueError])
def test_model_load_failure_is_actionable(monkeypatch, error):
    def loader(*args):
        raise error("private diagnostic")

    monkeypatch.setattr(embeddings, "_load_sentence_transformer", loader)
    with pytest.raises(EmbeddingError) as exc:
        LocalEmbeddings(local_files_only=True).embed(["content"])
    assert "private diagnostic" not in str(exc.value)
    assert (
        "requirements-rag.txt" in str(exc.value)
        if error is ImportError
        else "cache" in str(exc.value)
    )


@pytest.mark.parametrize(
    "corruption",
    ["count", "dimension", "zero", "nan", "infinity", "string", "bool", "underflow"],
)
def test_invalid_model_vectors_rejected(provider, monkeypatch, corruption):
    values = np.asarray([vector()], dtype=np.float64)
    if corruption == "count":
        values = np.zeros((2, 384))
    elif corruption == "dimension":
        values = np.ones((1, 12))
    elif corruption == "zero":
        values[:] = 0
    elif corruption == "nan":
        values[0, 0] = np.nan
    elif corruption == "infinity":
        values[0, 0] = np.inf
    elif corruption == "string":
        values = values.astype(str)
    elif corruption == "bool":
        values = values.astype(bool)
    elif corruption == "underflow":
        values[:] = 1e-100
    monkeypatch.setattr(provider.model, "encode", lambda *args, **kwargs: values)
    with pytest.raises(EmbeddingError, match="invalid vectors"):
        provider.embedder.embed(["content"])


def test_long_chunks_are_losslessly_segmented_and_pooled(provider):
    content = "First paragraph " * 30 + "tail evidence"
    result = np.asarray(provider.embedder.embed([content]))
    segments = provider.model.calls[0]
    assert len(segments) > 1
    assert "".join(segments) == content
    assert all(len(segment) <= 126 for segment in segments)
    expected = np.zeros(384)
    for index, segment in enumerate(segments):
        expected[index] = len(segment)
    expected /= np.linalg.norm(expected)
    assert result.shape == (1, 384)
    assert result[0] == pytest.approx(expected, abs=1e-7)
    assert np.linalg.norm(result[0]) == pytest.approx(1.0)


def test_runtime_inference_error_is_safe(provider, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("private diagnostic")

    monkeypatch.setattr(provider.model, "encode", fail)
    with pytest.raises(EmbeddingError, match="^Local embedding generation failed.$"):
        provider.embedder.embed(["content"])


@pytest.mark.parametrize("problem", ["dimensions", "tokens"])
def test_wrong_model_contract_is_rejected(provider, monkeypatch, problem):
    if problem == "dimensions":
        monkeypatch.setattr(
            provider.model, "get_sentence_embedding_dimension", lambda: 128
        )
    else:
        provider.model.max_seq_length = 1
    with pytest.raises(EmbeddingError):
        provider.embedder.load()


def test_real_curriculum_files_are_bilingual_and_have_valid_examples():
    modules = load_modules(CURRICULUM_DIR)
    assert [item.filename for item in modules] == list(MODULE_FILES)
    examples = 0
    for item in modules:
        assert re.search(r"[\u0600-\u06ff]", item.content)
        assert "## Lab" in item.content
        for code in re.findall(r"```python\n(.*?)\n```", item.content, re.DOTALL):
            exec(
                compile(code, item.filename, "exec"), {"__name__": "curriculum_example"}
            )
            examples += 1
    assert examples >= 5


def test_missing_files_rejected_before_ingestion(tmp_path):
    (tmp_path / "module-00.md").write_text("# First\nContent", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        load_modules(tmp_path)


@pytest.mark.parametrize("content", ["", "   ", "No heading", "# \nEmpty title"])
def test_invalid_markdown_rejected(tmp_path, content):
    (tmp_path / "module-00.md").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_modules(tmp_path)


def test_curriculum_pgvector_storage_and_repeat_dedup(db_session, track, provider):
    modules = load_modules(CURRICULUM_DIR)
    first = ingest_modules(
        db_session, modules, track_id=track.id, embedder=provider.embedder
    )
    assert len(first) == 4
    assert all(item.chunks == item.embedded > 0 for item in first)
    calls = len(provider.calls)
    second = ingest_modules(
        db_session, modules, track_id=track.id, embedder=provider.embedder
    )
    assert [r.document_id for r in second] == [r.document_id for r in first]
    assert all(r.embedded == 0 for r in second)
    assert len(provider.calls) == calls
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.track_id == track.id)
        )
        == 4
    )
    rows = list(
        db_session.execute(
            select(DocumentChunk, func.vector_dims(DocumentChunk.embedding))
            .join(Document)
            .where(Document.track_id == track.id)
        )
    )
    assert len(rows) == sum(r.chunks for r in first)
    for chunk, dimensions in rows:
        assert dimensions == 384
        assert chunk.metadata_json["embedding"]["model"] == MODEL_NAME
        assert chunk.document.metadata_json["content_status"] == "draft"


def test_embedding_batches_are_bounded(db_session, track, provider):
    # Many logical chunks require multiple provider batches, without reordering.
    result = ingest_modules(
        db_session,
        [module("# Example\n" + "transactions " * 4000)],
        track_id=track.id,
        embedder=provider.embedder,
    )[0]
    assert result.chunks > 32
    assert all(1 <= len(call) <= 32 for call in provider.calls)
    assert sum(map(len, provider.calls)) == result.chunks


def test_failure_rolls_back_all_documents_and_vectors(
    db_session, track, provider, monkeypatch
):
    original = provider.embedder.embed
    count = 0

    def fail_second_batch(texts):
        nonlocal count
        count += 1
        if count == 2:
            raise EmbeddingError("Local embedding generation failed.")
        return original(texts)

    monkeypatch.setattr(provider.embedder, "embed", fail_second_batch)
    with pytest.raises(EmbeddingError):
        ingest_modules(
            db_session,
            [module(), module("# Second\nDifferent content")],
            track_id=track.id,
            embedder=provider.embedder,
        )
    assert count == 2
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.track_id == track.id)
        )
        == 0
    )
    # The caller's existing track and transaction remain usable.
    assert db_session.get(Track, track.id) is track


@pytest.mark.parametrize("corruption", ["profile", "dimension", "content"])
def test_stale_embeddings_require_explicit_reembed(
    db_session, track, provider, corruption
):
    result = ingest_modules(
        db_session, [module()], track_id=track.id, embedder=provider.embedder
    )[0]
    document = db_session.get(Document, result.document_id)
    chunk = document.chunks[0]
    if corruption == "profile":
        document.metadata_json = {
            **document.metadata_json,
            "embedding": {"model": "old"},
        }
    elif corruption == "dimension":
        db_session.execute(
            DocumentChunk.__table__.update()
            .where(DocumentChunk.id == chunk.id)
            .values(embedding=[1.0, 0.0])
        )
        db_session.expire(chunk, ["embedding"])
    else:
        chunk.metadata_json = {}
    db_session.flush()
    with pytest.raises(ValueError, match="--reembed"):
        embed_document(db_session, document, provider.embedder)
    assert embed_document(db_session, document, provider.embedder, reembed=True) == 1
    assert len(document.chunks[0].embedding) == 384


def test_resumes_null_embeddings_only(db_session, track, provider):
    item = module("# Example\n" + "database transactions " * 100)
    result = ingest_modules(
        db_session, [item], track_id=track.id, embedder=provider.embedder
    )[0]
    document = db_session.get(Document, result.document_id)
    document.chunks[0].embedding = None
    db_session.flush()
    assert embed_document(db_session, document, provider.embedder) == 1
    assert embed_document(db_session, document, provider.embedder) == 0


def test_search_scopes_track_and_filters_incompatible_dimensions(
    db_session, track, provider
):
    result = ingest_modules(
        db_session,
        [module("# Example\n" + "database " * 500)],
        track_id=track.id,
        embedder=provider.embedder,
    )[0]
    other = Track(name=uuid4().hex, slug=uuid4().hex)
    db_session.add(other)
    db_session.flush()
    ingest_modules(
        db_session,
        [CurriculumModule("private.md", "Private", "# Private\nPrivate material")],
        track_id=other.id,
        embedder=provider.embedder,
    )
    document = db_session.get(Document, result.document_id)
    db_session.execute(
        DocumentChunk.__table__.update()
        .where(DocumentChunk.id == document.chunks[0].id)
        .values(embedding=[1.0, 0.0])
    )
    db_session.expire(document.chunks[0], ["embedding"])
    document.chunks[1].embedding = None
    db_session.flush()
    hits = search_curriculum(
        db_session, track_id=track.id, query="transactions", embedder=provider.embedder
    )
    assert hits
    assert all(hit.file_name == "module-00.md" and hit.chunk_index >= 2 for hit in hits)
    document.metadata_json = {**document.metadata_json, "embedding": {"model": "old"}}
    db_session.flush()
    assert (
        search_curriculum(
            db_session, track_id=track.id, query="test", embedder=provider.embedder
        )
        == []
    )


def test_track_resolution_does_not_publish_or_overwrite(db_session, track):
    assert (
        resolve_track(db_session, track_id=track.id, create_track=None, slug="unused")
        is track
    )
    name, slug = uuid4().hex, uuid4().hex
    created = resolve_track(db_session, track_id=None, create_track=name, slug=slug)
    assert not created.is_active
    assert (
        resolve_track(db_session, track_id=None, create_track=name, slug=slug)
        is created
    )
    with pytest.raises(ValueError, match="differently named"):
        resolve_track(db_session, track_id=None, create_track="Different", slug=slug)
    with pytest.raises(ValueError, match="name already exists"):
        resolve_track(db_session, track_id=None, create_track=name, slug="other-slug")
    with pytest.raises(ValueError, match="not found"):
        resolve_track(db_session, track_id=2147483647, create_track=None, slug="unused")


def test_cli_missing_files_fails_cleanly(tmp_path, capsys):
    assert main(["--track-id", "1", "--source-dir", str(tmp_path)]) == 1
    assert "File/database operation failed" in capsys.readouterr().err


def test_cli_commit_and_offline_rerun_without_api_key(
    test_engine, monkeypatch, capsys, provider
):
    from app.core.config import settings

    monkeypatch.setattr(
        settings, "DATABASE_URL", test_engine.url.render_as_string(hide_password=False)
    )
    name, slug = uuid4().hex, uuid4().hex
    arguments = ["--create-track", name, "--track-slug", slug, "--offline"]
    try:
        assert main(arguments) == 0
        output = capsys.readouterr().out
        assert "COMMITTED track_id=" in output
        assert "READY documents=4" in output
        count = len(provider.model.calls)
        assert main(arguments) == 0
        assert "embedded=0" in capsys.readouterr().out
        assert len(provider.model.calls) == count
        assert all(offline for _, offline in provider.loads)
        with test_engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(Document)
                    .join(Track)
                    .where(Track.slug == slug)
                )
                == 4
            )
    finally:
        with test_engine.begin() as connection:
            connection.execute(Track.__table__.delete().where(Track.slug == slug))
