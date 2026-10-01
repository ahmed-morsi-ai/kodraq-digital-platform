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


class GraduationStatus(str, Enum):
    PENDING = "PENDING"
    ELIGIBLE = "ELIGIBLE"
    GRADUATED = "GRADUATED"
    NOT_GRADUATED = "NOT_GRADUATED"


class GraduationRule(Base, TimestampMixin):
    __tablename__ = "graduation_rules"
    __table_args__ = (
        UniqueConstraint("track_id", "code", name="uq_graduation_rules_track_code"),
        CheckConstraint(
            "threshold IS NULL OR threshold BETWEEN 0 AND 100",
            name="ck_graduation_rules_threshold",
        ),
        CheckConstraint("ordering >= 0", name="ck_graduation_rules_ordering"),
    )
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(64), nullable=False)
    threshold = Column(Integer, nullable=True)
    is_mandatory = Column(Boolean, default=True, server_default="true", nullable=False)
    ordering = Column(
        Integer, default=0, server_default="0", nullable=False, index=True
    )
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)

    track = relationship("Track", back_populates="graduation_rules")
    checks = relationship(
        "GraduationCheck",
        back_populates="rule",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GraduationResult(Base, TimestampMixin):
    __tablename__ = "graduation_results"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "track_id", name="uq_graduation_results_student_track"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'GRADUATED', 'NOT_GRADUATED')",
            name="ck_graduation_results_status",
        ),
        CheckConstraint(
            "overall_score IS NULL OR overall_score BETWEEN 0 AND 100",
            name="ck_graduation_results_score",
        ),
        CheckConstraint(
            "status != 'GRADUATED' OR eligible", name="ck_graduation_results_eligible"
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_id = Column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    overall_score = Column(Float, nullable=True)
    status = Column(
        String(32),
        default="PENDING",
        server_default="PENDING",
        nullable=False,
        index=True,
    )
    eligible = Column(Boolean, default=False, server_default="false", nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    finalized_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship(
        "User", foreign_keys=[student_id], back_populates="graduation_results"
    )
    track = relationship("Track", back_populates="graduation_results")
    finalizer = relationship("User", foreign_keys=[finalized_by])
    checks = relationship(
        "GraduationCheck",
        back_populates="result",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="GraduationCheck.id",
    )
    certificate = relationship(
        "Certificate",
        back_populates="graduation_result",
        uselist=False,
        passive_deletes="all",
    )


class GraduationCheck(Base, TimestampMixin):
    __tablename__ = "graduation_checks"
    __table_args__ = (
        UniqueConstraint(
            "result_id", "rule_id", name="uq_graduation_checks_result_rule"
        ),
        CheckConstraint(
            "score IS NULL OR score BETWEEN 0 AND 100",
            name="ck_graduation_checks_score",
        ),
        CheckConstraint(
            "required_value IS NULL OR required_value BETWEEN 0 AND 100",
            name="ck_graduation_checks_required",
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(
        Integer,
        ForeignKey("graduation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        Integer,
        ForeignKey("graduation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gate_key = Column(String(64), nullable=False)
    passed = Column(Boolean, default=False, server_default="false", nullable=False)
    score = Column(Float, nullable=True)
    required_value = Column(Float, nullable=True)
    failure_reason = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    result = relationship("GraduationResult", back_populates="checks")
    rule = relationship("GraduationRule", back_populates="checks")
