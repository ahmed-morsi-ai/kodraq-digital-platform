from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import status

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.crud.crud_assignment import create_assignment
from app.models.enrollment import Enrollment
from app.models.role import Role
from app.models.track import Lesson, Track, TrackModule
from app.models.track_instructor import TrackInstructor
from app.models.user import User
from app.schemas.assignment import AssignmentCreate

ASSIGNMENTS_URL = f"{settings.API_V1_STR}/assignments"


def _create_role_user(
    db_session,
    *,
    role_name: str,
    is_superuser: bool = False,
) -> User:
    role = Role(
        name=role_name,
        description=f"{role_name} test role",
    )
    db_session.add(role)
    db_session.flush()

    user = User(
        email=f"{role_name}@api-test.local",
        hashed_password="not-used-in-api-tests",
        full_name=f"{role_name.title()} API Tester",
        is_active=True,
        is_superuser=is_superuser,
        role_id=role.id,
    )
    db_session.add(user)
    db_session.flush()

    return user


def test_student_cannot_update_assignment(client, db_session):
    student = _create_role_user(
        db_session,
        role_name="student",
    )
    assignment, _, _, _ = _create_assignment(db_session)

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: student

    try:
        response = client.patch(
            f"{ASSIGNMENTS_URL}/{assignment.id}",
            json={
                "title": "Student Must Not Update",
            },
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "Only admins and instructors can manage assignments"
    )


def _create_context(db_session):
    track = Track(
        name="API Test Track",
        slug="api-test-track",
        description="API test track",
        ordering=1,
    )
    db_session.add(track)
    db_session.flush()

    module = TrackModule(
        track_id=track.id,
        title="API Test Module",
        description="API test module",
        ordering=1,
    )
    db_session.add(module)
    db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        title="API Test Lesson",
        content="API test lesson",
        ordering=1,
    )
    db_session.add(lesson)
    db_session.flush()

    return track, module, lesson


def _create_assignment(db_session):
    track, module, lesson = _create_context(db_session)

    assignment = create_assignment(
        db_session,
        AssignmentCreate(
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
            title="API Assignment",
            description="API assignment description",
            instructions="API assignment instructions",
            difficulty="intermediate",
            ordering=1,
        ),
    )

    return assignment, track, module, lesson


def test_assignment_api_requires_authentication(client):
    response = client.get(ASSIGNMENTS_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_student_can_read_assignments(client, db_session):
    student = _create_role_user(
        db_session,
        role_name="student",
    )
    assignment, track, _, _ = _create_assignment(db_session)
    db_session.add(
        Enrollment(
            user_id=student.id,
            track_id=track.id,
            status="active",
            enrolled_at=datetime.now(UTC),
        )
    )
    db_session.flush()

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: student

    try:
        response = client.get(
            ASSIGNMENTS_URL,
            params={"track_id": track.id},
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == assignment.id
    assert data[0]["title"] == "API Assignment"


def test_student_cannot_create_assignment(client, db_session):
    student = _create_role_user(
        db_session,
        role_name="student",
    )
    track, module, lesson = _create_context(db_session)

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: student

    try:
        response = client.post(
            ASSIGNMENTS_URL,
            json={
                "track_id": track.id,
                "module_id": module.id,
                "lesson_id": lesson.id,
                "title": "Forbidden Assignment",
                "description": "Should be forbidden",
                "instructions": "Should be forbidden",
                "difficulty": "beginner",
                "ordering": 1,
                "is_mandatory": True,
                "is_active": True,
            },
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "Only admins and instructors can manage assignments"
    )


def test_instructor_can_create_assignment(client, db_session):
    instructor = _create_role_user(
        db_session,
        role_name="instructor",
    )
    track, module, lesson = _create_context(db_session)
    db_session.add(TrackInstructor(track_id=track.id, instructor_id=instructor.id))
    db_session.flush()

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: instructor

    try:
        response = client.post(
            ASSIGNMENTS_URL,
            json={
                "track_id": track.id,
                "module_id": module.id,
                "lesson_id": lesson.id,
                "title": "Instructor Assignment",
                "description": "Created by instructor",
                "instructions": "Instructor instructions",
                "difficulty": "advanced",
                "ordering": 2,
                "is_mandatory": False,
                "is_active": True,
            },
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["title"] == "Instructor Assignment"
    assert data["difficulty"] == "advanced"
    assert data["is_mandatory"] is False
    assert data["track_id"] == track.id
    assert data["module_id"] == module.id
    assert data["lesson_id"] == lesson.id


def test_admin_can_update_assignment(client, db_session):
    admin = _create_role_user(
        db_session,
        role_name="admin",
    )
    assignment, _, _, _ = _create_assignment(db_session)

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: admin

    try:
        response = client.patch(
            f"{ASSIGNMENTS_URL}/{assignment.id}",
            json={
                "title": "Updated Through API",
                "difficulty": "advanced",
                "ordering": 7,
                "is_mandatory": False,
            },
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == assignment.id
    assert data["title"] == "Updated Through API"
    assert data["difficulty"] == "advanced"
    assert data["ordering"] == 7
    assert data["is_mandatory"] is False


def test_student_cannot_delete_assignment(client, db_session):
    student = _create_role_user(
        db_session,
        role_name="student",
    )
    assignment, _, _, _ = _create_assignment(db_session)

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: student

    try:
        response = client.delete(
            f"{ASSIGNMENTS_URL}/{assignment.id}",
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "Only admins and instructors can manage assignments"
    )


def test_assignment_api_get_by_id_and_not_found(client, db_session):
    student = _create_role_user(
        db_session,
        role_name="student",
    )
    assignment, track, _, _ = _create_assignment(db_session)
    db_session.add(
        Enrollment(
            user_id=student.id,
            track_id=track.id,
            status="active",
            enrolled_at=datetime.now(UTC),
        )
    )
    db_session.flush()

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: student

    try:
        response = client.get(
            f"{ASSIGNMENTS_URL}/{assignment.id}",
        )
        missing_response = client.get(
            f"{ASSIGNMENTS_URL}/999999",
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == assignment.id

    assert missing_response.status_code == status.HTTP_404_NOT_FOUND
    assert missing_response.json()["detail"] == "Assignment not found"


def test_assignment_api_validates_context_relationships(client, db_session):
    instructor = _create_role_user(
        db_session,
        role_name="instructor",
    )

    track_a, module_a, lesson_a = _create_context(db_session)
    track_b = Track(
        name="Different API Track",
        slug="different-api-track",
        description="Different track",
        ordering=2,
    )
    db_session.add(track_b)
    db_session.flush()

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: instructor

    try:
        response = client.post(
            ASSIGNMENTS_URL,
            json={
                "track_id": track_b.id,
                "module_id": module_a.id,
                "lesson_id": lesson_a.id,
                "title": "Invalid Context",
                "description": "Invalid context",
                "instructions": "Invalid context",
                "difficulty": "beginner",
                "ordering": 1,
            },
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "module_id does not belong to track_id."


def test_admin_can_delete_assignment(client, db_session):
    admin = _create_role_user(
        db_session,
        role_name="admin",
    )
    assignment, _, _, _ = _create_assignment(db_session)

    app_dependency_overrides = client.app.dependency_overrides
    app_dependency_overrides[get_current_active_user] = lambda: admin

    try:
        response = client.delete(
            f"{ASSIGNMENTS_URL}/{assignment.id}",
        )
    finally:
        app_dependency_overrides.clear()

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize(
    ("field", "detail"),
    [
        ("track_id", "Track not found"),
        ("module_id", "Track module not found"),
        ("lesson_id", "Lesson not found"),
    ],
)
def test_assignment_api_missing_context_returns_404(
    client, db_session, method, field, detail
):
    admin = _create_role_user(db_session, role_name="admin")
    created, track, module, lesson = _create_assignment(db_session)
    client.app.dependency_overrides[get_current_active_user] = lambda: admin
    if method == "post":
        payload = {
            "title": "Missing context",
            "description": "Description",
            "instructions": "Instructions",
            "difficulty": "beginner",
            field: 999999,
        }
        response = client.post(ASSIGNMENTS_URL, json=payload)
    else:
        response = client.patch(f"{ASSIGNMENTS_URL}/{created.id}", json={field: 999999})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == detail
    db_session.refresh(created)
    assert (created.track_id, created.module_id, created.lesson_id) == (
        track.id,
        module.id,
        lesson.id,
    )


@pytest.mark.parametrize("mismatch", ["module_track", "lesson_module", "lesson_track"])
def test_assignment_api_partial_update_rejects_inconsistent_context(
    client, db_session, mismatch
):
    admin = _create_role_user(db_session, role_name="admin")
    created, track, module, lesson = _create_assignment(db_session)
    other_track = Track(name="Other PATCH track", slug="other-patch-track")
    other_module = TrackModule(title="Other PATCH module", track=other_track)
    db_session.add_all([other_track, other_module])
    db_session.flush()
    changes, detail = {
        "module_track": (
            {"track_id": other_track.id},
            "module_id does not belong to track_id.",
        ),
        "lesson_module": (
            {"track_id": None, "module_id": other_module.id},
            "lesson_id does not belong to module_id.",
        ),
        "lesson_track": (
            {"track_id": other_track.id, "module_id": None},
            "lesson_id does not belong to track_id.",
        ),
    }[mismatch]
    client.app.dependency_overrides[get_current_active_user] = lambda: admin
    response = client.patch(f"{ASSIGNMENTS_URL}/{created.id}", json=changes)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == detail
    db_session.refresh(created)
    assert (created.track_id, created.module_id, created.lesson_id) == (
        track.id,
        module.id,
        lesson.id,
    )


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_assignment_api_missing_record_returns_404(client, db_session, method):
    admin = _create_role_user(db_session, role_name="admin")
    client.app.dependency_overrides[get_current_active_user] = lambda: admin
    kwargs = {"json": {"title": "Missing assignment"}} if method == "patch" else {}
    response = getattr(client, method)(f"{ASSIGNMENTS_URL}/999999", **kwargs)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Assignment not found"


@pytest.mark.parametrize("invalid", [{"title": None}, {"id": 999999}])
def test_assignment_api_rejects_invalid_update_fields(client, db_session, invalid):
    admin = _create_role_user(db_session, role_name="admin")
    created, _, _, _ = _create_assignment(db_session)
    original_id = created.id
    client.app.dependency_overrides[get_current_active_user] = lambda: admin
    response = client.patch(f"{ASSIGNMENTS_URL}/{created.id}", json=invalid)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    db_session.refresh(created)
    assert created.title == "API Assignment"
    assert created.id == original_id


@pytest.mark.parametrize("field", ["skip", "limit"])
def test_assignment_api_rejects_negative_pagination(client, db_session, field):
    student = _create_role_user(db_session, role_name="student")
    client.app.dependency_overrides[get_current_active_user] = lambda: student
    response = client.get(ASSIGNMENTS_URL, params={field: -1})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response = client.get(ASSIGNMENTS_URL, params={"limit": 0})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_assignment_api_patch_preserves_falsy_values_and_clears_optional_context(
    client, db_session
):
    admin = _create_role_user(db_session, role_name="admin")
    created, track, module, _ = _create_assignment(db_session)
    client.app.dependency_overrides[get_current_active_user] = lambda: admin
    response = client.patch(
        f"{ASSIGNMENTS_URL}/{created.id}",
        json={
            "lesson_id": None,
            "ordering": 0,
            "is_mandatory": False,
            "is_active": False,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["lesson_id"] is None
    assert data["track_id"] == track.id
    assert data["module_id"] == module.id
    assert data["ordering"] == 0
    assert data["is_mandatory"] is False
    assert data["is_active"] is False
    assert data["instructions"] == "API assignment instructions"
