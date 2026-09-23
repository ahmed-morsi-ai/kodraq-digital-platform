from __future__ import annotations

from sqlalchemy import select

from app.crud.crud_user import user as crud_user
from app.models.enrollment import Enrollment
from app.models.final_project import ProjectRequirement, TrainingProject
from app.models.role import Role
from app.models.track import Track
from app.models.track_instructor import TrackInstructor
from app.schemas.user import UserCreate


def _create_user_and_get_token(
    client,
    db_session,
    *,
    email: str,
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
            password="Password123!",
            full_name=full_name,
            role_id=role_id,
            is_superuser=is_superuser,
        ),
    )

    response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": email,
            "password": "Password123!",
        },
    )

    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_track(db_session, *, name: str, slug: str) -> Track:
    track = Track(
        name=name,
        slug=slug,
        description="Final project API test track",
    )
    db_session.add(track)
    db_session.flush()
    return track


def _assign_instructor(
    db_session,
    *,
    email: str,
    track_id: int,
) -> None:
    instructor = crud_user.get_by_email(
        db_session,
        email=email,
    )
    assert instructor is not None

    db_session.add(
        TrackInstructor(
            track_id=track_id,
            instructor_id=instructor.id,
        )
    )
    db_session.commit()


def _create_final_project(
    db_session,
    *,
    track_id: int,
) -> TrainingProject:
    project = TrainingProject(
        track_id=track_id,
        title="Capstone Project",
        description="Build the final product.",
        passing_score=75,
        requirements=[
            ProjectRequirement(
                description="Authentication is implemented.",
                is_mandatory=True,
                order=1,
            ),
            ProjectRequirement(
                description="Automated tests are included.",
                is_mandatory=True,
                order=2,
            ),
        ],
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_admin_can_create_final_project_with_nested_requirements(
    client,
    db_session,
):
    admin = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-admin@example.com",
        full_name="Final Project Admin",
        is_superuser=True,
    )
    track = _create_track(
        db_session,
        name="Final Project Admin Track",
        slug="final-project-admin-track",
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/tracks/{track.id}/final-project",
        headers=admin,
        json={
            "title": "Build a Production API",
            "description": "Final capstone project.",
            "passing_score": 80,
            "requirements": [
                {
                    "description": "Authentication works.",
                    "is_mandatory": True,
                    "order": 1,
                },
                {
                    "description": "Tests cover the core flows.",
                    "is_mandatory": False,
                    "order": 2,
                },
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["track_id"] == track.id
    assert body["title"] == "Build a Production API"
    assert body["passing_score"] == 80
    assert len(body["requirements"]) == 2
    assert body["requirements"][0]["description"] == "Authentication works."


def test_enrolled_student_can_view_final_project(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-enrolled-student@example.com",
        full_name="Final Project Enrolled Student",
    )
    track = _create_track(
        db_session,
        name="Final Project Student Track",
        slug="final-project-student-track",
    )
    db_session.commit()

    student_user = crud_user.get_by_email(
        db_session,
        email="final-project-enrolled-student@example.com",
    )
    assert student_user is not None

    db_session.add(
        Enrollment(
            user_id=student_user.id,
            track_id=track.id,
            status="active",
        )
    )

    project = _create_final_project(
        db_session,
        track_id=track.id,
    )

    response = client.get(
        f"/api/v1/tracks/{track.id}/final-project",
        headers=student,
    )

    assert response.status_code == 200
    body = response.json()

    assert body["id"] == project.id
    assert body["track_id"] == track.id
    assert len(body["requirements"]) == 2


def test_unenrolled_student_is_denied_final_project_access(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-unenrolled-student@example.com",
        full_name="Final Project Unenrolled Student",
    )
    track = _create_track(
        db_session,
        name="Final Project Restricted Track",
        slug="final-project-restricted-track",
    )
    db_session.commit()

    _create_final_project(
        db_session,
        track_id=track.id,
    )

    response = client.get(
        f"/api/v1/tracks/{track.id}/final-project",
        headers=student,
    )

    assert response.status_code == 403


def test_instructor_is_limited_to_assigned_tracks(
    client,
    db_session,
):
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-instructor@example.com",
        full_name="Final Project Instructor",
        role_name="instructor",
    )
    assigned_track = _create_track(
        db_session,
        name="Final Project Assigned Track",
        slug="final-project-assigned-track",
    )
    other_track = _create_track(
        db_session,
        name="Final Project Other Track",
        slug="final-project-other-track",
    )
    db_session.commit()

    _assign_instructor(
        db_session,
        email="final-project-instructor@example.com",
        track_id=assigned_track.id,
    )

    assigned_create = client.post(
        f"/api/v1/tracks/{assigned_track.id}/final-project",
        headers=instructor,
        json={
            "title": "Assigned Capstone",
            "requirements": [
                {
                    "description": "Assigned requirement",
                    "is_mandatory": True,
                    "order": 1,
                }
            ],
        },
    )
    assert assigned_create.status_code == 201

    denied_create = client.post(
        f"/api/v1/tracks/{other_track.id}/final-project",
        headers=instructor,
        json={
            "title": "Unauthorized Capstone",
            "requirements": [],
        },
    )
    assert denied_create.status_code == 403

    denied_get = client.get(
        f"/api/v1/tracks/{other_track.id}/final-project",
        headers=instructor,
    )
    assert denied_get.status_code == 403


def test_student_cannot_modify_final_project(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-write-student@example.com",
        full_name="Final Project Write Student",
    )
    track = _create_track(
        db_session,
        name="Final Project Student Write Track",
        slug="final-project-student-write-track",
    )
    db_session.commit()

    student_user = crud_user.get_by_email(
        db_session,
        email="final-project-write-student@example.com",
    )
    assert student_user is not None

    db_session.add(
        Enrollment(
            user_id=student_user.id,
            track_id=track.id,
            status="active",
        )
    )

    project = _create_final_project(
        db_session,
        track_id=track.id,
    )

    response = client.patch(
        f"/api/v1/final-projects/{project.id}",
        headers=student,
        json={"title": "Unauthorized Update"},
    )

    assert response.status_code == 403


def test_nested_requirement_update_replaces_requirements(
    client,
    db_session,
):
    admin = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-update-admin@example.com",
        full_name="Final Project Update Admin",
        is_superuser=True,
    )
    track = _create_track(
        db_session,
        name="Final Project Update Track",
        slug="final-project-update-track",
    )
    db_session.commit()

    project = _create_final_project(
        db_session,
        track_id=track.id,
    )

    response = client.patch(
        f"/api/v1/final-projects/{project.id}",
        headers=admin,
        json={
            "title": "Updated Capstone",
            "passing_score": 85,
            "requirements": [
                {
                    "description": "Updated requirement.",
                    "is_mandatory": True,
                    "order": 1,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["title"] == "Updated Capstone"
    assert body["passing_score"] == 85
    assert len(body["requirements"]) == 1
    assert body["requirements"][0]["description"] == "Updated requirement."


def test_delete_final_project_cascades_requirements(
    client,
    db_session,
):
    admin = _create_user_and_get_token(
        client,
        db_session,
        email="final-project-delete-admin@example.com",
        full_name="Final Project Delete Admin",
        is_superuser=True,
    )
    track = _create_track(
        db_session,
        name="Final Project Delete Track",
        slug="final-project-delete-track",
    )
    db_session.commit()

    project = _create_final_project(
        db_session,
        track_id=track.id,
    )
    requirement_ids = [
        requirement.id
        for requirement in project.requirements
    ]

    response = client.delete(
        f"/api/v1/final-projects/{project.id}",
        headers=admin,
    )

    assert response.status_code == 204
    assert db_session.get(TrainingProject, project.id) is None

    remaining = db_session.scalars(
        select(ProjectRequirement).where(
            ProjectRequirement.id.in_(requirement_ids)
        )
    ).all()

    assert remaining == []

