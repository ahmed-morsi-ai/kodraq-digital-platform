from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    CheckConstraint,
    text,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class TrainingProject(Base, TimestampMixin):
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            name="uq_training_projects_track_id",
        ),
        CheckConstraint("length(trim(title)) > 0", name="ck_training_projects_title"),
        CheckConstraint(
            "passing_score BETWEEN 0 AND 100", name="ck_training_projects_passing_score"
        ),
    )
    __tablename__ = "training_projects"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    passing_score = Column(
        Integer, default=75, server_default=text("75"), nullable=False
    )
    is_active = Column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    track = relationship("Track", back_populates="training_projects")
    requirements = relationship(
        "ProjectRequirement",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="(ProjectRequirement.order, ProjectRequirement.id)",
    )
    submissions = relationship(
        "ProjectSubmission",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectRequirement(Base):
    __tablename__ = "project_requirements"
    __table_args__ = (
        CheckConstraint(
            "length(trim(description)) > 0", name="ck_project_requirements_description"
        ),
        CheckConstraint('"order" >= 0', name="ck_project_requirements_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("training_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=False)
    is_mandatory = Column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    order = Column(Integer, default=0, server_default=text("0"), nullable=False)

    project = relationship("TrainingProject", back_populates="requirements")


class ProjectReview(Base, TimestampMixin):
    __tablename__ = "project_reviews"
    __table_args__ = (
        CheckConstraint(
            "score IS NULL OR score BETWEEN 0 AND 100", name="ck_project_reviews_score"
        ),
        CheckConstraint(
            "status_decision IN ('UNDER_REVIEW', 'CHANGES_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_project_reviews_decision",
        ),
    )

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
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    # Retained for historical review data; new reviews use the numeric score.
    rubric_scores = Column(JSON, nullable=True)
    status_decision = Column(String(32), nullable=False)

    submission = relationship(
        "ProjectSubmission",
        back_populates="reviews",
    )
    reviewer = relationship(
        "User",
        back_populates="project_reviews",
    )
