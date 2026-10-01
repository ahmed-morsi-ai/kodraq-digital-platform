from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    ValidationInfo,
    field_validator,
)

Difficulty = Literal["beginner", "intermediate", "advanced"]


class AssignmentBase(BaseModel):
    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None
    title: str = Field(max_length=255)
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
    model_config = ConfigDict(extra="forbid")


class AssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: PositiveInt | None = None
    module_id: PositiveInt | None = None
    lesson_id: PositiveInt | None = None
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    instructions: str | None = None
    difficulty: Difficulty | None = None
    ordering: int | None = None
    is_mandatory: bool | None = None
    is_active: bool | None = None
    due_days: int | None = None
    estimated_minutes: int | None = None
    evaluation_config: dict[str, Any] | None = None

    @field_validator(
        "title",
        "description",
        "instructions",
        "difficulty",
        "ordering",
        "is_mandatory",
        "is_active",
    )
    @classmethod
    def reject_explicit_null(cls, value: Any, info: ValidationInfo) -> Any:
        # Omitted PATCH fields keep their defaults without running this validator.
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value


class AssignmentResponse(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
