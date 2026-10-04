from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class ResourceBase(BaseModel):
    title: str
    file_url: str
    resource_type: str = "document"


class ResourceCreate(ResourceBase):
    pass


class Resource(ResourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int


class LessonBase(BaseModel):
    title: str
    description: str | None = None
    content: str | None = None
    video_url: str | None = None
    ordering: int = 0


class LessonCreate(LessonBase):
    module_id: int


class LessonQuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str]
    correct_index: int
    explanation: str


class LessonQuizPrompt(BaseModel):
    id: int
    question: str
    options: list[str]


class LessonQuizAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: PositiveInt
    selected_index: int = Field(ge=0)


class LessonQuizSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[LessonQuizAnswer] = Field(min_length=1, max_length=100)

    @field_validator("answers")
    @classmethod
    def unique_question_answers(cls, answers: list[LessonQuizAnswer]):
        question_ids = [answer.question_id for answer in answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each quiz question must have one answer.")
        return answers


class LessonQuizResultAnswer(BaseModel):
    question_id: int
    selected_index: int
    correct_index: int
    is_correct: bool
    explanation: str


class LessonQuizResult(BaseModel):
    score: int
    total: int
    percentage: int
    answers: list[LessonQuizResultAnswer]


class Lesson(LessonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    quiz_data: list[LessonQuizQuestion] | None = None


class TrackModuleBase(BaseModel):
    title: str
    description: str | None = None
    ordering: int = 0
    is_active: bool = True


class TrackModuleCreate(TrackModuleBase):
    track_id: int


class TrackModule(TrackModuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_id: int
    lessons: list[Lesson] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)


class TrackBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    ordering: int = 0
    is_active: bool = True
    
    # أضف هذه الحقول الثلاثة لتمرير بيانات الدفع للواجهة الأمامية
    is_premium: bool = False
    price: Optional[float] = None
    currency: str = "EGP"


class TrackCreate(TrackBase):
    pass


class Track(TrackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    modules: list[TrackModule] = Field(default_factory=list)


class TrackSummary(TrackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TrackCurriculum(TrackBase):
    id: int
    is_premium: bool = False
    price: Optional[float] = None
    currency: str = "EGP"
    modules: list[TrackModule] = []
    
    class Config:
        from_attributes = True


class CurriculumResource(BaseModel):
    id: int
    module_id: int
    title: str
    file_url: str | None = None
    resource_type: str


class CurriculumLesson(BaseModel):
    id: int
    module_id: int
    title: str
    description: str | None = None
    content: str | None = None
    video_url: str | None = None
    ordering: int
    quiz_data: list[LessonQuizPrompt] | None = None


class CurriculumModule(BaseModel):
    id: int
    track_id: int
    title: str
    description: str | None = None
    ordering: int
    is_active: bool
    lessons: list[CurriculumLesson] = Field(default_factory=list)
    resources: list[CurriculumResource] = Field(default_factory=list)


class TrackCurriculumPreview(TrackBase):
    id: int
    modules: list[CurriculumModule] = Field(default_factory=list)
