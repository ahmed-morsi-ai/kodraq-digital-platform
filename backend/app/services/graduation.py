from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import math
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.crud.crud_assignment import assignment as curriculum
from app.models.assignment import Assignment
from app.models.certificate import Certificate
from app.models.enrollment import Enrollment, StudentProgress
from app.models.final_project import TrainingProject
from app.models.graduation import GraduationCheck, GraduationResult, GraduationRule
from app.models.project_submission import ProjectSubmission
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.submission import Submission, SubmissionStatus
from app.models.track import Lesson, Track, TrackModule
from app.models.track_instructor import TrackInstructor
from app.models.user import User
from app.services.final_project_access import is_admin, is_student

# Existing roadmap thresholds are floors: track rules may strengthen, never waive them.
GATE_DEFAULTS = {
    "enrollment": ("ENROLLMENT", "Active enrollment", 100),
    "curriculum_completion": ("CURRICULUM_COMPLETION", "Curriculum completion", 100),
    "mandatory_assignments": ("MANDATORY_ASSIGNMENTS", "Mandatory assignments", 100),
    "quiz_average": ("QUIZ_AVERAGE", "Quiz scores", 70),
    "final_project_score": ("FINAL_PROJECT", "Final project", 75),
    "overall_score": ("OVERALL_SCORE", "Overall score", 75),
}


@dataclass(frozen=True)
class GateResult:
    gate_key: str
    passed: bool
    actual_value: float
    required_value: float
    failure_reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    rule_id: int | None = None


@dataclass(frozen=True)
class GraduationCalculation:
    user_id: int
    track_id: int
    overall_score: float
    is_eligible: bool
    status: str
    evaluated_at: datetime
    gate_checks: list[GateResult]
    finalized_result: GraduationResult | None = None


def require_manager(db: Session, actor: User, track_id: int) -> None:
    if not actor.is_active:
        raise PermissionError("Inactive users cannot access graduation.")
    if is_admin(actor):
        return
    if not actor.role_rel or actor.role_rel.name.casefold() != "instructor":
        raise PermissionError(
            "Only admins and assigned instructors can finalize graduation."
        )
    if (
        db.scalar(
            select(TrackInstructor.track_id).where(
                TrackInstructor.track_id == track_id,
                TrackInstructor.instructor_id == actor.id,
            )
        )
        is None
    ):
        raise PermissionError("Instructor is not assigned to this track.")


def require_read(db: Session, actor: User, student_id: int, track_id: int) -> None:
    if not actor.is_active:
        raise PermissionError("Inactive users cannot access graduation.")
    if is_student(actor):
        if actor.id != student_id:
            raise PermissionError("You can only view your own graduation status.")
    else:
        require_manager(db, actor, track_id)


def _subject(db: Session, user_id: int, track_id: int):
    user, track = db.get(User, user_id), db.get(Track, track_id)
    if user is None or track is None:
        raise LookupError("Student or track not found.")
    if not is_student(user):
        raise PermissionError("Graduation is only available for students.")
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.track_id == track_id,
        )
    )
    if enrollment is None:
        raise PermissionError("The student is not enrolled in this track.")
    return user, track, enrollment


def _context(model, track_id):
    return or_(
        model.track_id == track_id,
        model.module.has(TrackModule.track_id == track_id),
        model.lesson.has(Lesson.module.has(TrackModule.track_id == track_id)),
    )


def _valid_context(db, record, track_id):
    try:
        return (
            curriculum.resolve_track_id(
                db,
                track_id=record.track_id,
                module_id=record.module_id,
                lesson_id=record.lesson_id,
            )
            == track_id
        )
    except (LookupError, ValueError):
        return False


def _valid_score(value):
    return value is not None and math.isfinite(value) and 0 <= value <= 100


def _curriculum_completion(db, enrollment, track_id):
    lessons = list(
        db.scalars(
            select(Lesson.id).join(TrackModule).where(TrackModule.track_id == track_id)
        )
    )
    progress = {
        row.lesson_id: row
        for row in db.scalars(
            select(StudentProgress).where(
                StudentProgress.enrollment_id == enrollment.id,
                StudentProgress.lesson_id.in_(lessons),
            )
        )
    }
    completed = sum(
        lesson in progress
        and progress[lesson].status == "completed"
        and progress[lesson].progress_percentage == 100
        for lesson in lessons
    )
    score = (
        sum(
            progress[item].progress_percentage if item in progress else 0
            for item in lessons
        )
        / len(lessons)
        if lessons
        else 100.0
    )
    return (
        score,
        completed == len(lessons),
        {"lessons": len(lessons), "completed_lessons": completed},
    )


def _mandatory_assignments(db, user_id, track_id):
    assignments = list(
        db.scalars(
            select(Assignment)
            .where(
                Assignment.is_active.is_(True),
                Assignment.is_mandatory.is_(True),
                _context(Assignment, track_id),
            )
            .order_by(Assignment.id)
        )
    )
    ids = [item.id for item in assignments]
    invalid = [
        item.id for item in assignments if not _valid_context(db, item, track_id)
    ]
    approved = set(
        db.scalars(
            select(Submission.assignment_id).where(
                Submission.user_id == user_id,
                Submission.assignment_id.in_(ids),
                Submission.status == SubmissionStatus.APPROVED,
            )
        )
    ) - set(invalid)
    score = 100 * len(approved) / len(ids) if ids else 100.0
    return (
        score,
        len(approved) == len(ids) and not invalid,
        {
            "total": len(ids),
            "approved": len(approved),
            "missing_assignment_ids": sorted(set(ids) - approved),
            "invalid_assignment_ids": invalid,
        },
    )


def _quiz_scores(db, user_id, track_id):
    quizzes = list(
        db.scalars(
            select(Quiz)
            .where(Quiz.is_active.is_(True), _context(Quiz, track_id))
            .order_by(Quiz.id)
        )
    )
    scores = {}
    for attempt in db.scalars(
        select(QuizAttempt).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id.in_([item.id for item in quizzes]),
            QuizAttempt.status == "COMPLETED",
        )
    ):
        if _valid_score(attempt.score):
            scores[attempt.quiz_id] = max(scores.get(attempt.quiz_id, 0), attempt.score)
    details = [
        {
            "quiz_id": quiz.id,
            "score": scores.get(quiz.id),
            "passing_score": quiz.passing_score,
            "passed": quiz.id in scores
            and scores[quiz.id] >= quiz.passing_score
            and _valid_context(db, quiz, track_id),
        }
        for quiz in quizzes
    ]
    average = (
        sum(scores.get(item.id, 0) for item in quizzes) / len(quizzes)
        if quizzes
        else 100.0
    )
    return (
        average,
        all(item["passed"] for item in details),
        {
            "quizzes": len(quizzes),
            "completed_quizzes": len(scores),
            "scores": details,
        },
    )


def _final_project_score(db, user_id, track_id):
    project = db.scalar(
        select(TrainingProject).where(
            TrainingProject.track_id == track_id, TrainingProject.is_active.is_(True)
        )
    )
    if project is None:
        return 0.0, False, 75, {"project_id": None, "submission_id": None}
    submission = db.scalar(
        select(ProjectSubmission)
        .options(selectinload(ProjectSubmission.reviews))
        .where(
            ProjectSubmission.student_id == user_id,
            ProjectSubmission.project_id == project.id,
        )
    )
    review = submission.reviews[-1] if submission and submission.reviews else None
    score = float(review.score) if review and _valid_score(review.score) else 0.0
    approved = bool(
        submission
        and submission.status == "APPROVED"
        and review
        and review.status_decision == "APPROVED"
        and _valid_score(review.score)
        and review.reviewer_id != user_id
    )
    return (
        score,
        approved,
        project.passing_score,
        {
            "project_id": project.id,
            "submission_id": submission.id if submission else None,
            "status": submission.status if submission else None,
            "review_id": review.id if review else None,
        },
    )


def _rule_key(rule):
    for key, (code, _, _) in GATE_DEFAULTS.items():
        if rule.code.casefold() in {code.casefold(), key}:
            return key
    return None


def _verified_finalization(result: GraduationResult | None) -> bool:
    return bool(
        result
        and result.status == "GRADUATED"
        and result.eligible
        and result.finalized_at is not None
        and set(GATE_DEFAULTS)
        <= {check.gate_key for check in result.checks if check.passed}
        and all(check.passed for check in result.checks)
    )


def calculate_graduation(
    db: Session, *, user_id: int, track_id: int
) -> GraduationCalculation:
    user, track, enrollment = _subject(db, user_id, track_id)
    rules = list(
        db.scalars(
            select(GraduationRule)
            .where(GraduationRule.track_id == track_id)
            .order_by(GraduationRule.ordering, GraduationRule.id)
        )
    )
    curriculum_score, curriculum_ok, curriculum_details = _curriculum_completion(
        db, enrollment, track_id
    )
    assignments, assignments_ok, assignment_details = _mandatory_assignments(
        db, user_id, track_id
    )
    quizzes, quizzes_ok, quiz_details = _quiz_scores(db, user_id, track_id)
    project, project_ok, project_threshold, project_details = _final_project_score(
        db, user_id, track_id
    )
    overall = (curriculum_score + assignments + quizzes + project) / 4
    enrollment_ok = enrollment.status == "active" and user.is_active and track.is_active
    values = {
        "enrollment": (
            100.0 if enrollment_ok else 0.0,
            enrollment_ok,
            {
                "enrollment_id": enrollment.id,
                "status": enrollment.status,
                "student_active": user.is_active,
                "track_active": track.is_active,
            },
        ),
        "curriculum_completion": (curriculum_score, curriculum_ok, curriculum_details),
        "mandatory_assignments": (assignments, assignments_ok, assignment_details),
        "quiz_average": (quizzes, quizzes_ok, quiz_details),
        "final_project_score": (project, project_ok, project_details),
        "overall_score": (
            overall,
            True,
            {
                "weights": {
                    "curriculum": 0.25,
                    "assignments": 0.25,
                    "quizzes": 0.25,
                    "final_project": 0.25,
                }
            },
        ),
    }
    gates = []
    for key, (_, name, floor) in GATE_DEFAULTS.items():
        matching = [rule for rule in rules if _rule_key(rule) == key]
        active = [rule for rule in matching if rule.is_active]
        threshold = max([floor] + [rule.threshold or 0 for rule in active])
        if key == "final_project_score":
            threshold = max(threshold, project_threshold)
        value, complete, details = values[key]
        configured = all(rule.rule_type == "THRESHOLD" for rule in active)
        passed = bool(complete and value >= threshold and configured)
        gates.append(
            GateResult(
                key,
                passed,
                round(value, 6),
                float(threshold),
                None
                if passed
                else f"{name} gate failed: all required work must be valid and reach {threshold}%.",
                details,
                matching[0].id if matching else None,
            )
        )
    for rule in rules:
        if rule.is_active and rule.is_mandatory and _rule_key(rule) is None:
            gates.append(
                GateResult(
                    rule.code,
                    False,
                    0.0,
                    float(rule.threshold or 1),
                    "Unsupported mandatory graduation rule; an administrator must configure a supported rule.",
                    {},
                    rule.id,
                )
            )
    eligible = all(gate.passed for gate in gates)
    result = db.scalar(
        select(GraduationResult)
        .options(selectinload(GraduationResult.checks))
        .where(
            GraduationResult.student_id == user_id,
            GraduationResult.track_id == track_id,
        )
    )
    status = (
        "NOT_GRADUATED"
        if not eligible
        else "GRADUATED"
        if _verified_finalization(result)
        else "ELIGIBLE"
    )
    return GraduationCalculation(
        user_id,
        track_id,
        round(overall, 2),
        eligible,
        status,
        datetime.now(UTC),
        gates,
        result,
    )


def read_eligibility(db: Session, *, actor: User, user_id: int, track_id: int):
    require_read(db, actor, user_id, track_id)
    return calculate_graduation(db, user_id=user_id, track_id=track_id)


def finalize_graduation(
    db: Session, *, actor: User, user_id: int, track_id: int
) -> GraduationResult:
    require_manager(db, actor, track_id)
    if actor.id == user_id:
        raise PermissionError("You cannot finalize your own graduation.")
    # Serializes rule/result creation and repeat finalization for this track.
    track = db.scalar(select(Track).where(Track.id == track_id).with_for_update())
    if track is None:
        raise LookupError("Track not found.")
    calculation = calculate_graduation(db, user_id=user_id, track_id=track_id)
    result = calculation.finalized_result
    if result and result.status == "GRADUATED" and not calculation.is_eligible:
        raise ValueError(
            "Current gates fail. The historical finalized result is unchanged; inspect current eligibility."
        )
    try:
        if _verified_finalization(result):
            db.commit()
            return result
        if result is None:
            result = GraduationResult(student_id=user_id, track_id=track_id)
            db.add(result)
        result.overall_score = calculation.overall_score
        result.eligible = calculation.is_eligible
        result.status = "GRADUATED" if calculation.is_eligible else "NOT_GRADUATED"
        result.evaluated_at = calculation.evaluated_at
        result.finalized_at = (
            calculation.evaluated_at if calculation.is_eligible else None
        )
        result.finalized_by = actor.id if calculation.is_eligible else None
        result.checks.clear()
        db.flush()
        for ordering, gate in enumerate(calculation.gate_checks):
            rule_id = gate.rule_id
            if rule_id is None:
                code, name, floor = GATE_DEFAULTS[gate.gate_key]
                rule = GraduationRule(
                    track_id=track_id,
                    code=code,
                    name=name,
                    rule_type="THRESHOLD",
                    threshold=floor,
                    ordering=ordering,
                )
                db.add(rule)
                db.flush()
                rule_id = rule.id
            result.checks.append(
                GraduationCheck(
                    rule_id=rule_id,
                    gate_key=gate.gate_key,
                    passed=gate.passed,
                    score=gate.actual_value,
                    required_value=gate.required_value,
                    failure_reason=gate.failure_reason,
                    details=gate.details,
                )
            )
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


def generate_certificate_number() -> str:
    return f"KODRAQ-{datetime.now(UTC):%Y}-{uuid4().hex[:12].upper()}"


def build_certificate(
    graduation_result: GraduationResult,
    *,
    certificate_number: str | None = None,
    file_url: str | None = None,
) -> Certificate:
    if graduation_result.status != "GRADUATED" or not graduation_result.eligible:
        raise ValueError("Certificate can only be issued for a GRADUATED result.")

    if not graduation_result.student_id or not graduation_result.track_id:
        raise ValueError("Graduation result must identify a student and track.")

    return Certificate(
        student_id=graduation_result.student_id,
        track_id=graduation_result.track_id,
        graduation_result_id=graduation_result.id,
        certificate_number=certificate_number or generate_certificate_number(),
        final_score=graduation_result.overall_score,
        status="ISSUED",
        file_url=file_url,
    )


def issue_certificate(
    db: Session,
    *,
    graduation_result_id: int,
    actor: User,
    certificate_number: str | None = None,
    file_url: str | None = None,
) -> Certificate:
    result = db.scalar(
        select(GraduationResult).where(GraduationResult.id == graduation_result_id)
    )
    if result is None:
        raise ValueError("Graduation result not found.")

    require_manager(db, actor, result.track_id)
    if actor.id == result.student_id:
        raise PermissionError("You cannot issue your own graduation certificate.")
    if not _verified_finalization(result):
        raise ValueError(
            "A finalized graduation result with all gates passed is required."
        )

    existing = db.scalar(
        select(Certificate).where(
            Certificate.graduation_result_id == graduation_result_id
        )
    )
    if existing is not None:
        return existing

    certificate = build_certificate(
        result,
        certificate_number=certificate_number,
        file_url=file_url,
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


def list_student_certificates(
    db: Session,
    *,
    student_id: int,
) -> list[Certificate]:
    return list(
        db.scalars(
            select(Certificate)
            .where(Certificate.student_id == student_id)
            .order_by(Certificate.id.desc())
        ).all()
    )


def get_certificate(
    db: Session,
    *,
    certificate_id: int,
) -> Certificate | None:
    return db.scalar(select(Certificate).where(Certificate.id == certificate_id))
