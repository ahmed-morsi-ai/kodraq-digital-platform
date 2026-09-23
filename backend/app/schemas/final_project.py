from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.project_submission import ProjectSubmissionStatus


class ProjectRequirementCreate(BaseModel):
    description: str
    is_mandatory: bool = True
    order: int = 0


class ProjectRequirementResponse(ProjectRequirementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int


class TrainingProjectCreate(BaseModel):
    title: str
    description: str | None = None
    passing_score: int = 75
    is_active: bool = True
    requirements: list[ProjectRequirementCreate] = Field(default_factory=list)


class TrainingProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    passing_score: int | None = None
    is_active: bool | None = None
    requirements: list[ProjectRequirementCreate] | None = None


class ProjectReviewCreate(BaseModel):
    score: int
    feedback: str


class ProjectReviewResponse(ProjectReviewCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    reviewer_id: int
    created_at: datetime
    updated_at: datetime


class ProjectSubmissionCreate(BaseModel):
    github_url: str | None = None
    live_url: str | None = None
    file_url: str | None = None
    student_notes: str | None = None


class ProjectSubmissionUpdate(ProjectSubmissionCreate):
    status: Literal["SUBMITTED"] | None = None


class ProjectSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    student_id: int
    github_url: str | None
    live_url: str | None
    file_url: str | None
    student_notes: str | None
    status: ProjectSubmissionStatus
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    reviews: list[ProjectReviewResponse] = Field(default_factory=list)


class TrainingProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_id: int
    title: str
    description: str | None
    passing_score: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    requirements: list[ProjectRequirementResponse] = Field(default_factory=list)
