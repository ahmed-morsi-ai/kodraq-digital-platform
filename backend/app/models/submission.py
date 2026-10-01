from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from app.models.base import Base, TimestampMixin


class SubmissionStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', "
            "'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_submissions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(
        Integer,
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SQLAlchemyEnum(
            SubmissionStatus,
            native_enum=False,
            validate_strings=True,
            length=32,
        ),
        default=SubmissionStatus.DRAFT,
        server_default=SubmissionStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    grade = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    content = Column(Text, nullable=True)
    github_url = Column(String(512), nullable=True)
    file_path_or_url = Column(String(1024), nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    files = relationship(
        "SubmissionFile",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    reviews = relationship(
        "SubmissionReview",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="(SubmissionReview.created_at, SubmissionReview.id)",
    )
    attempts = relationship(
        "SubmissionAttempt",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="(SubmissionAttempt.submitted_at, SubmissionAttempt.id)",
    )

    @validates("status")
    def validate_status(
        self, key: str, value: str | SubmissionStatus
    ) -> SubmissionStatus:
        return SubmissionStatus(value)


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(String(512), nullable=False)
    file_url = Column(String(1024), nullable=False)
    file_type = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    submission = relationship("Submission", back_populates="files")


class SubmissionAttempt(Base):
    """Append-only timestamps preserve every submit/resubmit in the history."""

    __tablename__ = "submission_attempts"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    submission = relationship("Submission", back_populates="attempts")


class SubmissionReview(Base):
    __tablename__ = "submission_reviews"
    __table_args__ = (
        CheckConstraint(
            "status_transition IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', "
            "'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_submission_reviews_status_transition",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feedback_text = Column(Text, nullable=False)
    score = Column(Integer, nullable=True)
    status_transition = Column(
        SQLAlchemyEnum(
            SubmissionStatus,
            native_enum=False,
            validate_strings=True,
            length=32,
        ),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    submission = relationship("Submission", back_populates="reviews")
    reviewer = relationship(
        "User",
        back_populates="submission_reviews",
    )

    @validates("status_transition")
    def validate_status_transition(
        self, key: str, value: str | SubmissionStatus
    ) -> SubmissionStatus:
        return SubmissionStatus(value)
