"""RAG documents, deterministic ingestion, and native pgvector chunks.

Revision ID: f16100000001
Revises: f15500000001
"""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "f16100000001"
down_revision = "f15500000001"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column(
            name,
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        )
        for name in ("created_at", "updated_at")
    ]


def upgrade():
    # Installation on the PostgreSQL server is a prerequisite; fail atomically if absent.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    for table in ("knowledge_documents", "knowledge_chunks"):
        # Preserve legacy text/JSON embeddings without presenting hash vectors as embeddings.
        op.drop_constraint(f"{table}_track_id_fkey", table, type_="foreignkey")
        op.rename_table(table, f"{table}_archive")
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "track_id",
            sa.Integer(),
            sa.ForeignKey("tracks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(32), server_default="text", nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_url", sa.String(1024), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False),
        sa.Column(
            "metadata_json",
            JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_documents_hash"),
        sa.CheckConstraint("length(raw_text) > 0", name="ck_documents_text"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_documents_title"),
        sa.CheckConstraint("chunk_size > 0", name="ck_documents_chunk_size"),
        sa.CheckConstraint(
            "chunk_overlap >= 0 AND chunk_overlap < chunk_size",
            name="ck_documents_chunk_overlap",
        ),
    )
    op.create_index("ix_documents_track_id", "documents", ["track_id"])
    op.create_index("ix_documents_lesson_id", "documents", ["lesson_id"])
    op.create_index(
        "uq_documents_track_hash",
        "documents",
        ["track_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("lesson_id IS NULL"),
    )
    op.create_index(
        "uq_documents_lesson_hash",
        "documents",
        ["lesson_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("lesson_id IS NOT NULL"),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column(
            "metadata_json",
            JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_index"
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_index"),
        sa.CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset AND char_length(content) = end_offset - start_offset",
            name="ck_document_chunks_offsets",
        ),
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM documents)")):
        raise RuntimeError(
            "Export and remove RAG documents before downgrade; refusing to discard ingested content."
        )
    op.drop_table("document_chunks")
    op.drop_table("documents")
    for table in ("knowledge_documents", "knowledge_chunks"):
        op.rename_table(f"{table}_archive", table)
        op.create_foreign_key(
            f"{table}_track_id_fkey",
            table,
            "tracks",
            ["track_id"],
            ["id"],
            ondelete="CASCADE",
        )
    # The extension may be shared with other applications; never DROP EXTENSION CASCADE.
