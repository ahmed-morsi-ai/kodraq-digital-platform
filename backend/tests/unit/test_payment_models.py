from decimal import Decimal

import pytest
from fastapi import HTTPException, status

from app.api.v1.enrollments import update_enrollment
from app.crud.crud_enrollment import enrollment as crud_enrollment
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.track import Track
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


def _create_user(db_session) -> User:
    user = User(
        email="payment-test@example.com",
        hashed_password="test-password",
        full_name="Payment Test User",
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_track(db_session, *, is_premium: bool, suffix: str) -> Track:
    track = Track(
        name=f"Payment Track {suffix}",
        slug=f"payment-track-{suffix}",
        description="Payment test track",
        is_premium=is_premium,
    )
    db_session.add(track)
    db_session.flush()
    return track


def test_payment_creation(db_session):
    user = _create_user(db_session)
    track = _create_track(db_session, is_premium=True, suffix="creation")

    payment = Payment(
        user_id=user.id,
        track_id=track.id,
        amount=Decimal("150.00"),
        payment_method="VODAFONE_CASH",
        receipt_url="https://example.com/receipt.jpg",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    assert payment.id is not None
    assert payment.amount == Decimal("150.00")
    assert payment.currency == "EGP"
    assert payment.status == "PENDING_VERIFICATION"
    assert payment.user_id == user.id
    assert payment.track_id == track.id
    assert payment.receipt_url == "https://example.com/receipt.jpg"


def test_premium_enrollment_starts_pending_payment(db_session):
    user = _create_user(db_session)
    track = _create_track(db_session, is_premium=True, suffix="premium")

    created = crud_enrollment.create_for_user(
        db_session,
        user_id=user.id,
        obj_in=EnrollmentCreate(
            track_id=track.id,
            status="active",
        ),
    )

    assert created.status == "pending_payment"


def test_premium_enrollment_cannot_be_activated_without_verified_payment(
    db_session,
):
    user = _create_user(db_session)
    track = _create_track(db_session, is_premium=True, suffix="activation")

    enrollment = Enrollment(
        user_id=user.id,
        track_id=track.id,
        status="pending_payment",
    )
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)

    with pytest.raises(HTTPException) as exc_info:
        update_enrollment(
            enrollment_id=enrollment.id,
            session=db_session,
            enrollment_in=EnrollmentUpdate(status="active"),
            current_user=user,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "payment is verified" in exc_info.value.detail

    payment = Payment(
        user_id=user.id,
        track_id=track.id,
        amount=Decimal("150.00"),
        payment_method="INSTAPAY",
        receipt_url="https://example.com/verified.jpg",
        status="VERIFIED",
    )
    db_session.add(payment)
    db_session.commit()

    updated = update_enrollment(
        enrollment_id=enrollment.id,
        session=db_session,
        enrollment_in=EnrollmentUpdate(status="active"),
        current_user=user,
    )

    assert updated.status == "active"


def test_payment_instructions(client):
    response = client.get("/api/v1/payments/instructions")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "vodafone_cash": "01140225360",
        "instapay": "ahmed_morsi2672@instapay",
    }
