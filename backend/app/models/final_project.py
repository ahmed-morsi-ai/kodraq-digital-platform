from sqlalchemy import (
    JSON,
    Boolean,
    Column,
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
    passing_score = Column(Integer, default=75, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track", back_populates="training_projects")
    requirements = relationship(
        "ProjectRequirement",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProjectRequirement.order",
    )
    submissions = relationship(
        "ProjectSubmission",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectRequirement(Base):
    __tablename__ = "project_requirements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("training_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    project = relationship("TrainingProject", back_populates="requirements")

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
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    # Preserve the pre-existing review contract.
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
