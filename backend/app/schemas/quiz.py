from __future__ import annotations

from datetime import datetime

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    StrictBool,
    field_validator,
)

PositiveValue = Annotated[int, Field(strict=True, ge=1, le=2**31 - 1)]
Ordering = Annotated[int, Field(strict=True, ge=0, le=2**31 - 1)]
Percentage = Annotated[int, Field(strict=True, ge=0, le=100)]


class QuizInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QuestionOptionBase(QuizInput):
    text: str = Field(min_length=1)
    is_correct: StrictBool = False


class QuestionOptionCreate(QuestionOptionBase):
    pass


class QuestionOptionResponse(QuestionOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int


class QuestionBase(QuizInput):
    difficulty: PositiveValue = 1
    text: str = Field(min_length=1)
    question_type: str = Field(min_length=1, max_length=32)
    points: PositiveValue = 1
    explanation: str | None = None
    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None


class QuestionCreate(QuestionBase):
    options: list[QuestionOptionCreate] = Field(default_factory=list)


class QuestionUpdate(QuizInput):
    difficulty: PositiveValue | None = None
    text: str | None = Field(default=None, min_length=1)
    question_type: str | None = Field(default=None, min_length=1, max_length=32)
    points: PositiveValue | None = None
    explanation: str | None = None
    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None
    options: list[QuestionOptionCreate] | None = None

    @field_validator("text", "question_type", "difficulty", "points", "options")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class QuestionResponse(QuestionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    options: list[QuestionOptionResponse] = Field(default_factory=list)


class QuizQuestionBase(QuizInput):
    question_id: PositiveInt
    ordering: Ordering = 0


class QuizQuestionCreate(QuizQuestionBase):
    pass


class QuizQuestionResponse(QuizQuestionBase):
    model_config = ConfigDict(from_attributes=True)

    question: QuestionResponse


class QuizBase(QuizInput):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None
    passing_score: Percentage
    time_limit_minutes: PositiveValue | None = None
    is_active: StrictBool = True


def unique_questions(questions):
    if len({link.question_id for link in questions}) != len(questions):
        raise ValueError("A question may only appear once in a quiz")
    return questions


class QuizCreate(QuizBase):
    questions: list[QuizQuestionCreate] = Field(default_factory=list)

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, value):
        return unique_questions(value)


class QuizUpdate(QuizInput):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None
    passing_score: Percentage | None = None
    time_limit_minutes: PositiveValue | None = None
    is_active: StrictBool | None = None
    questions: list[QuizQuestionCreate] | None = None

    @field_validator("title", "passing_score", "is_active", "questions")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, value):
        return unique_questions(value)


class QuizResponse(QuizBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    questions: list[QuizQuestionResponse] = Field(
        default_factory=list,
        validation_alias="question_links",
    )


class StudentQuestionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    text: str


class StudentQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    question_type: str
    points: int
    options: list[StudentQuestionOptionResponse] = Field(default_factory=list)


class StudentQuizQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    ordering: int
    question: StudentQuestionResponse


class StudentQuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None
    passing_score: int
    time_limit_minutes: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    questions: list[StudentQuizQuestionResponse] = Field(
        default_factory=list,
        validation_alias="question_links",
    )


class QuizResultQuestionResponse(BaseModel):
    question_id: int
    question_text: str
    points: int
    selected_option_id: int | None = None
    selected_option_text: str | None = None
    correct_option_ids: list[int] = Field(default_factory=list)
    correct_option_texts: list[str] = Field(default_factory=list)
    is_correct: bool


class QuizResultResponse(BaseModel):
    attempt_id: int
    quiz_id: int
    score: float
    max_score: int
    earned_points: int
    percentage: float
    passed: bool
    time_taken_seconds: float
    is_flagged: bool
    flag_reason: str | None = None
    questions: list[QuizResultQuestionResponse] = Field(default_factory=list)
