from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_VERIFICATION', 'VERIFIED', 'REJECTED')",
            name="ck_payments_status",
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
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="EGP", nullable=False)
    status = Column(String(32), default="PENDING_VERIFICATION", nullable=False)
    payment_method = Column(String(32), nullable=False)
    receipt_url = Column(String(1024), nullable=False)
    rejection_reason = Column(String(512), nullable=True)

    user = relationship("User", back_populates="payments")
    track = relationship("Track", back_populates="payments")
