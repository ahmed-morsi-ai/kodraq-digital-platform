from __future__ import annotations

from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.role import Role
from app.models.track import Track
from app.models.track_assignment_config import TrackAssignmentConfig
from app.models.user import User


def _create_user(db_session, *, email: str, role_name: str) -> User:
    role = db_session.execute(
        select(Role).where(Role.name == role_name)
    ).scalar_one_or_none()
    if role is None:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()

    user = User(
        email=email,
        hashed_password=get_password_hash("Password123!"),
        full_name=email.split("@")[0],
        is_active=True,
        is_superuser=False,
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _create_track(db_session) -> Track:
    track = Track(
        name="Python Backend",
        slug="python-backend",
        description="Backend track",
        is_active=True,
        ordering=1,
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    return track


def test_get_creates_default_track_assignment_config(client, db_session):
    track = _create_track(db_session)
    student = _create_user(
        db_session,
        email="config-student@example.com",
        role_name="student",
    )

    response = client.get(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        headers=_headers(student),
    )

    assert response.status_code == 200
    assert response.json()["track_id"] == track.id
    assert response.json()["passing_score_threshold"] == 50
    assert response.json()["max_retries"] == 3
    assert response.json()["is_strict_progression"] is False
    assert response.json()["late_submission_policy"] == "ACCEPTED"

    configs = db_session.execute(
        select(TrackAssignmentConfig).where(
            TrackAssignmentConfig.track_id == track.id
        )
    ).scalars().all()
    assert len(configs) == 1

    second = client.get(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        headers=_headers(student),
    )
    assert second.status_code == 200
    assert second.json()["id"] == response.json()["id"]


def test_student_cannot_update_track_assignment_config(client, db_session):
    track = _create_track(db_session)
    student = _create_user(
        db_session,
        email="config-student-update@example.com",
        role_name="student",
    )

    response = client.patch(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        json={"passing_score_threshold": 75},
        headers=_headers(student),
    )

    assert response.status_code == 403


def test_instructor_can_patch_track_assignment_config(client, db_session):
    track = _create_track(db_session)
    instructor = _create_user(
        db_session,
        email="config-instructor@example.com",
        role_name="instructor",
    )

    response = client.patch(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        json={
            "passing_score_threshold": 75,
            "max_retries": 5,
            "is_strict_progression": True,
            "late_submission_policy": "PENALIZED",
        },
        headers=_headers(instructor),
    )

    assert response.status_code == 200
    assert response.json()["passing_score_threshold"] == 75
    assert response.json()["max_retries"] == 5
    assert response.json()["is_strict_progression"] is True
    assert response.json()["late_submission_policy"] == "PENALIZED"


def test_admin_can_put_track_assignment_config(client, db_session):
    track = _create_track(db_session)
    admin = _create_user(
        db_session,
        email="config-admin@example.com",
        role_name="admin",
    )

    response = client.put(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        json={
            "passing_score_threshold": 80,
            "max_retries": 2,
            "is_strict_progression": False,
            "late_submission_policy": "REJECTED",
        },
        headers=_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["passing_score_threshold"] == 80
    assert response.json()["max_retries"] == 2
    assert response.json()["late_submission_policy"] == "REJECTED"


def test_invalid_track_assignment_config_values_are_rejected(client, db_session):
    track = _create_track(db_session)
    admin = _create_user(
        db_session,
        email="config-admin-invalid@example.com",
        role_name="admin",
    )

    response = client.patch(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        json={"passing_score_threshold": 101},
        headers=_headers(admin),
    )
    assert response.status_code == 422

    response = client.patch(
        f"/api/v1/tracks/{track.id}/assignment-config/",
        json={"late_submission_policy": "UNKNOWN"},
        headers=_headers(admin),
    )
    assert response.status_code == 422


def test_track_assignment_config_returns_404_for_missing_track(client, db_session):
    student = _create_user(
        db_session,
        email="config-missing@example.com",
        role_name="student",
    )

    response = client.get(
        "/api/v1/tracks/999999/assignment-config/",
        headers=_headers(student),
    )
    assert response.status_code == 404
