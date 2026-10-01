from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StrictBool

from app.models.quiz_attempt import QuizAttemptStatus


class QuizAnswerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: PositiveInt
    selected_option_id: PositiveInt | None = None


class QuizAnswerResponse(QuizAnswerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_id: int
    is_correct: bool


class QuizAttemptSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[QuizAnswerCreate] = Field(default_factory=list)
    is_flagged: StrictBool = False
    flag_reason: str | None = Field(default=None, max_length=255)


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    user_id: int
    score: float | None = None
    passed: bool
    is_flagged: bool
    flag_reason: str | None = None
    status: QuizAttemptStatus
    started_at: datetime
    completed_at: datetime | None = None
    deadline_at: datetime | None = None
    passing_score: int | None = None
    created_at: datetime
    updated_at: datetime
    answers: list[QuizAnswerResponse] = Field(default_factory=list)
