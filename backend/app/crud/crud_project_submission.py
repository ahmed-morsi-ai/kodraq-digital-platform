from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.final_project import ProjectReview, TrainingProject
from app.models.project_submission import ProjectSubmission
from app.schemas.final_project import (
    ProjectReviewCreate,
    ProjectSubmissionCreate,
    ProjectSubmissionUpdate,
)
from app.schemas.project_submission import (
    ProjectReviewCreate as LegacyProjectReviewCreate,
)


def _submission_reviews_query():
    return selectinload(ProjectSubmission.reviews).selectinload(
        ProjectReview.reviewer
    )


class CRUDProjectSubmission(
    CRUDBase[
        ProjectSubmission,
        ProjectSubmissionCreate,
        ProjectSubmissionUpdate,
    ]
):
    def _get_with_reviews(
        self,
        db: Session,
        *,
        submission_id: int,
    ) -> ProjectSubmission | None:
        stmt = (
            select(ProjectSubmission)
            .options(_submission_reviews_query())
            .where(ProjectSubmission.id == submission_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get(
        self,
        db: Session,
        id: int,
    ) -> ProjectSubmission | None:
        return self._get_with_reviews(db, submission_id=id)

    def create_for_user(
        self,
        db: Session,
        *,
        user_id: int,
        project_id: int,
        obj_in: ProjectSubmissionCreate,
    ) -> ProjectSubmission:
        if db.get(TrainingProject, project_id) is None:
            raise ValueError(
                f"Training project {project_id} was not found"
            )

        existing = db.scalar(
            select(ProjectSubmission.id).where(
                ProjectSubmission.project_id == project_id,
                ProjectSubmission.student_id == user_id,
            )
        )
        if existing is not None:
            raise ValueError(
                "A submission already exists for this student and project."
            )

        db_obj = ProjectSubmission(
            project_id=project_id,
            student_id=user_id,
            **obj_in.model_dump(),
        )
        db.add(db_obj)

        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError(
                "A submission already exists for this student and project."
            ) from error

        return self._get_with_reviews(
            db,
            submission_id=db_obj.id,
        )  # type: ignore[return-value]

    def get_multi_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ProjectSubmission]:
        stmt = (
            select(ProjectSubmission)
            .options(_submission_reviews_query())
            .where(ProjectSubmission.student_id == user_id)
            .order_by(
                ProjectSubmission.created_at.desc(),
                ProjectSubmission.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_multi_by_project(
        self,
        db: Session,
        *,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ProjectSubmission]:
        stmt = (
            select(ProjectSubmission)
            .options(_submission_reviews_query())
            .where(ProjectSubmission.project_id == project_id)
            .order_by(
                ProjectSubmission.created_at.desc(),
                ProjectSubmission.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def update(
        self,
        db: Session,
        *,
        db_obj: ProjectSubmission,
        obj_in: ProjectSubmissionUpdate,
    ) -> ProjectSubmission:
        data = obj_in.model_dump(exclude_unset=True)
        requested_status = data.pop("status", None)

        for field, value in data.items():
            setattr(db_obj, field, value)

        if requested_status == "SUBMITTED":
            db_obj.status = "SUBMITTED"
            db_obj.submitted_at = datetime.now(UTC)

        db.add(db_obj)
        db.commit()

        return self._get_with_reviews(
            db,
            submission_id=db_obj.id,
        )  # type: ignore[return-value]

    def create_review(
        self,
        db: Session,
        *,
        db_obj: ProjectSubmission,
        reviewer_id: int,
        obj_in: ProjectReviewCreate,
    ) -> ProjectReview:
        if db_obj.status not in {"SUBMITTED", "UNDER_REVIEW"}:
            raise ValueError(
                "Only submitted project submissions can be reviewed."
            )

        passing_score = db_obj.project.passing_score
        resulting_status = (
            "APPROVED"
            if obj_in.score >= passing_score
            else "CHANGES_REQUIRED"
        )

        review = ProjectReview(
            submission_id=db_obj.id,
            reviewer_id=reviewer_id,
            score=obj_in.score,
            feedback=obj_in.feedback,
            status_decision=resulting_status,
        )

        db_obj.status = resulting_status
        db.add(review)
        db.add(db_obj)
        db.commit()
        db.refresh(review)

        return review

    def get_reviews(
        self,
        db: Session,
        *,
        submission_id: int,
    ) -> Sequence[ProjectReview]:
        stmt = (
            select(ProjectReview)
            .where(ProjectReview.submission_id == submission_id)
            .order_by(
                ProjectReview.created_at.asc(),
                ProjectReview.id.asc(),
            )
        )
        return db.execute(stmt).scalars().all()

    def review(
        self,
        db: Session,
        *,
        db_obj: ProjectSubmission,
        reviewer_id: int,
        obj_in: LegacyProjectReviewCreate,
    ) -> ProjectSubmission:
        review = ProjectReview(
            submission_id=db_obj.id,
            reviewer_id=reviewer_id,
            rubric_scores=obj_in.rubric_scores,
            feedback=obj_in.feedback,
            status_decision=obj_in.status_decision,
        )
        db_obj.status = obj_in.status_decision
        db_obj.reviews.append(review)
        db.add(db_obj)
        db.commit()

        return self._get_with_reviews(
            db,
            submission_id=db_obj.id,
        )  # type: ignore[return-value]


project_submission = CRUDProjectSubmission(ProjectSubmission)


def create_project_submission(
    db: Session,
    obj_in: ProjectSubmissionCreate,
    user_id: int,
    project_id: int,
) -> ProjectSubmission:
    return project_submission.create_for_user(
        db,
        user_id=user_id,
        project_id=project_id,
        obj_in=obj_in,
    )


def get_project_submission(
    db: Session,
    submission_id: int,
) -> ProjectSubmission | None:
    return project_submission.get(db, id=submission_id)


def get_project_submissions_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[ProjectSubmission]:
    return project_submission.get_multi_by_user(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


def get_project_submissions_by_project(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[ProjectSubmission]:
    return project_submission.get_multi_by_project(
        db,
        project_id=project_id,
        skip=skip,
        limit=limit,
    )


def update_project_submission(
    db: Session,
    db_obj: ProjectSubmission,
    obj_in: ProjectSubmissionUpdate,
) -> ProjectSubmission:
    return project_submission.update(
        db,
        db_obj=db_obj,
        obj_in=obj_in,
    )


def review_project_submission(
    db: Session,
    db_obj: ProjectSubmission,
    reviewer_id: int,
    obj_in: LegacyProjectReviewCreate,
) -> ProjectSubmission:
    return project_submission.review(
        db,
        db_obj=db_obj,
        reviewer_id=reviewer_id,
        obj_in=obj_in,
    )
