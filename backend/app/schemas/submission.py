from __future__ import annotations

from datetime import datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
)

from app.models.submission import SubmissionStatus
from app.schemas.submission_file import SubmissionFileResponse


class SubmissionBase(BaseModel):
    content: str | None = None
    github_url: str | None = Field(default=None, max_length=512)
    file_path_or_url: str | None = Field(default=None, max_length=1024)


class SubmissionInput(SubmissionBase):
    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        match = re.fullmatch(
            r"https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/([A-Za-z0-9_.-]{1,100})/?",
            value,
            flags=re.IGNORECASE | re.ASCII,
        )
        if match is None or match[2] in {".", "..", ".git"}:
            raise ValueError(
                "Use a GitHub repository URL: https://github.com/owner/repository"
            )
        return f"https://github.com/{match[1]}/{match[2]}"


class SubmissionCreate(SubmissionInput):
    model_config = ConfigDict(extra="forbid")

    assignment_id: PositiveInt


class SubmissionUpdate(SubmissionInput):
    model_config = ConfigDict(extra="forbid")

    status: Literal["SUBMITTED"] | None = None

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("status cannot be null")
        return value


class SubmissionReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    feedback_text: str = Field(min_length=1)
    grade: int | None = Field(default=None, strict=True, ge=-(2**31), le=2**31 - 1)
    status_transition: SubmissionStatus

    @field_validator("status_transition")
    @classmethod
    def validate_review_state(cls, value: SubmissionStatus) -> SubmissionStatus:
        if value in {SubmissionStatus.DRAFT, SubmissionStatus.SUBMITTED}:
            raise ValueError("Reviews must select a review state or decision")
        return value


class SubmissionResponse(SubmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    user_id: int
    status: SubmissionStatus
    grade: int | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SubmissionReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: int
    reviewer_id: int | None
    feedback_text: str
    grade: int | None = Field(validation_alias="score")
    status_transition: SubmissionStatus
    created_at: datetime


class SubmissionAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submitted_at: datetime


class SubmissionDetailResponse(SubmissionResponse):
    attempts: list[SubmissionAttemptResponse]
    files: list[SubmissionFileResponse]
    reviews: list[SubmissionReviewResponse]
