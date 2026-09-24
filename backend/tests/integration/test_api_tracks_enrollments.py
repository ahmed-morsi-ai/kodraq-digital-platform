from __future__ import annotations

from fastapi import status

from app.crud.crud_user import user as crud_user
from app.schemas.user import UserCreate


def create_user_and_get_token(
    client,
    db_session,
    *,
    email: str,
    password: str,
    full_name: str,
    is_superuser: bool = False,
) -> dict[str, str]:
    crud_user.create(
        db_session,
        obj_in=UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            is_superuser=is_superuser,
        ),
    )

    response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
    }


def test_track_curriculum_endpoints_and_rbac(client, db_session):
    student_headers = create_user_and_get_token(
        client,
        db_session,
        email="track-student@example.com",
        password="Password123!",
        full_name="Track Student",
    )

    admin_headers = create_user_and_get_token(
        client,
        db_session,
        email="track-admin@example.com",
        password="AdminPassword123!",
        full_name="Track Admin",
        is_superuser=True,
    )

    denied = client.post(
        "/api/v1/tracks",
        headers=student_headers,
        json={
            "name": "Denied Track",
            "slug": "denied-track",
            "description": "Should be denied",
        },
    )

    assert denied.status_code == status.HTTP_403_FORBIDDEN

    created = client.post(
        "/api/v1/tracks",
        headers=admin_headers,
        json={
            "name": "Backend Engineering",
            "slug": "backend-engineering",
            "description": "Backend bootcamp",
            "ordering": 1,
        },
    )

    assert created.status_code == status.HTTP_201_CREATED
    track_id = created.json()["id"]

    listing = client.get("/api/v1/tracks")
    assert listing.status_code == status.HTTP_200_OK
    assert any(item["id"] == track_id for item in listing.json())

    module_response = client.post(
        f"/api/v1/tracks/{track_id}/modules",
        headers=admin_headers,
        json={
            "track_id": track_id,
            "title": "FastAPI",
            "description": "FastAPI fundamentals",
            "ordering": 1,
        },
    )

    assert module_response.status_code == status.HTTP_201_CREATED
    module_id = module_response.json()["id"]

    lesson_response = client.post(
        f"/api/v1/tracks/modules/{module_id}/lessons",
        headers=admin_headers,
        json={
            "module_id": module_id,
            "title": "Dependencies",
            "content": "Dependency injection",
            "ordering": 1,
        },
    )

    assert lesson_response.status_code == status.HTTP_201_CREATED

    resource_response = client.post(
        f"/api/v1/tracks/modules/{module_id}/resources",
        headers=admin_headers,
        json={
            "title": "FastAPI Documentation",
            "file_url": "https://example.com/fastapi.pdf",
            "resource_type": "pdf",
        },
    )

    assert resource_response.status_code == status.HTTP_201_CREATED

    unauthenticated_curriculum = client.get(
        f"/api/v1/tracks/{track_id}/curriculum"
    )
    assert unauthenticated_curriculum.status_code == status.HTTP_401_UNAUTHORIZED

    locked_curriculum = client.get(
        f"/api/v1/tracks/{track_id}/curriculum",
        headers=student_headers,
    )
    assert locked_curriculum.status_code == status.HTTP_200_OK
    locked_data = locked_curriculum.json()

    assert locked_data["id"] == track_id
    assert len(locked_data["modules"]) == 1

    locked_module = locked_data["modules"][0]
    assert locked_module["title"] == "FastAPI"
    assert len(locked_module["lessons"]) == 1
    assert len(locked_module["resources"]) == 1

    locked_lesson = locked_module["lessons"][0]
    assert locked_lesson["title"] == "Dependencies"
    assert locked_lesson["content"]
    assert locked_lesson["content"] != "Dependency injection"

    curriculum = client.get(
        f"/api/v1/tracks/{track_id}/curriculum",
        headers=admin_headers,
    )
    assert curriculum.status_code == status.HTTP_200_OK
    data = curriculum.json()
    assert data["id"] == track_id
    assert len(data["modules"]) == 1
    assert len(data["modules"][0]["lessons"]) == 1
    assert len(data["modules"][0]["resources"]) == 1
    assert data["modules"][0]["lessons"][0]["content"] == "Dependency injection"


def test_enrollment_and_progress_endpoints(client, db_session):
    student_headers = create_user_and_get_token(
        client,
        db_session,
        email="enrollment-student@example.com",
        password="Password123!",
        full_name="Enrollment Student",
    )

    other_headers = create_user_and_get_token(
        client,
        db_session,
        email="other-student@example.com",
        password="Password123!",
        full_name="Other Student",
    )

    admin_headers = create_user_and_get_token(
        client,
        db_session,
        email="enrollment-admin@example.com",
        password="AdminPassword123!",
        full_name="Enrollment Admin",
        is_superuser=True,
    )

    track_response = client.post(
        "/api/v1/tracks",
        headers=admin_headers,
        json={
            "name": "AI Engineering",
            "slug": "ai-engineering",
            "description": "AI Engineering track",
            "ordering": 1,
        },
    )

    assert track_response.status_code == status.HTTP_201_CREATED
    track_id = track_response.json()["id"]

    module_response = client.post(
        f"/api/v1/tracks/{track_id}/modules",
        headers=admin_headers,
        json={
            "track_id": track_id,
            "title": "Machine Learning",
            "ordering": 1,
        },
    )

    module_id = module_response.json()["id"]

    lesson_response = client.post(
        f"/api/v1/tracks/modules/{module_id}/lessons",
        headers=admin_headers,
        json={
            "module_id": module_id,
            "title": "Supervised Learning",
            "ordering": 1,
        },
    )

    lesson_id = lesson_response.json()["id"]

    enrollment_response = client.post(
        "/api/v1/enrollments",
        headers=student_headers,
        json={
            "track_id": track_id,
            "status": "active",
        },
    )

    assert enrollment_response.status_code == status.HTTP_201_CREATED
    enrollment_id = enrollment_response.json()["id"]

    duplicate_response = client.post(
        "/api/v1/enrollments",
        headers=student_headers,
        json={
            "track_id": track_id,
            "status": "active",
        },
    )

    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST

    my_enrollments = client.get(
        "/api/v1/enrollments/me",
        headers=student_headers,
    )

    assert my_enrollments.status_code == status.HTTP_200_OK
    assert len(my_enrollments.json()) == 1

    own_enrollment = client.get(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=student_headers,
    )

    assert own_enrollment.status_code == status.HTTP_200_OK

    progress_response = client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        headers=student_headers,
        json={
            "enrollment_id": enrollment_id,
            "lesson_id": lesson_id,
            "status": "in_progress",
            "progress_percentage": 50,
        },
    )

    assert progress_response.status_code == status.HTTP_201_CREATED
    progress_id = progress_response.json()["id"]

    progress_list = client.get(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        headers=student_headers,
    )

    assert progress_list.status_code == status.HTTP_200_OK
    assert len(progress_list.json()) == 1

    progress_update = client.patch(
        f"/api/v1/enrollments/{enrollment_id}/progress/{progress_id}",
        headers=student_headers,
        json={
            "status": "completed",
            "progress_percentage": 100,
        },
    )

    assert progress_update.status_code == status.HTTP_200_OK
    assert progress_update.json()["progress_percentage"] == 100

    forbidden_progress = client.get(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        headers=other_headers,
    )

    assert forbidden_progress.status_code == status.HTTP_403_FORBIDDEN

    admin_enrollments = client.get(
        f"/api/v1/enrollments/track/{track_id}",
        headers=admin_headers,
    )

    assert admin_enrollments.status_code == status.HTTP_200_OK
    assert len(admin_enrollments.json()) == 1

    admin_update = client.patch(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=admin_headers,
        json={
            "status": "completed",
        },
    )

    assert admin_update.status_code == status.HTTP_200_OK
    assert admin_update.json()["status"] == "completed"


def test_invalid_progress_lesson_is_rejected(client, db_session):
    student_headers = create_user_and_get_token(
        client,
        db_session,
        email="progress-student@example.com",
        password="Password123!",
        full_name="Progress Student",
    )

    admin_headers = create_user_and_get_token(
        client,
        db_session,
        email="progress-admin@example.com",
        password="AdminPassword123!",
        full_name="Progress Admin",
        is_superuser=True,
    )

    first_track = client.post(
        "/api/v1/tracks",
        headers=admin_headers,
        json={
            "name": "Frontend Engineering",
            "slug": "frontend-engineering",
        },
    ).json()

    second_track = client.post(
        "/api/v1/tracks",
        headers=admin_headers,
        json={
            "name": "Computer Vision",
            "slug": "computer-vision",
        },
    ).json()

    module = client.post(
        f"/api/v1/tracks/{second_track['id']}/modules",
        headers=admin_headers,
        json={
            "track_id": second_track["id"],
            "title": "Vision Module",
        },
    ).json()

    lesson = client.post(
        f"/api/v1/tracks/modules/{module['id']}/lessons",
        headers=admin_headers,
        json={
            "module_id": module["id"],
            "title": "Image Classification",
        },
    ).json()

    enrollment = client.post(
        "/api/v1/enrollments",
        headers=student_headers,
        json={
            "track_id": first_track["id"],
            "status": "active",
        },
    ).json()

    response = client.post(
        f"/api/v1/enrollments/{enrollment['id']}/progress",
        headers=student_headers,
        json={
            "enrollment_id": enrollment["id"],
            "lesson_id": lesson["id"],
            "status": "in_progress",
            "progress_percentage": 25,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "enrolled track" in response.json()["detail"].lower()
