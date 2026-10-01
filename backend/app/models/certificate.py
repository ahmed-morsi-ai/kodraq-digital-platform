from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


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
    final_score = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="ISSUED")
    file_url = Column(Text, nullable=True)

    student = relationship("User")
    track = relationship("Track")
    graduation_result = relationship(
        "GraduationResult",
        back_populates="certificate",
    )
