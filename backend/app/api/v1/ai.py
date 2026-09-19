from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, get_current_active_user
from app.models.ai import AIRequestLog
from app.models.user import User
from app.schemas.ai import (
    AICompletionRequest,
    AICompletionResponse,
    AIUsageResponse,
)
from app.services.ai_gateway import (
    AIGateway,
    AIProviderError,
    gateway,
)

router = APIRouter()

CurrentUserDep = Annotated[
    User,
    Depends(get_current_active_user),
]


def get_ai_gateway() -> AIGateway:
    return gateway


GatewayDep = Annotated[AIGateway, Depends(get_ai_gateway)]


@router.post(
    "/completions",
    response_model=AICompletionResponse,
)
def create_completion(
    request: AICompletionRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    ai_gateway: GatewayDep,
) -> AICompletionResponse:
    try:
        completion = ai_gateway.complete(
            [message.model_dump() for message in request.messages],
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except AIProviderError as error:
        session.add(
            AIRequestLog(
                user_id=current_user.id,
                provider=request.provider or "openai",
                model=request.model or "unknown",
                request_type=request.request_type,
                success=False,
                error_message=str(error),
            )
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from None

    session.add(
        AIRequestLog(
            user_id=current_user.id,
            provider=completion.provider,
            model=completion.model,
            request_type=request.request_type,
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
            estimated_cost=completion.estimated_cost,
            latency_ms=completion.latency_ms,
            success=True,
        )
    )
    session.commit()
    return AICompletionResponse(
        content=completion.content,
        provider=completion.provider,
        model=completion.model,
        usage=AIUsageResponse(
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
        ),
        estimated_cost=completion.estimated_cost,
    )
