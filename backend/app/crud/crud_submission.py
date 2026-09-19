from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.submission import Submission
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionReview,
    SubmissionUpdate,
)


class CRUDSubmission(
    CRUDBase[Submission, SubmissionCreate, SubmissionUpdate]
):
    def create_for_user(
        self,
        db: Session,
        *,
        user_id: int,
        obj_in: SubmissionCreate,
    ) -> Submission:
        db_obj = Submission(
            user_id=user_id,
            **obj_in.model_dump(),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc(), Submission.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_multi_by_assignment(
        self,
        db: Session,
        *,
        assignment_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.created_at.desc(), Submission.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def review(
        self,
        db: Session,
        *,
        db_obj: Submission,
        obj_in: SubmissionReview,
    ) -> Submission:
        return self.update(
            db,
            db_obj=db_obj,
            obj_in={"status": obj_in.status},
        )


submission = CRUDSubmission(Submission)


def create_submission(
    db: Session,
    obj_in: SubmissionCreate,
    user_id: int,
) -> Submission:
    return submission.create_for_user(
        db,
        user_id=user_id,
        obj_in=obj_in,
    )


def get_submission(db: Session, submission_id: int) -> Submission | None:
    return submission.get(db, id=submission_id)


def get_submissions_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Submission]:
    return submission.get_multi_by_user(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


def get_submissions_by_assignment(
    db: Session,
    assignment_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Submission]:
    return submission.get_multi_by_assignment(
        db,
        assignment_id=assignment_id,
        skip=skip,
        limit=limit,
    )


def update_submission(
    db: Session,
    db_obj: Submission,
    obj_in: SubmissionUpdate,
) -> Submission:
    return submission.update(db, db_obj=db_obj, obj_in=obj_in)


def review_submission(
    db: Session,
    db_obj: Submission,
    status: str | SubmissionReview,
) -> Submission:
    review = (
        status
        if isinstance(status, SubmissionReview)
        else SubmissionReview(status=status)
    )
    return submission.review(db, db_obj=db_obj, obj_in=review)
