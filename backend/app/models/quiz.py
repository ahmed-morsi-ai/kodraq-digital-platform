from sqlalchemy import (
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


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    question_type = Column(String(32), nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)
    points = Column(Integer, default=1, nullable=False)
    explanation = Column(Text, nullable=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    track = relationship("Track", back_populates="questions")
    lesson = relationship("Lesson", back_populates="questions")
    options = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    quiz_questions = relationship(
        "QuizQuestion",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    quiz_answers = relationship("QuizAnswer", back_populates="question")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship("Question", back_populates="options")
    selected_answers = relationship(
        "QuizAnswer",
        back_populates="selected_option",
    )


class Quiz(Base, TimestampMixin):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    passing_score = Column(Integer, nullable=False)
    time_limit_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track", back_populates="quizzes")
    lesson = relationship("Lesson", back_populates="quizzes")
    question_links = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.ordering",
    )
    attempts = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan",
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint(
            "quiz_id",
            "question_id",
            name="uq_quiz_questions_quiz_question",
        ),
    )

    quiz_id = Column(
        Integer,
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    ordering = Column(Integer, default=0, nullable=False, index=True)

    quiz = relationship("Quiz", back_populates="question_links")
    question = relationship("Question", back_populates="quiz_questions")
