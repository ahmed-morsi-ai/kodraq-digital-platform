from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "track_id",
            name="uq_knowledge_documents_id_track",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    source_type = Column(String(32), nullable=False)
    file_url = Column(String(1024), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track", back_populates="knowledge_documents")
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
        overlaps="track,knowledge_chunks",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "track_id"],
            ["knowledge_documents.id", "knowledge_documents.track_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_knowledge_chunks_document_index",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    document = relationship(
        "KnowledgeDocument",
        back_populates="chunks",
        overlaps="track,knowledge_chunks",
    )
    track = relationship(
        "Track",
        back_populates="knowledge_chunks",
        overlaps="document,chunks",
    )
