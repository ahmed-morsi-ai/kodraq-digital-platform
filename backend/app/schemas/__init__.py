from __future__ import annotations

from app.schemas.enrollment import (
    Enrollment,
    EnrollmentCreate,
    EnrollmentDetail,
    EnrollmentUpdate,
    StudentProgress,
    StudentProgressCreate,
    StudentProgressDetail,
    StudentProgressUpdate,
)
from app.schemas.role import Role, RoleCreate, RoleUpdate
from app.schemas.token import Token, TokenPayload
from app.schemas.track import (
    Lesson,
    LessonCreate,
    Resource,
    ResourceCreate,
    Track,
    TrackCreate,
    TrackCurriculum,
    TrackModule,
    TrackModuleCreate,
    TrackSummary,
)
from app.schemas.user import User, UserCreate, UserInDB, UserUpdate

__all__ = [
    "Role",
    "RoleCreate",
    "RoleUpdate",
    "Token",
    "TokenPayload",
    "User",
    "UserCreate",
    "UserInDB",
    "UserUpdate",
    "Resource",
    "ResourceCreate",
    "Lesson",
    "LessonCreate",
    "TrackModule",
    "TrackModuleCreate",
    "Track",
    "TrackCreate",
    "TrackSummary",
    "TrackCurriculum",
    "Enrollment",
    "EnrollmentCreate",
    "EnrollmentUpdate",
    "EnrollmentDetail",
    "StudentProgress",
    "StudentProgressCreate",
    "StudentProgressUpdate",
    "StudentProgressDetail",
]
