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


class GraduationRule(Base, TimestampMixin):
    __tablename__ = "graduation_rules"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "code",
            name="uq_graduation_rules_track_code",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(64), nullable=False)
    threshold = Column(Integer, nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    ordering = Column(Integer, default=0, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    track = relationship("Track")
    checks = relationship(
        "GraduationCheck",
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class GraduationResult(Base, TimestampMixin):
    __tablename__ = "graduation_results"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "track_id",
            name="uq_graduation_results_student_track",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
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
    overall_score = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    eligible = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(String(64), nullable=True)

    student = relationship("User")
    track = relationship("Track")
    checks = relationship(
        "GraduationCheck",
        back_populates="result",
        cascade="all, delete-orphan",
        order_by="GraduationCheck.id",
    )
    certificate = relationship(
        "Certificate",
        back_populates="graduation_result",
        uselist=False,
    )


class GraduationCheck(Base, TimestampMixin):
    __tablename__ = "graduation_checks"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "rule_id",
            name="uq_graduation_checks_result_rule",
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
    passed = Column(Boolean, nullable=False, default=False)
    score = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)

    result = relationship("GraduationResult", back_populates="checks")
    rule = relationship("GraduationRule", back_populates="checks")


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"
    __table_args__ = (
        UniqueConstraint(
            "graduation_result_id",
            name="uq_certificates_graduation_result",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
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
    graduation_result_id = Column(
        Integer,
        ForeignKey("graduation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    certificate_number = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    final_score = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="ISSUED")
    file_url = Column(Text, nullable=True)

    student = relationship("User")
    track = relationship("Track")
    graduation_result = relationship(
        "GraduationResult",
        back_populates="certificate",
    )
