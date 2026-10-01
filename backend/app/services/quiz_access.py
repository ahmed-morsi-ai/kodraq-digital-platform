from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.crud_assignment import assignment as curriculum
from app.crud.crud_quiz import quiz as quizzes
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz
from app.models.track_instructor import TrackInstructor
from app.models.user import User


def is_admin(actor: User) -> bool:
    return actor.is_superuser or bool(
        actor.role_rel and actor.role_rel.name.casefold() == "admin"
    )


def is_student(actor: User) -> bool:
    return not is_admin(actor) and (
        actor.role_rel is None or actor.role_rel.name.casefold() == "student"
    )


def require_active(actor: User) -> None:
    if not actor.is_active:
        raise PermissionError("Inactive users cannot access quizzes.")


def track_id(db: Session, record) -> int | None:
    try:
        return curriculum.resolve_track_id(
            db,
            track_id=record.track_id,
            module_id=record.module_id,
            lesson_id=record.lesson_id,
        )
    except (LookupError, ValueError) as error:
        raise PermissionError("Quiz curriculum references are inconsistent.") from error


def require_track(db: Session, actor: User, owning_track: int | None) -> None:
    require_active(actor)
    if is_admin(actor):
        return
    if owning_track is None:
        raise PermissionError("Quiz has no authorized track context.")
    if is_student(actor):
        allowed = db.scalar(
            select(Enrollment.id).where(
                Enrollment.user_id == actor.id,
                Enrollment.track_id == owning_track,
                Enrollment.status == "active",
            )
        )
    elif actor.role_rel and actor.role_rel.name.casefold() == "instructor":
        allowed = db.scalar(
            select(TrackInstructor.track_id).where(
                TrackInstructor.instructor_id == actor.id,
                TrackInstructor.track_id == owning_track,
            )
        )
    else:
        allowed = None
    if allowed is None:
        raise PermissionError(
            "An active enrollment or instructor assignment to this track is required."
        )


def require_quiz(db: Session, actor: User, quiz: Quiz) -> None:
    require_active(actor)
    if is_admin(actor):
        return
    owner = track_id(db, quiz)
    require_track(db, actor, owner)
    for link in quiz.question_links:
        if track_id(db, link.question) != owner:
            raise PermissionError("Quiz contains questions from an unauthorized track.")


def require_attempt_read(db: Session, actor: User, attempt) -> None:
    require_active(actor)
    if is_student(actor):
        if attempt.user_id != actor.id:
            raise PermissionError("Only the attempt owner can access this attempt.")
    else:
        # Includes inherited module/lesson ownership and malformed legacy links.
        quizzes.get_for_manager(db, id=attempt.quiz_id, actor=actor)
