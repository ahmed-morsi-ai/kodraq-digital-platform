from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.quiz_attempt import QuizAttemptStatus


class QuizAnswerCreate(BaseModel):
    question_id: int
    selected_option_id: int | None = None


class QuizAnswerResponse(QuizAnswerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_id: int
    is_correct: bool


class QuizAttemptSubmit(BaseModel):
    answers: list[QuizAnswerCreate] = Field(default_factory=list)


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    user_id: int
    score: float | None = None
    passed: bool
    status: QuizAttemptStatus
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    answers: list[QuizAnswerResponse] = Field(default_factory=list)
