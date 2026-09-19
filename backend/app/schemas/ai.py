from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AIChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)


class AICompletionRequest(BaseModel):
    request_type: str = Field(default="tutor_chat", min_length=1, max_length=64)
    messages: list[AIChatMessage] = Field(min_length=1, max_length=100)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=32_000)


class AIUsageResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AICompletionResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: AIUsageResponse
    estimated_cost: float
