from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
)

from app.models.submission import SubmissionStatus
from app.schemas.submission_file import SubmissionFileResponse

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

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        parsed_url = TypeAdapter(AnyHttpUrl).validate_python(value)
        if parsed_url.host.casefold() != "github.com":
            raise ValueError("github_url must belong to github.com")

        return str(parsed_url)


class SubmissionCreate(SubmissionBase):
    assignment_id: int


class SubmissionUpdate(SubmissionBase):
    status: Literal["SUBMITTED"] | None = None


class SubmissionReviewCreate(BaseModel):
    feedback: str
    score: int | None = None
    resulting_status: SubmissionStatus


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


class SubmissionReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback: str
    score: int | None = None
    resulting_state: SubmissionStatus = Field(validation_alias="resulting_status")
    reviewed_at: datetime = Field(validation_alias="created_at")


class SubmissionDetailResponse(SubmissionResponse):
    files: list[SubmissionFileResponse]
    reviews: list[SubmissionReviewResponse]
