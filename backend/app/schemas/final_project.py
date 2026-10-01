from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.project_submission import ProjectSubmissionStatus
from app.schemas.submission import SubmissionInput

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Score = Annotated[int, Field(strict=True, ge=0, le=100)]
Ordering = Annotated[int, Field(strict=True, ge=0, le=2**31 - 1)]
ReviewDecision = Literal["UNDER_REVIEW", "CHANGES_REQUIRED", "APPROVED", "REJECTED"]


class ProjectRequirementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: NonBlank
    is_mandatory: StrictBool = True
    order: Ordering = 0


class ProjectRequirementResponse(ProjectRequirementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class TrainingProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    description: str | None = None
    passing_score: Score = 75
    is_active: StrictBool = True
    requirements: list[ProjectRequirementCreate] = Field(default_factory=list)


class TrainingProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title | None = None
    description: str | None = None
    passing_score: Score | None = None
    is_active: StrictBool | None = None
    requirements: list[ProjectRequirementCreate] | None = None

    @field_validator("title", "passing_score", "is_active", "requirements")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class ProjectReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: Score | None = None
    feedback: NonBlank
    status_decision: ReviewDecision | None = None

    @model_validator(mode="after")
    def require_grade(self):
        if self.status_decision in {None, "APPROVED"} and self.score is None:
            raise ValueError("A score is required for grading or approval")
        return self


class ProjectReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    submission_id: int
    reviewer_id: int
    score: int | None
    feedback: str | None
    status_decision: ReviewDecision
    created_at: datetime
    updated_at: datetime


class ProjectSubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    github_url: str | None = Field(default=None, max_length=512)
    live_url: str | None = Field(default=None, max_length=512)
    file_url: str | None = Field(default=None, max_length=512)
    student_notes: str | None = None

    @field_validator("github_url")
    @classmethod
    def repository_url(cls, value):
        return SubmissionInput.validate_github_url(value)

    @field_validator("live_url", "file_url")
    @classmethod
    def web_url(cls, value):
        if value is None:
            return value
        if (
            not value
            or any(char.isspace() or ord(char) < 32 for char in value)
            or "\\" in value
        ):
            raise ValueError(
                "Use an absolute HTTP or HTTPS URL without whitespace or credentials"
            )
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as error:
            raise ValueError("Invalid URL") from error
        if (
            parsed.scheme.lower() not in {"https", "http"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or (port is not None and port < 1)
        ):
            raise ValueError("Use an absolute HTTP or HTTPS URL without credentials")
        return value


class ProjectSubmissionUpdate(ProjectSubmissionCreate):
    status: Literal["SUBMITTED"] | None = None

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value):
        if value is None:
            raise ValueError("status cannot be null")
        return value


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
