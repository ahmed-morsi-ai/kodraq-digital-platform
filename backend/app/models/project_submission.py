from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
        UniqueConstraint(
            "project_id",
            "student_id",
            name="uq_project_submissions_project_student",
        ),
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
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    github_url = Column(String(512), nullable=True)
    live_url = Column(String(512), nullable=True)
    file_url = Column(String(512), nullable=True)
    student_notes = Column(Text, nullable=True)
    status = Column(
        String(32),
        default=ProjectSubmissionStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship(
        "TrainingProject",
        back_populates="submissions",
    )
    student = relationship(
        "User",
        back_populates="project_submissions",
    )
    reviews = relationship(
        "ProjectReview",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="ProjectReview.created_at",
    )
