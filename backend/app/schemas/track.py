from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
