from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class GraduationEvaluationStatus(str, Enum):
    PENDING = "PENDING"
    GRADUATED = "GRADUATED"
    FAILED_GATES = "FAILED_GATES"


class GraduationEvaluation(Base, TimestampMixin):
    __tablename__ = "graduation_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'GRADUATED', 'FAILED_GATES')",
            name="ck_graduation_evaluations_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score = Column(Float, nullable=True)
    is_eligible = Column(Boolean, default=False, nullable=False)
    status = Column(
        String(32),
        default=GraduationEvaluationStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    evaluated_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="graduation_evaluations")
    track = relationship("Track", back_populates="graduation_evaluations")
    gate_checks = relationship(
        "GraduationGateCheck",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="GraduationGateCheck.id",
    )


class GraduationGateCheck(Base):
    __tablename__ = "graduation_gate_checks"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            "gate_key",
            name="uq_graduation_gate_checks_evaluation_gate",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(
        Integer,
        ForeignKey("graduation_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gate_key = Column(String(64), nullable=False, index=True)
    passed = Column(Boolean, nullable=False)
    actual_value = Column(Float, nullable=True)
    required_value = Column(Float, nullable=True)
    failure_reason = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    evaluation = relationship("GraduationEvaluation", back_populates="gate_checks")
