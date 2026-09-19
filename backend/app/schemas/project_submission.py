from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.project_submission import ProjectSubmissionStatus

ProjectReviewDecision = Literal[
    "UNDER_REVIEW",
    "CHANGES_REQUIRED",
    "APPROVED",
    "REJECTED",
]


class ProjectSubmissionBase(BaseModel):
    repository_url: str | None = None
    live_url: str | None = None
    documentation_url: str | None = None


class ProjectSubmissionCreate(ProjectSubmissionBase):
    project_id: int


class ProjectSubmissionUpdate(ProjectSubmissionBase):
    pass


class ProjectReviewCreate(BaseModel):
    rubric_scores: dict[str, float] | None = None
    feedback: str | None = None
    status_decision: ProjectReviewDecision


class ProjectReviewResponse(ProjectReviewCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    reviewer_id: int
    created_at: datetime
    updated_at: datetime


class ProjectSubmissionResponse(ProjectSubmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    status: ProjectSubmissionStatus
    created_at: datetime
    updated_at: datetime
    reviews: list[ProjectReviewResponse] = Field(default_factory=list)
