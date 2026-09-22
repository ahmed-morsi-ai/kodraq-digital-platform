from app.models.ai import AIRequestLog
from app.models.assignment import Assignment
from app.models.base import Base
from app.models.enrollment import Enrollment, StudentProgress
from app.models.final_project import ProjectRequirement, TrainingProject
from app.models.graduation import (
    GraduationEvaluation,
    GraduationEvaluationStatus,
    GraduationGateCheck,
)
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.project_submission import (
    ProjectReview,
    ProjectSubmission,
    ProjectSubmissionStatus,
)
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAnswer, QuizAttempt, QuizAttemptStatus
from app.models.role import Role
from app.models.submission import (
    Submission,
    SubmissionFile,
    SubmissionReview,
    SubmissionStatus,
)
from app.models.track import Lesson, Resource, Track, TrackModule
from app.models.track_assignment_config import TrackAssignmentConfig
from app.models.track_instructor import TrackInstructor
from app.models.user import User

__all__ = [
    "Base",
    "Assignment",
    "AIRequestLog",
    "Role",
    "User",
    "Track",
    "TrackModule",
    "Lesson",
    "Resource",
    "TrackAssignmentConfig",
    "TrackInstructor",
    "Enrollment",
    "StudentProgress",
    "Submission",
    "SubmissionStatus",
    "SubmissionFile",
    "SubmissionReview",
    "Question",
    "QuestionOption",
    "Quiz",
    "QuizQuestion",
    "QuizAttempt",
    "QuizAnswer",
    "QuizAttemptStatus",
    "TrainingProject",
    "ProjectRequirement",
    "ProjectSubmission",
    "ProjectReview",
    "ProjectSubmissionStatus",
    "GraduationEvaluation",
    "GraduationGateCheck",
    "GraduationEvaluationStatus",
    "KnowledgeDocument",
    "KnowledgeChunk",
]
