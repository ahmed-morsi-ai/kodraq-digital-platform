from fastapi import status

from app.crud.crud_user import user as crud_user
from app.models.role import Role
from app.models.track import Track
from app.models.track_instructor import TrackInstructor
from app.schemas.user import UserCreate


def _create_user_and_get_token(
    client,
    db_session,
    *,
    email: str,
    password: str = "Password123!",
    full_name: str,
    role_name: str | None = None,
    is_superuser: bool = False,
) -> dict[str, str]:
    role_id = None
    if role_name:
        role = db_session.query(Role).filter(Role.name == role_name).first()
        if role is None:
            role = Role(name=role_name, description=f"{role_name} role")
            db_session.add(role)
            db_session.flush()
        role_id = role.id

    crud_user.create(
        db_session,
        obj_in=UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            role_id=role_id,
            is_superuser=is_superuser,
        ),
    )
    response = client.post(
        "/api/v1/login/access-token",
        data={"username": email, "password": password},
    )
    assert response.status_code == status.HTTP_200_OK
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_track(db_session, *, name: str, slug: str) -> Track:
    track = Track(name=name, slug=slug, description=f"{name} description")
    db_session.add(track)
    db_session.flush()
    return track


def _assign_instructor(db_session, *, email: str, track_id: int) -> None:
    instructor = crud_user.get_by_email(db_session, email=email)
    assert instructor is not None
    db_session.add(
        TrackInstructor(track_id=track_id, instructor_id=instructor.id)
    )
    db_session.commit()


def test_admin_can_create_question_with_options(client, db_session):
    admin = _create_user_and_get_token(
        client,
        db_session,
        email="question-admin@example.com",
        full_name="Question Admin",
        is_superuser=True,
    )
    track = _create_track(
        db_session,
        name="Question API Track",
        slug="question-api-track",
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/tracks/{track.id}/questions",
        headers=admin,
        json={
            "text": "Which answer is correct?",
            "question_type": "MULTIPLE_CHOICE",
            "difficulty": 2,
            "points": 5,
            "options": [
                {"text": "Correct", "is_correct": True},
                {"text": "Incorrect", "is_correct": False},
            ],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["track_id"] == track.id
    assert body["text"] == "Which answer is correct?"
    assert body["difficulty"] == 2
    assert len(body["options"]) == 2
    assert body["options"][0]["question_id"] == body["id"]

    detail = client.get(
        f"/api/v1/questions/{body['id']}",
        headers=admin,
    )
    assert detail.status_code == status.HTTP_200_OK
    assert len(detail.json()["options"]) == 2


def test_student_cannot_access_question_bank(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="question-student@example.com",
        full_name="Question Student",
    )
    track = _create_track(
        db_session,
        name="Student Question Track",
        slug="student-question-track",
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/tracks/{track.id}/questions",
        headers=student,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_instructor_is_limited_to_assigned_tracks(client, db_session):
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="question-instructor@example.com",
        full_name="Question Instructor",
        role_name="instructor",
    )
    admin = _create_user_and_get_token(
        client,
        db_session,
        email="question-scope-admin@example.com",
        full_name="Question Scope Admin",
        is_superuser=True,
    )
    assigned_track = _create_track(
        db_session,
        name="Assigned Question Track",
        slug="assigned-question-track",
    )
    other_track = _create_track(
        db_session,
        name="Other Question Track",
        slug="other-question-track",
    )
    db_session.commit()
    _assign_instructor(
        db_session,
        email="question-instructor@example.com",
        track_id=assigned_track.id,
    )

    allowed = client.get(
        f"/api/v1/tracks/{assigned_track.id}/questions",
        headers=instructor,
    )
    assert allowed.status_code == status.HTTP_200_OK

    denied = client.get(
        f"/api/v1/tracks/{other_track.id}/questions",
        headers=instructor,
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    created = client.post(
        f"/api/v1/tracks/{other_track.id}/questions",
        headers=admin,
        json={
            "text": "Scoped question",
            "question_type": "TRUE_FALSE",
        },
    )
    assert created.status_code == status.HTTP_201_CREATED

    denied_detail = client.get(
        f"/api/v1/questions/{created.json()['id']}",
        headers=instructor,
    )
    assert denied_detail.status_code == status.HTTP_403_FORBIDDEN
