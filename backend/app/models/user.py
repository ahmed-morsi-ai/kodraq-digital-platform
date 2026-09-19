from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.graduation import GraduationEvaluation
    from app.models.project_submission import ProjectReview, ProjectSubmission
    from app.models.quiz_attempt import QuizAttempt
    from app.models.role import Role
    from app.models.submission import Submission


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id"), nullable=True
    )
    role_rel: Mapped[Role | None] = relationship(
        "Role", back_populates="users"
    )

    enrollments: Mapped[list[Enrollment]] = relationship(
        "Enrollment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list[Submission]] = relationship(
        "Submission",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    quiz_attempts: Mapped[list[QuizAttempt]] = relationship(
        "QuizAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    project_submissions: Mapped[list[ProjectSubmission]] = relationship(
        "ProjectSubmission",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    project_reviews: Mapped[list[ProjectReview]] = relationship(
        "ProjectReview",
        back_populates="reviewer",
        cascade="all, delete-orphan",
    )
    graduation_evaluations: Mapped[list[GraduationEvaluation]] = relationship(
        "GraduationEvaluation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
