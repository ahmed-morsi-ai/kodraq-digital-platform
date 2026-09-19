from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class TrainingProject(Base, TimestampMixin):
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
    evaluation_rubric = Column(JSON, default=dict, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track", back_populates="training_projects")
    requirements = relationship(
        "ProjectRequirement",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectRequirement.ordering",
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
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    ordering = Column(Integer, default=0, nullable=False)

    project = relationship("TrainingProject", back_populates="requirements")
