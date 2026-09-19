from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.graduation import GraduationEvaluationStatus


class GraduationGateCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    evaluation_id: int
    gate_key: str
    passed: bool
    actual_value: float | None = None
    required_value: float | None = None
    failure_reason: str | None = None
    details: dict[str, Any] | None = None


class GraduationEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    track_id: int
    overall_score: float | None = None
    is_eligible: bool
    status: GraduationEvaluationStatus
    evaluated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    gate_checks: list[GraduationGateCheckResponse] = Field(
        default_factory=list
    )
