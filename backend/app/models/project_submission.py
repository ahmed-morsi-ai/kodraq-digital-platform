from enum import Enum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ProjectSubmissionStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProjectSubmission(Base, TimestampMixin):
    __tablename__ = "project_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', "
            "'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_project_submissions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("training_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_url = Column(String(512), nullable=True)
    live_url = Column(String(512), nullable=True)
    documentation_url = Column(String(512), nullable=True)
    status = Column(
        String(32),
        default=ProjectSubmissionStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    project = relationship("TrainingProject", back_populates="submissions")
    user = relationship("User", back_populates="project_submissions")
    reviews = relationship(
        "ProjectReview",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="ProjectReview.created_at",
    )


class ProjectReview(Base, TimestampMixin):
    __tablename__ = "project_reviews"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(
        Integer,
        ForeignKey("project_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rubric_scores = Column(JSON, nullable=True)
    feedback = Column(Text, nullable=True)
    status_decision = Column(String(32), nullable=False)

    submission = relationship("ProjectSubmission", back_populates="reviews")
    reviewer = relationship("User", back_populates="project_reviews")
