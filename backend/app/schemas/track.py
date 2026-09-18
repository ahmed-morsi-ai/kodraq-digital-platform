from __future__ import annotations

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
    content: str | None = None
    video_url: str | None = None
    ordering: int = 0


class LessonCreate(LessonBase):
    module_id: int


class Lesson(LessonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int


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
    description: str | None = None
    is_active: bool = True
    ordering: int = 0


class TrackCreate(TrackBase):
    pass


class Track(TrackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    modules: list[TrackModule] = Field(default_factory=list)


class TrackSummary(TrackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TrackCurriculum(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    ordering: int
    modules: list[TrackModule] = Field(default_factory=list)
