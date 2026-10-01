from __future__ import annotations

from app.core.admin_identity import PLATFORM_ADMIN_EMAIL
from app.core.security import get_password_hash
from app.models.enrollment import Enrollment
from app.models.role import Role
from app.models.track import Track
from app.models.user import User


def create_user_headers(
    client,
    db_session,
    *,
    email: str,
    role_name: str,
    is_superuser: bool = False,
) -> dict[str, str]:
    role = db_session.query(Role).filter(Role.name == role_name).one_or_none()
    if role is None:
        role = Role(name=role_name)
        db_session.add(role)
        db_session.flush()

    password = "TestPassword123!"
    user = User(
        email=email,
        full_name=f"{role_name.title()} Test User",
        hashed_password=get_password_hash(password),
        role_id=role.id,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    db_session.flush()

    response = client.post(
        "/api/v1/login/access-token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_list_and_update_enrollments(client, db_session):
    admin_headers = create_user_headers(
        client,
        db_session,
        email="enrollment-admin@example.test",
        role_name="admin",
    )
    student_headers = create_user_headers(
        client,
        db_session,
        email="enrollment-student@example.test",
        role_name="student",
    )
    student_id = client.get("/api/v1/users/me", headers=student_headers).json()["id"]

    track = Track(
        name="Admin enrollment test track",
        slug="admin-enrollment-test-track",
        is_active=True,
    )
    db_session.add(track)
    db_session.flush()
    enrollment = Enrollment(
        user_id=student_id,
        track_id=track.id,
        status="pending_payment",
    )
    db_session.add(enrollment)
    db_session.flush()

    url = "/api/v1/admin/enrollments"
    response = client.get(url, headers=admin_headers)
    assert response.status_code == 200
    expected_enrollments = [
        {
            "id": enrollment.id,
            "user_id": student_id,
            "student_name": "Student Test User",
            "student_email": "enrollment-student@example.test",
            "track_id": track.id,
            "track_name": track.name,
            "status": "pending_payment",
            "enrolled_at": enrollment.enrolled_at.isoformat(),
        }
    ]
    assert response.json() == expected_enrollments

    slash_response = client.get(
        f"{url}/",
        headers=admin_headers,
        follow_redirects=False,
    )
    assert slash_response.status_code == 200
    assert slash_response.json() == expected_enrollments

    status_url = f"{url}/{enrollment.id}/status"
    activated = client.patch(status_url, headers=admin_headers, json={"status": "active"})
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"

    revoked = client.patch(status_url, headers=admin_headers, json={"status": "cancelled"})
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "cancelled"


def test_admin_activation_creates_missing_primary_track_enrollment(
    client,
    db_session,
):
    admin_headers = create_user_headers(
        client,
        db_session,
        email=PLATFORM_ADMIN_EMAIL,
        role_name="admin",
    )
    create_user_headers(
        client,
        db_session,
        email="activate-sub-student@example.test",
        role_name="student",
    )
    student = db_session.query(User).filter_by(
        email="activate-sub-student@example.test"
    ).one()
    primary_track = Track(
        name="Primary activation track",
        slug="primary-activation-track",
        ordering=1,
        is_active=True,
    )
    secondary_track = Track(
        name="Secondary activation track",
        slug="secondary-activation-track",
        ordering=2,
        is_active=True,
    )
    db_session.add_all([primary_track, secondary_track])
    db_session.flush()
    secondary_enrollment = Enrollment(
        user_id=student.id,
        track_id=secondary_track.id,
        status="pending_payment",
    )
    db_session.add(secondary_enrollment)
    db_session.flush()

    route_variants = [
        (prefix, method, suffix)
        for prefix in ("/api/admin", "/api/v1/admin")
        for method in ("PATCH", "POST")
        for suffix in ("", "/")
    ]
    for index, (prefix, method, suffix) in enumerate(route_variants):
        expected_action = "activated" if index % 2 == 0 else "deactivated"
        expected_message = (
            "Subscription activated"
            if expected_action == "activated"
            else "Subscription deactivated"
        )
        response = client.request(
            method,
            f"{prefix}/users/{student.id}/activate-subscription{suffix}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "action": expected_action,
            "message": expected_message,
        }

    assert student.is_active is True
    db_session.refresh(secondary_enrollment)
    assert secondary_enrollment.status == "pending_payment"

    created_enrollment = db_session.query(Enrollment).filter_by(
        user_id=student.id,
        track_id=primary_track.id,
    ).one()
    assert created_enrollment.status == "inactive"


def test_admin_and_superuser_can_manage_enrollments(client, db_session):
    student_headers = create_user_headers(
        client,
        db_session,
        email="enrollment-forbidden@example.test",
        role_name="student",
    )
    instructor_headers = create_user_headers(
        client,
        db_session,
        email="enrollment-instructor@example.test",
        role_name="instructor",
    )
    superuser_headers = create_user_headers(
        client,
        db_session,
        email="enrollment-superuser@example.test",
        role_name="student",
        is_superuser=True,
    )

    superuser_response = client.get(
        "/api/v1/admin/enrollments",
        headers=superuser_headers,
    )
    assert superuser_response.status_code == 200
    assert superuser_response.json() == []

    for headers in (student_headers, instructor_headers):
        response = client.get("/api/v1/admin/enrollments", headers=headers)
        assert response.status_code == 403


def test_student_enrollment_is_persisted_as_pending(client, db_session):
    student_headers = create_user_headers(
        client,
        db_session,
        email="pending-enrollment@example.test",
        role_name="student",
    )
    student = db_session.query(User).filter_by(
        email="pending-enrollment@example.test"
    ).one()
    track = Track(
        name="Pending enrollment test track",
        slug="pending-enrollment-test-track",
        is_active=True,
    )
    db_session.add(track)
    db_session.flush()

    response = client.post(
        "/api/v1/enrollments",
        headers=student_headers,
        json={"track_id": track.id},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    stored = db_session.query(Enrollment).filter_by(
        user_id=student.id,
        track_id=track.id,
    ).one()
    assert stored.status == "pending"