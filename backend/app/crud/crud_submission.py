from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.crud.crud_assignment import assignment as crud_assignment
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.submission import (
    Submission,
    SubmissionAttempt,
    SubmissionReview,
    SubmissionStatus,
)
from app.models.track_instructor import TrackInstructor
from app.models.user import User
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionReviewCreate,
    SubmissionUpdate,
)

EDITABLE_STATES = {SubmissionStatus.DRAFT, SubmissionStatus.CHANGES_REQUIRED}
REVIEW_TRANSITIONS = {
    SubmissionStatus.SUBMITTED: {
        SubmissionStatus.UNDER_REVIEW,
        SubmissionStatus.CHANGES_REQUIRED,
        SubmissionStatus.APPROVED,
        SubmissionStatus.REJECTED,
    },
    SubmissionStatus.UNDER_REVIEW: {
        SubmissionStatus.CHANGES_REQUIRED,
        SubmissionStatus.APPROVED,
        SubmissionStatus.REJECTED,
    },
}


class SubmissionStateError(ValueError):
    """The requested action conflicts with the current submission state."""


class CRUDSubmission(CRUDBase[Submission, SubmissionCreate, SubmissionUpdate]):
    @staticmethod
    def _is_admin(actor: User) -> bool:
        return actor.is_superuser or (
            actor.role_rel is not None and actor.role_rel.name.casefold() == "admin"
        )

    @staticmethod
    def _is_student(actor: User) -> bool:
        return actor.role_rel is None or actor.role_rel.name.casefold() == "student"

    @staticmethod
    def _require_active(actor: User) -> None:
        if not actor.is_active:
            raise PermissionError("Inactive users cannot access submissions.")

    @staticmethod
    def _track_id(db: Session, assignment: Assignment) -> int | None:
        try:
            return crud_assignment.resolve_track_id(
                db,
                track_id=assignment.track_id,
                module_id=assignment.module_id,
                lesson_id=assignment.lesson_id,
            )
        except (LookupError, ValueError) as error:
            raise PermissionError(
                "The assignment has no authorized track context."
            ) from error

    def _require_student_assignment(
        self, db: Session, *, actor: User, assignment: Assignment
    ) -> None:
        if not self._is_student(actor):
            raise PermissionError("Only students can submit assignment work.")
        track_id = self._track_id(db, assignment)
        enrollment = (
            db.scalar(
                select(Enrollment.id).where(
                    Enrollment.user_id == actor.id,
                    Enrollment.track_id == track_id,
                    Enrollment.status == "active",
                )
            )
            if track_id is not None
            else None
        )
        if not assignment.is_active or enrollment is None:
            raise PermissionError(
                "An active enrollment and active assignment are required."
            )

    def require_manager(
        self, db: Session, *, actor: User, assignment: Assignment
    ) -> None:
        self._require_active(actor)
        if self._is_admin(actor):
            return
        if actor.role_rel is None or actor.role_rel.name.casefold() != "instructor":
            raise PermissionError(
                "Only admins and assigned instructors can grade submissions."
            )
        track_id = self._track_id(db, assignment)
        link = (
            db.scalar(
                select(TrackInstructor.track_id).where(
                    TrackInstructor.track_id == track_id,
                    TrackInstructor.instructor_id == actor.id,
                )
            )
            if track_id is not None
            else None
        )
        if link is None:
            raise PermissionError(
                "Instructor is not assigned to this submission's track."
            )

    @staticmethod
    def _get_assignment(db: Session, assignment_id: int) -> Assignment:
        assignment = db.get(Assignment, assignment_id)
        if assignment is None:
            raise LookupError("Assignment not found")
        return assignment

    @staticmethod
    def _load(db: Session, submission_id: int, *, lock: bool = False) -> Submission:
        stmt = select(Submission).where(Submission.id == submission_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        else:
            stmt = stmt.options(
                selectinload(Submission.files),
                selectinload(Submission.reviews),
                selectinload(Submission.attempts),
            )
        submission = db.scalar(stmt)
        if submission is None:
            raise LookupError("Submission not found")
        return submission

    @staticmethod
    def _commit(db: Session, submission: Submission) -> Submission:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(submission)
        return submission

    @staticmethod
    def _pagination(skip: int, limit: int) -> None:
        if skip < 0 or limit < 0:
            raise ValueError("Pagination values must be non-negative.")

    def create(
        self, db: Session, *, obj_in: SubmissionCreate, actor: User
    ) -> Submission:
        obj_in = SubmissionCreate.model_validate(obj_in.model_dump())
        self._require_active(actor)
        assignment = self._get_assignment(db, obj_in.assignment_id)
        if not self._is_admin(actor):
            self._require_student_assignment(db, actor=actor, assignment=assignment)
        submission = Submission(user_id=actor.id, **obj_in.model_dump())
        db.add(submission)
        return self._commit(db, submission)

    def get_for_user(
        self, db: Session, *, submission_id: int, actor: User
    ) -> Submission:
        self._require_active(actor)
        submission = self._load(db, submission_id)
        if self._is_student(actor) and submission.user_id == actor.id:
            return submission
        self.require_manager(db, actor=actor, assignment=submission.assignment)
        return submission

    def get_editable(
        self, db: Session, *, submission_id: int, actor: User
    ) -> Submission:
        self._require_active(actor)
        submission = self._load(db, submission_id, lock=True)
        if self._is_admin(actor):
            return submission
        if submission.user_id != actor.id or not self._is_student(actor):
            raise PermissionError(
                "Only the submission owner or an admin can update it."
            )
        self._require_student_assignment(
            db, actor=actor, assignment=submission.assignment
        )
        if submission.status not in EDITABLE_STATES:
            raise SubmissionStateError(
                "Only draft or changes-required submissions can be updated."
            )
        return submission

    def update(
        self,
        db: Session,
        *,
        db_obj: Submission,
        obj_in: SubmissionUpdate | dict,
        actor: User,
    ) -> Submission:
        payload = (
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        )
        changes = SubmissionUpdate.model_validate(payload).model_dump(
            exclude_unset=True
        )
        submission = self.get_editable(db, submission_id=db_obj.id, actor=actor)
        if "status" in changes:
            if submission.status not in EDITABLE_STATES:
                raise SubmissionStateError(
                    "Only draft or changes-required submissions can be submitted."
                )
            submission.submitted_at = datetime.now(UTC)
            submission.grade = None
            db.add(
                SubmissionAttempt(
                    submission_id=submission.id, submitted_at=submission.submitted_at
                )
            )
        for field, value in changes.items():
            setattr(submission, field, value)
        return self._commit(db, submission)

    def get_multi_by_user(
        self,
        db: Session,
        *,
        actor: User,
        skip: int = 0,
        limit: int = 100,
        assignment_id: int | None = None,
    ) -> Sequence[Submission]:
        self._require_active(actor)
        if not self._is_admin(actor) and not self._is_student(actor):
            raise PermissionError(
                "Only students and admins can list their own submissions."
            )
        self._pagination(skip, limit)
        stmt = select(Submission).where(Submission.user_id == actor.id)
        if assignment_id is not None:
            stmt = stmt.where(Submission.assignment_id == assignment_id)
        return db.scalars(
            stmt.order_by(Submission.created_at.desc(), Submission.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()

    def get_multi_by_assignment(
        self,
        db: Session,
        *,
        assignment_id: int,
        actor: User,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Submission]:
        assignment = self._get_assignment(db, assignment_id)
        self.require_manager(db, actor=actor, assignment=assignment)
        self._pagination(skip, limit)
        return db.scalars(
            select(Submission)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.created_at.desc(), Submission.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()

    def create_review_and_transition(
        self,
        db: Session,
        *,
        db_obj: Submission,
        actor: User,
        obj_in: SubmissionReviewCreate,
    ) -> Submission:
        obj_in = SubmissionReviewCreate.model_validate(obj_in.model_dump())
        submission = self._load(db, db_obj.id, lock=True)
        self.require_manager(db, actor=actor, assignment=submission.assignment)
        if obj_in.status_transition not in REVIEW_TRANSITIONS.get(
            submission.status, set()
        ):
            raise SubmissionStateError(
                f"Cannot review {submission.status.value} as {obj_in.status_transition.value}."
            )
        review = SubmissionReview(
            submission_id=submission.id,
            reviewer_id=actor.id,
            feedback_text=obj_in.feedback_text,
            status_transition=obj_in.status_transition,
            score=obj_in.grade,
            created_at=datetime.now(UTC),
        )
        submission.status = obj_in.status_transition
        submission.grade = obj_in.grade
        db.add(review)
        return self._commit(db, submission)


submission = CRUDSubmission(Submission)
