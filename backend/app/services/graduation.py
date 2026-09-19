from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.assignment import Assignment
from app.models.enrollment import Enrollment, StudentProgress
from app.models.final_project import TrainingProject
from app.models.project_submission import ProjectSubmission
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt, QuizAttemptStatus
from app.models.submission import Submission, SubmissionStatus
from app.models.track import Lesson, TrackModule

CURRICULUM_COMPLETION_THRESHOLD = 100.0
MANDATORY_ASSIGNMENT_THRESHOLD = 100.0
QUIZ_AVERAGE_THRESHOLD = 70.0
FINAL_PROJECT_THRESHOLD = 75.0
OVERALL_SCORE_THRESHOLD = 75.0
CRITICAL_FAILURE_THRESHOLD = 0.0


@dataclass(frozen=True)
class GateResult:
    gate_key: str
    passed: bool
    actual_value: float
    required_value: float
    failure_reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraduationCalculation:
    overall_score: float
    is_eligible: bool
    status: str
    gates: list[GateResult]


def _curriculum_completion(
    db: Session,
    *,
    user_id: int,
    track_id: int,
) -> tuple[float, dict[str, Any]]:
    lesson_ids = list(
        db.execute(
            select(Lesson.id)
            .join(TrackModule, Lesson.module_id == TrackModule.id)
            .where(TrackModule.track_id == track_id)
        ).scalars()
    )
    if not lesson_ids:
        return 100.0, {"lessons": 0, "completed_lessons": 0}

    progress_rows = db.execute(
        select(
            StudentProgress.lesson_id,
            StudentProgress.progress_percentage,
        )
        .join(
            Enrollment,
            StudentProgress.enrollment_id == Enrollment.id,
        )
        .where(
            Enrollment.user_id == user_id,
            Enrollment.track_id == track_id,
            StudentProgress.lesson_id.in_(lesson_ids),
        )
    ).all()
    progress_by_lesson = {
        lesson_id: progress for lesson_id, progress in progress_rows
    }
    total_progress = sum(
        progress_by_lesson.get(lesson_id, 0) for lesson_id in lesson_ids
    )
    completed_lessons = sum(
        progress_by_lesson.get(lesson_id, 0) >= 100 for lesson_id in lesson_ids
    )
    return round(total_progress / len(lesson_ids), 2), {
        "lessons": len(lesson_ids),
        "completed_lessons": completed_lessons,
    }


def _track_assignment_filter(track_id: int):
    return or_(
        Assignment.track_id == track_id,
        Assignment.module.has(TrackModule.track_id == track_id),
        Assignment.lesson.has(
            Lesson.module.has(TrackModule.track_id == track_id)
        ),
    )


def _mandatory_assignment_score(
    db: Session,
    *,
    user_id: int,
    track_id: int,
) -> tuple[float, dict[str, Any]]:
    assignments = list(
        db.execute(
            select(Assignment.id).where(
                Assignment.is_active.is_(True),
                Assignment.is_mandatory.is_(True),
                _track_assignment_filter(track_id),
            )
        ).scalars()
    )
    if not assignments:
        return 100.0, {"total": 0, "passed": 0}

    passed = db.execute(
        select(func.count(func.distinct(Submission.assignment_id)))
        .where(
            Submission.user_id == user_id,
            Submission.assignment_id.in_(assignments),
            Submission.status == SubmissionStatus.APPROVED.value,
        )
    ).scalar_one()
    return round((passed / len(assignments)) * 100, 2), {
        "total": len(assignments),
        "passed": passed,
    }


def _quiz_average(
    db: Session,
    *,
    user_id: int,
    track_id: int,
) -> tuple[float, dict[str, Any]]:
    quiz_filter = or_(
        Quiz.track_id == track_id,
        Quiz.lesson.has(
            Lesson.module.has(TrackModule.track_id == track_id)
        ),
    )
    quiz_ids = list(
        db.execute(
            select(Quiz.id).where(Quiz.is_active.is_(True), quiz_filter)
        ).scalars()
    )
    if not quiz_ids:
        return 100.0, {"quizzes": 0, "completed_quizzes": 0}

    best_scores = db.execute(
        select(
            QuizAttempt.quiz_id,
            func.max(QuizAttempt.score),
        )
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id.in_(quiz_ids),
            QuizAttempt.status == QuizAttemptStatus.COMPLETED.value,
        )
        .group_by(QuizAttempt.quiz_id)
    ).all()
    scores = {quiz_id: score for quiz_id, score in best_scores if score is not None}
    average = sum(scores.values()) / len(quiz_ids)
    return round(average, 2), {
        "quizzes": len(quiz_ids),
        "completed_quizzes": len(scores),
    }


def _rubric_score(
    rubric: dict[str, Any] | None,
    scores: dict[str, Any] | None,
) -> float:
    if not scores:
        return 0.0
    numeric_scores = {
        key: float(value)
        for key, value in scores.items()
        if isinstance(value, int | float)
    }
    if not numeric_scores:
        return 0.0
    if rubric:
        weights = {
            key: float(value)
            for key, value in rubric.items()
            if key in numeric_scores and isinstance(value, int | float)
        }
        weight_total = sum(weights.values())
        if weight_total:
            return round(
                sum(numeric_scores[key] * weight for key, weight in weights.items())
                / weight_total,
                2,
            )
    return round(sum(numeric_scores.values()) / len(numeric_scores), 2)


def _final_project_score(
    db: Session,
    *,
    user_id: int,
    track_id: int,
) -> tuple[float, dict[str, Any]]:
    projects = list(
        db.execute(
            select(TrainingProject).where(
                TrainingProject.track_id == track_id,
                TrainingProject.is_active.is_(True),
            )
        ).scalars()
    )
    if not projects:
        return 0.0, {"projects": 0, "approved_projects": 0}

    project_ids = [project.id for project in projects]
    submissions = list(
        db.execute(
            select(ProjectSubmission)
            .options(selectinload(ProjectSubmission.reviews))
            .where(
                ProjectSubmission.user_id == user_id,
                ProjectSubmission.project_id.in_(project_ids),
                ProjectSubmission.status == "APPROVED",
            )
        ).scalars()
    )
    score_by_project: dict[int, float] = {}
    project_by_id = {project.id: project for project in projects}
    for submission in submissions:
        approved_reviews = [
            review
            for review in submission.reviews
            if review.status_decision == "APPROVED"
        ]
        if not approved_reviews:
            continue
        latest_review = approved_reviews[-1]
        score_by_project[submission.project_id] = _rubric_score(
            project_by_id[submission.project_id].evaluation_rubric,
            latest_review.rubric_scores,
        )

    score = sum(score_by_project.values()) / len(projects)
    return round(score, 2), {
        "projects": len(projects),
        "approved_projects": len(score_by_project),
    }


def calculate_graduation(
    db: Session,
    *,
    user_id: int,
    track_id: int,
) -> GraduationCalculation:
    curriculum, curriculum_details = _curriculum_completion(
        db,
        user_id=user_id,
        track_id=track_id,
    )
    assignments, assignment_details = _mandatory_assignment_score(
        db,
        user_id=user_id,
        track_id=track_id,
    )
    quizzes, quiz_details = _quiz_average(
        db,
        user_id=user_id,
        track_id=track_id,
    )
    final_project, final_project_details = _final_project_score(
        db,
        user_id=user_id,
        track_id=track_id,
    )
    overall = round(
        (curriculum + assignments + quizzes + final_project) / 4,
        2,
    )

    gates = [
        GateResult(
            "curriculum_completion",
            curriculum >= CURRICULUM_COMPLETION_THRESHOLD,
            curriculum,
            CURRICULUM_COMPLETION_THRESHOLD,
            None
            if curriculum >= CURRICULUM_COMPLETION_THRESHOLD
            else "Curriculum completion must reach 100%.",
            curriculum_details,
        ),
        GateResult(
            "mandatory_assignments",
            assignments >= MANDATORY_ASSIGNMENT_THRESHOLD,
            assignments,
            MANDATORY_ASSIGNMENT_THRESHOLD,
            None
            if assignments >= MANDATORY_ASSIGNMENT_THRESHOLD
            else "All mandatory assignments must be passed.",
            assignment_details,
        ),
        GateResult(
            "quiz_average",
            quizzes >= QUIZ_AVERAGE_THRESHOLD,
            quizzes,
            QUIZ_AVERAGE_THRESHOLD,
            None
            if quizzes >= QUIZ_AVERAGE_THRESHOLD
            else "Quiz average must be at least 70%.",
            quiz_details,
        ),
        GateResult(
            "final_project_score",
            final_project >= FINAL_PROJECT_THRESHOLD,
            final_project,
            FINAL_PROJECT_THRESHOLD,
            None
            if final_project >= FINAL_PROJECT_THRESHOLD
            else "Final project score must be at least 75%.",
            final_project_details,
        ),
        GateResult(
            "overall_score",
            overall >= OVERALL_SCORE_THRESHOLD,
            overall,
            OVERALL_SCORE_THRESHOLD,
            None
            if overall >= OVERALL_SCORE_THRESHOLD
            else "Overall score must be at least 75%.",
            {},
        ),
        GateResult(
            "critical_failures",
            True,
            0.0,
            CRITICAL_FAILURE_THRESHOLD,
            None,
            {
                "source": (
                    "No critical-failure records exist in the current domain model."
                )
            },
        ),
    ]
    eligible = all(gate.passed for gate in gates)
    return GraduationCalculation(
        overall_score=overall,
        is_eligible=eligible,
        status="GRADUATED" if eligible else "FAILED_GATES",
        gates=gates,
    )
