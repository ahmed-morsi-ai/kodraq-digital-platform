from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LateSubmissionPolicy = Literal["ACCEPTED", "REJECTED", "PENALIZED"]


class TrackAssignmentConfigUpdate(BaseModel):
    passing_score_threshold: int | None = Field(default=None, ge=0, le=100)
    max_retries: int | None = Field(default=None, ge=0)
    is_strict_progression: bool | None = None
    late_submission_policy: LateSubmissionPolicy | None = None


class TrackAssignmentConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_id: int
    passing_score_threshold: int
    max_retries: int
    is_strict_progression: bool
    late_submission_policy: LateSubmissionPolicy
    created_at: datetime
    updated_at: datetime
