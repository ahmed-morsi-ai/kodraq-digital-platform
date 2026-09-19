from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_assignments_difficulty",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    module_id = Column(
        Integer,
        ForeignKey("track_modules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    difficulty = Column(String(20), nullable=False)
    ordering = Column(Integer, default=0, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    due_days = Column(Integer, nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    evaluation_config = Column(JSON, nullable=True)

    track = relationship("Track", back_populates="assignments")
    module = relationship("TrackModule", back_populates="assignments")
    lesson = relationship("Lesson", back_populates="assignments")
    submissions = relationship(
        "Submission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )
