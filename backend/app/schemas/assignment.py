from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Difficulty = Literal["beginner", "intermediate", "advanced"]


class AssignmentBase(BaseModel):
    track_id: int | None = None
    module_id: int | None = None
    lesson_id: int | None = None
    title: str
    description: str
    instructions: str
    difficulty: Difficulty
    ordering: int = 0
    is_mandatory: bool = True
    is_active: bool = True
    due_days: int | None = None
    estimated_minutes: int | None = None
    evaluation_config: dict[str, Any] | None = None


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    track_id: int | None = None
    module_id: int | None = None
    lesson_id: int | None = None
    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    difficulty: Difficulty | None = None
    ordering: int | None = None
    is_mandatory: bool | None = None
    is_active: bool | None = None
    due_days: int | None = None
    estimated_minutes: int | None = None
    evaluation_config: dict[str, Any] | None = None


class AssignmentResponse(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
