from __future__ import annotations

from app.crud.base import CRUDBase
from app.crud.crud_enrollment import (
    CRUDEnrollment,
    CRUDStudentProgress,
    enrollment,
    student_progress,
)
from app.crud.crud_role import role
from app.crud.crud_track import (
    CRUDLesson,
    CRUDResource,
    CRUDTrack,
    CRUDTrackModule,
    lesson,
    resource,
    track,
    track_module,
)
from app.crud.crud_user import user

__all__ = [
    "CRUDBase",
    "CRUDTrack",
    "CRUDTrackModule",
    "CRUDLesson",
    "CRUDResource",
    "CRUDEnrollment",
    "CRUDStudentProgress",
    "track",
    "track_module",
    "lesson",
    "resource",
    "enrollment",
    "student_progress",
    "role",
    "user",
]
