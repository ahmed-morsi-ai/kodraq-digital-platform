from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class QuizAttemptStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED')",
            name="ck_quiz_attempts_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(
        Integer,
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Float, nullable=True)
    passed = Column(Boolean, default=False, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False, index=True)
    flag_reason = Column(String(255), nullable=True)
    status = Column(
        String(32),
        default=QuizAttemptStatus.IN_PROGRESS.value,
        nullable=False,
        index=True,
    )
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", back_populates="quiz_attempts")
    answers = relationship(
        "QuizAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="QuizAnswer.id",
    )


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_quiz_answers_attempt_question",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(
        Integer,
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_option_id = Column(
        Integer,
        ForeignKey("question_options.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_correct = Column(Boolean, default=False, nullable=False)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="quiz_answers")
    selected_option = relationship(
        "QuestionOption",
        back_populates="selected_answers",
    )
