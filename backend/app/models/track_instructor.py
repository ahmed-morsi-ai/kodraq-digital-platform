from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class TrackInstructor(Base):
    __tablename__ = "track_instructors"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "instructor_id",
            name="uq_track_instructors_track_instructor",
        ),
    )

    track_id = Column(
        Integer,
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    instructor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    track = relationship("Track", back_populates="track_instructor_links")
    instructor = relationship(
        "User",
        back_populates="instructor_track_links",
    )
