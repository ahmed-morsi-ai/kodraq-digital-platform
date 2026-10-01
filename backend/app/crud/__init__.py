from __future__ import annotations

from app.crud.base import CRUDBase
from app.crud.crud_assignment import (
    CRUDAssignment,
    assignment,
    create_assignment,
    delete_assignment,
    get_assignment,
    get_assignments_by_context,
    update_assignment,
)
from app.crud.crud_enrollment import (
    CRUDEnrollment,
    CRUDStudentProgress,
    enrollment,
    student_progress,
)
from app.crud.crud_project_submission import (
    CRUDProjectSubmission,
    project_submission,
)
from app.crud.crud_quiz import (
    CRUDQuestion,
    CRUDQuiz,
    question,
    quiz,
)
from app.crud.crud_quiz_attempt import (
    CRUDQuizAttempt,
    quiz_attempt,
)
from app.crud.crud_role import role
from app.crud.crud_submission import (
    CRUDSubmission,
    submission,
)
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
    "CRUDAssignment",
    "CRUDTrack",
    "CRUDTrackModule",
    "CRUDLesson",
    "CRUDResource",
    "CRUDEnrollment",
    "CRUDStudentProgress",
    "CRUDSubmission",
    "track",
    "track_module",
    "lesson",
    "resource",
    "enrollment",
    "student_progress",
    "assignment",
    "create_assignment",
    "get_assignment",
    "get_assignments_by_context",
    "update_assignment",
    "delete_assignment",
    "submission",
    "CRUDQuestion",
    "CRUDQuiz",
    "question",
    "quiz",
    "CRUDQuizAttempt",
    "quiz_attempt",
    "CRUDProjectSubmission",
    "project_submission",
    "role",
    "user",
]
