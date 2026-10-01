from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.graduation import GraduationStatus


class GraduationFinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GraduationGateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    gate_key: str
    passed: bool
    actual_value: float
    required_value: float
    failure_reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class GraduationCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: int
    gate_key: str
    passed: bool
    score: float | None
    required_value: float | None
    failure_reason: str | None
    details: dict[str, Any] | None


class GraduationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    track_id: int
    overall_score: float | None
    eligible: bool
    status: GraduationStatus
    evaluated_at: datetime | None
    finalized_at: datetime | None
    finalized_by: int | None
    checks: list[GraduationCheckResponse]
    created_at: datetime
    updated_at: datetime


class GraduationEligibilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    track_id: int
    overall_score: float
    is_eligible: bool
    status: GraduationStatus
    evaluated_at: datetime
    gate_checks: list[GraduationGateResponse]
    finalized_result: GraduationResultResponse | None = None
