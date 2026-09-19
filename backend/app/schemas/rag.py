from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ai import AIUsageResponse


class RAGQueryRequest(BaseModel):
    track_id: int
    query: str = Field(min_length=1, max_length=20_000)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    top_k: int = Field(default=4, ge=1, le=20)
    query_embedding: list[float] | None = Field(default=None, min_length=1)


class RAGSourceReference(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    similarity: float
    metadata_json: dict[str, Any] | None = None


class RAGQueryResponse(BaseModel):
    track_id: int
    answer: str
    provider: str
    model: str
    usage: AIUsageResponse
    estimated_cost: float
    sources: list[RAGSourceReference] = Field(default_factory=list)
