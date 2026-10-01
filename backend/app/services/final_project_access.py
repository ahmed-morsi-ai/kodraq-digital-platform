from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.track_instructor import TrackInstructor
from app.models.user import User


class ProjectConflictError(ValueError):
    """A unique final project or student submission already exists."""


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
        raise PermissionError("Inactive users cannot access final projects.")


def require_student(actor: User) -> None:
    require_active(actor)
    if not is_student(actor):
        raise PermissionError("Only students can submit final projects.")


def require_manager(db: Session, actor: User, track_id: int) -> None:
    require_active(actor)
    if is_admin(actor):
        return
    if not actor.role_rel or actor.role_rel.name.casefold() != "instructor":
        raise PermissionError(
            "Only admins and assigned instructors can manage final projects."
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


def require_enrollment(db: Session, actor: User, track_id: int) -> None:
    require_student(actor)
    if (
        db.scalar(
            select(Enrollment.id).where(
                Enrollment.user_id == actor.id,
                Enrollment.track_id == track_id,
                Enrollment.status == "active",
            )
        )
        is None
    ):
        raise PermissionError("You must be actively enrolled in this track.")


def require_track_read(db: Session, actor: User, track_id: int) -> None:
    if is_student(actor):
        require_enrollment(db, actor, track_id)
    else:
        require_manager(db, actor, track_id)


def require_project_read(db: Session, actor: User, project) -> None:
    require_track_read(db, actor, project.track_id)
    if is_student(actor) and not project.is_active:
        raise LookupError("Final project not found")


def require_submission_read(db: Session, actor: User, submission) -> None:
    require_active(actor)
    if is_student(actor):
        if submission.student_id != actor.id:
            raise PermissionError("You can only view your own submission and reviews.")
    else:
        require_manager(db, actor, submission.project.track_id)


def commit(db: Session, record):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return record
