from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.submission import SubmissionStatus

SubmissionReviewStatus = Literal[
    "UNDER_REVIEW",
    "CHANGES_REQUIRED",
    "APPROVED",
    "REJECTED",
]


class SubmissionBase(BaseModel):
    content: str | None = None
    github_url: str | None = None
    file_path_or_url: str | None = None


class SubmissionCreate(SubmissionBase):
    assignment_id: int


class SubmissionUpdate(SubmissionBase):
    pass


class SubmissionReview(BaseModel):
    status: SubmissionReviewStatus


class SubmissionResponse(SubmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    user_id: int
    status: SubmissionStatus
    created_at: datetime
    updated_at: datetime
