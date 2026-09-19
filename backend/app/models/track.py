from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Track(Base, TimestampMixin):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    ordering = Column(Integer, default=0, nullable=False)

    modules = relationship(
        "TrackModule",
        back_populates="track",
        cascade="all, delete-orphan",
    )
    enrollments = relationship(
        "Enrollment",
        back_populates="track",
        cascade="all, delete-orphan",
    )
    assignments = relationship("Assignment", back_populates="track")
    questions = relationship("Question", back_populates="track")
    quizzes = relationship("Quiz", back_populates="track")
    training_projects = relationship(
        "TrainingProject",
        back_populates="track",
        cascade="all, delete-orphan",
    )
    graduation_evaluations = relationship(
        "GraduationEvaluation",
        back_populates="track",
        cascade="all, delete-orphan",
    )
    knowledge_documents = relationship(
        "KnowledgeDocument",
        back_populates="track",
        cascade="all, delete-orphan",
    )
    knowledge_chunks = relationship(
        "KnowledgeChunk",
        back_populates="track",
        cascade="all, delete-orphan",
        overlaps="document,chunks",
    )


class TrackModule(Base, TimestampMixin):
    __tablename__ = "track_modules"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ordering = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track", back_populates="modules")
    lessons = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
    )
    resources = relationship(
        "Resource",
        back_populates="module",
        cascade="all, delete-orphan",
    )
    assignments = relationship("Assignment", back_populates="module")


class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(
        Integer,
        ForeignKey("track_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    video_url = Column(String(512), nullable=True)
    ordering = Column(Integer, default=0, nullable=False)

    module = relationship("TrackModule", back_populates="lessons")
    student_progress = relationship(
        "StudentProgress",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    assignments = relationship("Assignment", back_populates="lesson")
    questions = relationship("Question", back_populates="lesson")
    quizzes = relationship("Quiz", back_populates="lesson")


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(
        Integer,
        ForeignKey("track_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    file_url = Column(String(512), nullable=False)
    resource_type = Column(
        String(50),
        default="document",
        nullable=False,
    )

    module = relationship("TrackModule", back_populates="resources")
