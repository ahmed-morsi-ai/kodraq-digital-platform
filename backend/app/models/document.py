from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_documents_hash"),
        CheckConstraint("length(raw_text) > 0", name="ck_documents_text"),
        CheckConstraint("length(trim(title)) > 0", name="ck_documents_title"),
        CheckConstraint("chunk_size > 0", name="ck_documents_chunk_size"),
        CheckConstraint(
            "chunk_overlap >= 0 AND chunk_overlap < chunk_size",
            name="ck_documents_chunk_overlap",
        ),
        Index(
            "uq_documents_track_hash",
            "track_id",
            "content_hash",
            unique=True,
            postgresql_where=text("lesson_id IS NULL"),
        ),
        Index(
            "uq_documents_lesson_hash",
            "lesson_id",
            "content_hash",
            unique=True,
            postgresql_where=text("lesson_id IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    track_id = Column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id = Column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    source_type = Column(
        String(32), nullable=False, default="text", server_default="text"
    )
    file_name = Column(String(255), nullable=True)
    file_url = Column(String(1024), nullable=True)
    raw_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    chunk_size = Column(Integer, nullable=False)
    chunk_overlap = Column(Integer, nullable=False)
    metadata_json = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    track = relationship("Track", back_populates="documents")
    lesson = relationship("Lesson", back_populates="documents")
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_index"),
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_index"),
        CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset AND "
            "char_length(content) = end_offset - start_offset",
            name="ck_document_chunks_offsets",
        ),
    )

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    metadata_json = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    # Provider/dimension metadata accompanies embeddings; ingestion can stage NULLs.
    embedding = Column(Vector(), nullable=True)

    document = relationship("Document", back_populates="chunks")
