from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep, get_current_active_user
from app.api.v1.ai import get_ai_gateway
from app.models.ai import AIRequestLog
from app.models.enrollment import Enrollment
from app.models.track import Track
from app.models.user import User
from app.schemas.ai import AIUsageResponse
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, RAGSourceReference
from app.services.ai_gateway import AIGateway, AIProviderError
from app.services.rag_engine import RAGEngine

router = APIRouter()

CurrentUserDep = Annotated[
    User,
    Depends(get_current_active_user),
]
GatewayDep = Annotated[AIGateway, Depends(get_ai_gateway)]


def _is_manager(user: User) -> bool:
    return user.is_superuser or (
        user.role_rel is not None
        and user.role_rel.name.casefold() in {"admin", "instructor"}
    )


@router.post("/query", response_model=RAGQueryResponse)
def query_knowledge_base(
    request: RAGQueryRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    ai_gateway: GatewayDep,
) -> RAGQueryResponse:
    track = session.get(Track, request.track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found",
        )

    enrolled = session.execute(
        select(Enrollment.id).where(
            Enrollment.user_id == current_user.id,
            Enrollment.track_id == request.track_id,
            Enrollment.status == "active",
        )
    ).scalar_one_or_none()
    if not enrolled and not _is_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this track to query its knowledge base.",
        )

    engine = RAGEngine(ai_gateway)
    try:
        result = engine.query(
            session,
            track_id=request.track_id,
            query=request.query,
            top_k=request.top_k,
            model=request.model,
            query_vector=request.query_embedding,
        )
    except AIProviderError as error:
        session.add(
            AIRequestLog(
                user_id=current_user.id,
                provider="openai",
                model=request.model or "unknown",
                request_type="rag_query",
                success=False,
                error_message=str(error),
            )
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from None

    completion = result.completion
    session.add(
        AIRequestLog(
            user_id=current_user.id,
            provider=completion.provider,
            model=completion.model,
            request_type="rag_query",
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
            estimated_cost=completion.estimated_cost,
            latency_ms=completion.latency_ms,
            success=True,
        )
    )
    session.commit()
    return RAGQueryResponse(
        track_id=request.track_id,
        answer=completion.content,
        provider=completion.provider,
        model=completion.model,
        usage=AIUsageResponse(
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
        ),
        estimated_cost=completion.estimated_cost,
        sources=[
            RAGSourceReference(
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                document_title=source.document_title,
                chunk_index=source.chunk_index,
                similarity=source.similarity,
                metadata_json=source.metadata_json,
            )
            for source in result.sources
        ],
    )
