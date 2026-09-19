from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionOptionBase(BaseModel):
    text: str
    is_correct: bool = False


class QuestionOptionCreate(QuestionOptionBase):
    pass


class QuestionOptionResponse(QuestionOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int


class QuestionBase(BaseModel):
    text: str
    question_type: str
    points: int = 1
    explanation: str | None = None
    track_id: int | None = None
    lesson_id: int | None = None


class QuestionCreate(QuestionBase):
    options: list[QuestionOptionCreate] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    text: str | None = None
    question_type: str | None = None
    points: int | None = None
    explanation: str | None = None
    track_id: int | None = None
    lesson_id: int | None = None
    options: list[QuestionOptionCreate] | None = None


class QuestionResponse(QuestionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    options: list[QuestionOptionResponse] = Field(default_factory=list)


class QuizQuestionBase(BaseModel):
    question_id: int
    ordering: int = 0


class QuizQuestionCreate(QuizQuestionBase):
    pass


class QuizQuestionResponse(QuizQuestionBase):
    model_config = ConfigDict(from_attributes=True)

    question: QuestionResponse


class QuizBase(BaseModel):
    title: str
    description: str | None = None
    track_id: int | None = None
    lesson_id: int | None = None
    passing_score: int
    time_limit_minutes: int | None = None
    is_active: bool = True


class QuizCreate(QuizBase):
    questions: list[QuizQuestionCreate] = Field(default_factory=list)


class QuizUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    track_id: int | None = None
    lesson_id: int | None = None
    passing_score: int | None = None
    time_limit_minutes: int | None = None
    is_active: bool | None = None
    questions: list[QuizQuestionCreate] | None = None


class QuizResponse(QuizBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    questions: list[QuizQuestionResponse] = Field(
        default_factory=list,
        validation_alias="question_links",
    )
