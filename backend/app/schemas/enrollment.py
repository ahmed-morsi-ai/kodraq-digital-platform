from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.track import CurriculumLesson, TrackSummary


class StudentProgressBase(BaseModel):
    lesson_id: int
    status: str = "not_started"
    progress_percentage: int = Field(
        default=0,
        ge=0,
        le=100,
    )


class StudentProgressCreate(StudentProgressBase):
    enrollment_id: int


class StudentProgressUpdate(BaseModel):
    status: str | None = None
    progress_percentage: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class StudentProgress(StudentProgressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    enrollment_id: int
    started_at: datetime | None = None
    completed_at: datetime | None = None


class StudentProgressDetail(StudentProgress):
    lesson: CurriculumLesson | None = None


class EnrollmentBase(BaseModel):
    track_id: int
    status: str = "active"


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    status: str | None = None
    completed_at: datetime | None = None


class Enrollment(EnrollmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    enrolled_at: datetime
    completed_at: datetime | None = None


class EnrollmentDetail(Enrollment):
    track: TrackSummary | None = None
    progress: list[StudentProgressDetail] = Field(
        default_factory=list,
    )


class AdminEnrollmentStatusUpdate(BaseModel):
    status: Literal["active", "cancelled"]


class AdminEnrollmentResponse(BaseModel):
    id: int
    user_id: int
    student_name: str
    student_email: str
    track_id: int
    track_name: str
    status: str
    enrolled_at: datetime
