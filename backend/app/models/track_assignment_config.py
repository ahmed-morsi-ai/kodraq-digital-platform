from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class TrackAssignmentConfig(Base, TimestampMixin):
    __tablename__ = "track_assignment_configs"
    __table_args__ = (
        CheckConstraint(
            "passing_score_threshold BETWEEN 0 AND 100",
            name="ck_track_assignment_config_passing_score",
        ),
        CheckConstraint(
            "max_retries >= 0",
            name="ck_track_assignment_config_max_retries",
        ),
        CheckConstraint(
            "late_submission_policy IN ('ACCEPTED', 'REJECTED', 'PENALIZED')",
            name="ck_track_assignment_config_late_policy",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    passing_score_threshold = Column(Integer, default=50, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    is_strict_progression = Column(Boolean, default=False, nullable=False)
    late_submission_policy = Column(
        String(20),
        default="ACCEPTED",
        nullable=False,
    )

    track = relationship("Track", back_populates="assignment_config", uselist=False)
