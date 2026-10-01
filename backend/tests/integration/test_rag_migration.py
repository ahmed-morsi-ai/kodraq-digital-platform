import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.rag_ingestion import ingest_text


def seed_legacy(connection):
    track = connection.scalar(
        text(
            "INSERT INTO tracks(name,slug,is_active,ordering,price,currency,is_premium) "
            "VALUES ('RAG migration','rag-migration',true,0,0,'EGP',false) RETURNING id"
        )
    )
    document = connection.scalar(
        text(
            "INSERT INTO knowledge_documents(track_id,title,source_type,file_url,is_active) "
            "VALUES (:track,'Keep original source','text','https://example.test/original.txt',true) RETURNING id"
        ),
        {"track": track},
    )
    chunk = connection.scalar(
        text(
            "INSERT INTO knowledge_chunks(document_id,track_id,chunk_index,content,embedding,metadata_json) "
            "VALUES (:document,:track,0,'Keep original chunk','[1,2,3]',CAST(:metadata AS JSON)) RETURNING id"
        ),
        {"track": track, "document": document, "metadata": '{"page":1}'},
    )
    return {"track": track, "document": document, "chunk": chunk}


def test_rag_upgrade_downgrade_reupgrade_preserves_legacy_data(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15500000001")
    with engine.begin() as connection:
        ids = seed_legacy(connection)
        assert (
            connection.scalar(
                text("SELECT count(*) FROM pg_extension WHERE extname='vector'")
            )
            == 0
        )
    for iteration in range(2):
        migrate("upgrade", "f16100000001")
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            )
            assert connection.execute(
                text(
                    "SELECT content,embedding,metadata_json FROM knowledge_chunks_archive WHERE id=:chunk"
                ),
                ids,
            ).one() == ("Keep original chunk", [1, 2, 3], {"page": 1})
            assert (
                connection.scalar(
                    text(
                        "SELECT title FROM knowledge_documents_archive WHERE id=:document"
                    ),
                    ids,
                )
                == "Keep original source"
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT udt_name FROM information_schema.columns WHERE table_name='document_chunks' AND column_name='embedding'"
                    )
                )
                == "vector"
            )
        tables = inspect(engine).get_table_names()
        assert "documents" in tables and "document_chunks" in tables
        assert "knowledge_documents" not in tables
        assert inspect(engine).get_foreign_keys("knowledge_documents_archive") == []
        with Session(engine) as db, db.begin():
            document = ingest_text(
                db,
                track_id=ids["track"],
                title="New source",
                raw_text="New course text. " * 300,
            )
            duplicate = ingest_text(
                db,
                track_id=ids["track"],
                title="Duplicate",
                raw_text="New course text. " * 300,
            )
            assert document.id == duplicate.id
            assert document.chunks and all(
                chunk.embedding is None for chunk in document.chunks
            )
            document.chunks[0].embedding = [1, 2, 3]
            db.flush()
            assert (
                db.scalar(
                    select(DocumentChunk.embedding.l2_distance([1, 2, 3])).where(
                        DocumentChunk.id == document.chunks[0].id
                    )
                )
                == 0
            )
            for statement in [
                "UPDATE documents SET content_hash='invalid' WHERE id=:id",
                "UPDATE document_chunks SET end_offset=0 WHERE document_id=:id",
            ]:
                with pytest.raises(IntegrityError), db.begin_nested():
                    db.execute(text(statement), {"id": document.id})
            db.delete(document)
        if iteration == 0:
            migrate("downgrade", "f15500000001")
            with engine.connect() as connection:
                assert connection.scalar(
                    text("SELECT embedding FROM knowledge_chunks WHERE id=:chunk"), ids
                ) == [1, 2, 3]
                assert (
                    connection.scalar(
                        text("SELECT count(*) FROM pg_extension WHERE extname='vector'")
                    )
                    == 1
                )
            assert "documents" not in inspect(engine).get_table_names()
            assert len(inspect(engine).get_foreign_keys("knowledge_documents")) == 1
    print(
        "RAG upgrade -> downgrade -> re-upgrade: native vector, ingestion, deduplication, and legacy preservation verified. Exit code: 0"
    )


def test_rag_downgrade_refuses_to_discard_ingested_content(migration_database):
    engine, migrate = migration_database
    migrate("upgrade", "f15500000001")
    with engine.begin() as connection:
        ids = seed_legacy(connection)
    migrate("upgrade", "f16100000001")
    with Session(engine) as db, db.begin():
        document_id = ingest_text(
            db,
            track_id=ids["track"],
            title="Retain",
            raw_text="Do not discard this document.",
        ).id
    result = migrate("downgrade", "f15500000001", succeeds=False)
    assert "refusing to discard ingested content" in result.stderr
    with Session(engine) as db:
        assert db.get(Document, document_id).chunks
        assert (
            db.scalar(text("SELECT version_num FROM alembic_version")) == "f16100000001"
        )
