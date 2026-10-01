from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.crud.crud_final_project import get_project
from app.models.final_project import ProjectReview
from app.models.project_submission import ProjectSubmission
from app.models.user import User
from app.schemas.final_project import (
    ProjectReviewCreate,
    ProjectSubmissionCreate,
    ProjectSubmissionUpdate,
)
from app.services.final_project_access import (
    ProjectConflictError,
    commit,
    require_enrollment,
    require_manager,
    require_student,
    require_submission_read,
)


def _query():
    return select(ProjectSubmission).options(
        selectinload(ProjectSubmission.reviews), selectinload(ProjectSubmission.project)
    )


def _pagination(skip, limit):
    if skip < 0 or limit < 1 or limit > 100:
        raise ValueError("Pagination requires skip >= 0 and limit between 1 and 100.")


class CRUDProjectSubmission(
    CRUDBase[ProjectSubmission, ProjectSubmissionCreate, ProjectSubmissionUpdate]
):
    def get(self, db: Session, id: int, *, actor: User) -> ProjectSubmission:
        record = db.scalar(_query().where(ProjectSubmission.id == id))
        if record is None:
            raise LookupError("Project submission not found")
        require_submission_read(db, actor, record)
        return record

    def _locked(
        self, db: Session, submission_id: int, actor: User
    ) -> ProjectSubmission:
        record = self.get(db, submission_id, actor=actor)
        # Shared lock order for edits, resubmissions, reviews and project removal.
        get_project(db, record.project_id, lock=True)
        record = db.scalar(
            _query()
            .where(ProjectSubmission.id == submission_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise LookupError("Project submission not found")
        require_submission_read(db, actor, record)
        return record

    def create(
        self,
        db: Session,
        *,
        project_id: int,
        obj_in: ProjectSubmissionCreate,
        actor: User,
    ) -> ProjectSubmission:
        require_student(actor)
        project = get_project(db, project_id, lock=True)
        require_enrollment(db, actor, project.track_id)
        if not project.is_active:
            raise LookupError("Training project not found")
        if (
            db.scalar(
                select(ProjectSubmission.id).where(
                    ProjectSubmission.project_id == project_id,
                    ProjectSubmission.student_id == actor.id,
                )
            )
            is not None
        ):
            raise ProjectConflictError(
                "A submission already exists for this student and project."
            )
        data = ProjectSubmissionCreate.model_validate(obj_in.model_dump()).model_dump()
        record = ProjectSubmission(project_id=project_id, student_id=actor.id, **data)
        db.add(record)
        return commit(db, record)

    def get_mine(self, db: Session, *, actor: User, project_id=None, skip=0, limit=100):
        require_student(actor)
        _pagination(skip, limit)
        stmt = _query().where(ProjectSubmission.student_id == actor.id)
        if project_id is not None:
            stmt = stmt.where(ProjectSubmission.project_id == project_id)
        return db.scalars(
            stmt.order_by(
                ProjectSubmission.created_at.desc(), ProjectSubmission.id.desc()
            )
            .offset(skip)
            .limit(limit)
        ).all()

    def get_multi_by_project(
        self, db: Session, *, project_id: int, actor: User, skip=0, limit=100
    ):
        project = get_project(db, project_id)
        require_manager(db, actor, project.track_id)
        _pagination(skip, limit)
        return db.scalars(
            _query()
            .where(ProjectSubmission.project_id == project_id)
            .order_by(ProjectSubmission.created_at.desc(), ProjectSubmission.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()

    def get_multi(self, *args, **kwargs):
        raise PermissionError("Use an authorized final-project submission listing.")

    def remove(self, *args, **kwargs):
        raise PermissionError(
            "Individual final-project submissions cannot be deleted through CRUD."
        )

    def update(
        self,
        db: Session,
        *,
        submission_id: int,
        obj_in: ProjectSubmissionUpdate,
        actor: User,
    ) -> ProjectSubmission:
        require_student(actor)
        record = self._locked(db, submission_id, actor)
        require_enrollment(db, actor, record.project.track_id)
        if not record.project.is_active:
            raise LookupError("Training project not found")
        if record.status not in {"DRAFT", "CHANGES_REQUIRED"}:
            raise PermissionError(
                "Only draft or changes-required submissions can be updated."
            )
        data = ProjectSubmissionUpdate.model_validate(
            obj_in.model_dump(exclude_unset=True)
        ).model_dump(exclude_unset=True)
        requested = data.pop("status", None)
        if requested == "SUBMITTED":
            evidence = {
                key: data.get(key, getattr(record, key))
                for key in ("github_url", "live_url", "file_url")
            }
            # Revalidate legacy stored URLs too before work enters the review queue.
            ProjectSubmissionCreate.model_validate(evidence)
            if not any(evidence.values()):
                raise ValueError(
                    "Include a GitHub repository, live URL, or file URL before submitting."
                )
        for field, value in data.items():
            setattr(record, field, value)
        if requested == "SUBMITTED":
            record.status = requested
            record.submitted_at = datetime.now(UTC)
        return commit(db, record)

    def create_review(
        self,
        db: Session,
        *,
        submission_id: int,
        obj_in: ProjectReviewCreate,
        actor: User,
    ) -> ProjectReview:
        record = self._locked(db, submission_id, actor)
        require_manager(db, actor, record.project.track_id)
        if record.student_id == actor.id:
            raise PermissionError(
                "Reviewers cannot grade their own final-project submission."
            )
        if record.status not in {"SUBMITTED", "UNDER_REVIEW"}:
            raise ValueError("Only submitted project submissions can be reviewed.")
        data = ProjectReviewCreate.model_validate(obj_in.model_dump())
        decision = data.status_decision
        if decision is None:
            decision = (
                "APPROVED"
                if data.score >= record.project.passing_score
                else "CHANGES_REQUIRED"
            )
        if decision == "UNDER_REVIEW" and record.status != "SUBMITTED":
            raise ValueError("This submission is already under review.")
        if decision == "APPROVED" and data.score < record.project.passing_score:
            raise ValueError(
                "Approval requires a score at or above the project passing score."
            )
        review = ProjectReview(
            submission_id=record.id,
            reviewer_id=actor.id,
            score=data.score,
            feedback=data.feedback,
            status_decision=decision,
        )
        record.status = decision
        db.add(review)
        return commit(db, review)

    def get_reviews(self, db: Session, *, submission_id: int, actor: User):
        record = self.get(db, submission_id, actor=actor)
        return record.reviews


project_submission = CRUDProjectSubmission(ProjectSubmission)
