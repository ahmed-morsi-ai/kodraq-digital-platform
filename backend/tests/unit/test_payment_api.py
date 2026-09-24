from __future__ import annotations

from pathlib import Path

from app.core.security import create_access_token
from app.crud.crud_enrollment import enrollment as crud_enrollment
from app.models.payment import Payment
from app.models.track import Track
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate


def _create_user(
    db_session,
    *,
    email: str,
    is_superuser: bool = False,
) -> User:
    user = User(
        email=email,
        hashed_password="test-hash",
        full_name=email.split("@")[0],
        is_superuser=is_superuser,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_premium_track(db_session) -> Track:
    track = Track(
        name="Payment API Track",
        slug="payment-api-track",
        description="Payment API test track",
        is_premium=True,
        price=150,
        currency="EGP",
    )
    db_session.add(track)
    db_session.flush()
    return track


def _token_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _cleanup_receipt(receipt_url: str) -> None:
    path = Path(__file__).resolve().parents[2] / receipt_url
    path.unlink(missing_ok=True)

def test_student_successfully_submits_receipt(client, db_session):
    student = _create_user(
        db_session,
        email="payment-api-student@example.com",
    )
    track = _create_premium_track(db_session)

    enrollment = crud_enrollment.create_for_user(
        db_session,
        user_id=student.id,
        obj_in=EnrollmentCreate(
            track_id=track.id,
            status="active",
        ),
    )
    assert enrollment.status == "pending_payment"

    response = client.post(
        "/api/v1/payments/submit",
        headers=_token_headers(student),
        data={
            "track_id": str(track.id),
            "payment_method": "VODAFONE_CASH",
        },
        files={
            "receipt": (
                "receipt.png",
                b"fake-png-receipt",
                "image/png",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["track_id"] == track.id
    assert payload["user_id"] == student.id
    assert payload["amount"] == "150.00"
    assert payload["currency"] == "EGP"
    assert payload["status"] == "PENDING_VERIFICATION"
    assert payload["payment_method"] == "VODAFONE_CASH"

    receipt_url = payload["receipt_url"]
    assert receipt_url.startswith("uploads/receipts/")
    receipt_path = Path(__file__).resolve().parents[2] / receipt_url
    assert receipt_path.exists()
    history = client.get(
        "/api/v1/payments/me",
        headers=_token_headers(student),
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    payment = db_session.get(Payment, payload["id"])
    assert payment is not None

    _cleanup_receipt(receipt_url)


def test_admin_verification_activates_pending_enrollment(
    client,
    db_session,
):
    student = _create_user(
        db_session,
        email="payment-api-verification-student@example.com",
    )
    admin = _create_user(
        db_session,
        email="payment-api-admin@example.com",
        is_superuser=True,
    )
    track = _create_premium_track(db_session)

    enrollment = crud_enrollment.create_for_user(
        db_session,
        user_id=student.id,
        obj_in=EnrollmentCreate(
            track_id=track.id,
            status="active",
        ),
    )

    submit_response = client.post(
        "/api/v1/payments/submit",
        headers=_token_headers(student),
        data={
            "track_id": str(track.id),
            "payment_method": "INSTAPAY",
        },
        files={
            "receipt": (
                "receipt.jpg",
                b"fake-jpeg-receipt",
                "image/jpeg",
            )
        },
    )

    assert submit_response.status_code == 201
    payment = submit_response.json()
    receipt_url = payment["receipt_url"]

    verify_response = client.patch(
        f"/api/v1/payments/{payment['id']}/verify",
        headers=_token_headers(admin),
        json={
            "status": "VERIFIED",
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "VERIFIED"

    db_session.refresh(enrollment)
    assert enrollment.status == "active"

    _cleanup_receipt(receipt_url)


def test_student_cannot_verify_own_payment(client, db_session):
    student = _create_user(
        db_session,
        email="payment-api-forbidden-student@example.com",
    )
    track = _create_premium_track(db_session)

    crud_enrollment.create_for_user(
        db_session,
        user_id=student.id,
        obj_in=EnrollmentCreate(
            track_id=track.id,
            status="active",
        ),
    )

    submit_response = client.post(
        "/api/v1/payments/submit",
        headers=_token_headers(student),
        data={
            "track_id": str(track.id),
            "payment_method": "VODAFONE_CASH",
        },
        files={
            "receipt": (
                "receipt.webp",
                b"fake-webp-receipt",
                "image/webp",
            )
        },
    )

    assert submit_response.status_code == 201
    payment = submit_response.json()
    receipt_url = payment["receipt_url"]

    verify_response = client.patch(
        f"/api/v1/payments/{payment['id']}/verify",
        headers=_token_headers(student),
        json={"status": "VERIFIED"},
    )

    assert verify_response.status_code == 403
    assert db_session.get(Payment, payment["id"]).status == (
        "PENDING_VERIFICATION"
    )

    _cleanup_receipt(receipt_url)
