from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubmissionFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: int
    file_name: str
    file_url: str
    file_size_bytes: int | None = Field(validation_alias="file_size")
    file_type: str
    created_at: datetime
