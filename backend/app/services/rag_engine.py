from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.ai_gateway import AIGateway, GatewayCompletion

EmbeddingGenerator = Callable[[str], Sequence[float]]


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    content: str
    similarity: float
    metadata_json: dict[str, Any] | None


@dataclass(frozen=True)
class RAGCompletion:
    completion: GatewayCompletion
    sources: list[RetrievedChunk]


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (
        left_norm * right_norm
    )


def _hash_embedding(text: str, dimension: int) -> list[float]:
    values = [0.0] * dimension
    tokens = re.findall(r"\w+", text.casefold())
    for token_index, token in enumerate(tokens):
        digest = hashlib.sha256(f"{token_index}:{token}".encode()).digest()
        for offset in range(0, len(digest), 4):
            bucket = int.from_bytes(digest[offset : offset + 4], "big") % dimension
            sign = 1.0 if digest[offset] & 1 else -1.0
            values[bucket] += sign
    return values


class RAGEngine:
    def __init__(self, ai_gateway: AIGateway):
        self.ai_gateway = ai_gateway

    def retrieve(
        self,
        db: Session,
        *,
        track_id: int,
        query: str,
        top_k: int = 4,
        query_vector: Sequence[float] | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
    ) -> list[RetrievedChunk]:
        rows = db.execute(
            select(KnowledgeChunk, KnowledgeDocument.title)
            .join(
                KnowledgeDocument,
                KnowledgeChunk.document_id == KnowledgeDocument.id,
            )
            .where(
                KnowledgeChunk.track_id == track_id,
                KnowledgeDocument.track_id == track_id,
                KnowledgeDocument.is_active.is_(True),
            )
        ).all()
        embedded_rows = [
            (chunk, title, chunk.embedding)
            for chunk, title in rows
            if isinstance(chunk.embedding, list) and chunk.embedding
        ]
        if not embedded_rows:
            return []

        if query_vector is None:
            if embedding_generator is not None:
                query_vector = embedding_generator(query)
            else:
                query_vector = _hash_embedding(
                    query,
                    len(embedded_rows[0][2]),
                )

        ranked = []
        for chunk, title, embedding in embedded_rows:
            similarity = cosine_similarity(query_vector, embedding)
            ranked.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=title,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    similarity=round(similarity, 6),
                    metadata_json=chunk.metadata_json,
                )
            )
        ranked.sort(key=lambda item: item.similarity, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def build_augmented_prompt(
        query: str,
        sources: Sequence[RetrievedChunk],
    ) -> str:
        context = "\n\n".join(
            f"[Source {index}: {source.document_title} / chunk "
            f"{source.chunk_index}]\n{source.content}"
            for index, source in enumerate(sources, start=1)
        )
        if not context:
            context = "No relevant knowledge-base context was found."
        return (
            "You are Kodraq's track-scoped learning assistant. "
            "Answer using the provided context when possible. "
            "Do not invent course-specific facts.\n\n"
            f"Knowledge context:\n{context}\n\n"
            f"Student question:\n{query}"
        )

    def query(
        self,
        db: Session,
        *,
        track_id: int,
        query: str,
        top_k: int = 4,
        model: str | None = None,
        query_vector: Sequence[float] | None = None,
        embedding_generator: EmbeddingGenerator | None = None,
    ) -> RAGCompletion:
        sources = self.retrieve(
            db,
            track_id=track_id,
            query=query,
            top_k=top_k,
            query_vector=query_vector,
            embedding_generator=embedding_generator,
        )
        prompt = self.build_augmented_prompt(query, sources)
        completion = self.ai_gateway.complete(
            [
                {
                    "role": "system",
                    "content": "You are a precise educational assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            model=model,
        )
        return RAGCompletion(completion=completion, sources=sources)
