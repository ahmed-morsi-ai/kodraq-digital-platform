from __future__ import annotations

from sqlalchemy import select

from app.crud.crud_user import user as crud_user
from app.models.enrollment import Enrollment
from app.models.final_project import TrainingProject
from app.models.project_submission import ProjectSubmission
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
        role = (
            db_session.query(Role)
            .filter(Role.name == role_name)
            .first()
        )
        if role is None:
            role = Role(
                name=role_name,
                description=f"{role_name} role",
            )
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

    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
    }


def _create_track(
    db_session,
    *,
    name: str,
    slug: str,
) -> Track:
    track = Track(
        name=name,
        slug=slug,
        description="Final project submission test track",
    )
    db_session.add(track)
    db_session.flush()
    return track


def _create_project(
    db_session,
    *,
    track_id: int,
) -> TrainingProject:
    project = TrainingProject(
        track_id=track_id,
        title="Final Submission Project",
        description="Submission test project.",
        passing_score=75,
        is_active=True,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _enroll_student(
    db_session,
    *,
    email: str,
    track_id: int,
) -> int:
    student = crud_user.get_by_email(
        db_session,
        email=email,
    )
    assert student is not None

    db_session.add(
        Enrollment(
            user_id=student.id,
            track_id=track_id,
            status="active",
        )
    )
    db_session.commit()

    return student.id


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


def test_enrolled_student_can_create_and_update_final_project_submission(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="project-submission-student@example.com",
        full_name="Project Submission Student",
    )
    track = _create_track(
        db_session,
        name="Project Submission Track",
        slug="project-submission-track",
    )
    db_session.commit()

    _enroll_student(
        db_session,
        email="project-submission-student@example.com",
        track_id=track.id,
    )
    project = _create_project(
        db_session,
        track_id=track.id,
    )

    create_response = client.post(
        f"/api/v1/final-projects/{project.id}/submissions",
        headers=student,
        json={
            "github_url": "https://github.com/example/final-project",
            "live_url": "https://example.com",
            "file_url": "https://example.com/project.zip",
            "student_notes": "Initial draft submission.",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()

    assert created["project_id"] == project.id
    assert created["github_url"] == (
        "https://github.com/example/final-project"
    )
    assert created["status"] == "DRAFT"
    assert created["submitted_at"] is None

    update_response = client.patch(
        f"/api/v1/final-projects/submissions/{created['id']}",
        headers=student,
        json={
            "student_notes": "Ready for review.",
            "status": "SUBMITTED",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()

    assert updated["student_notes"] == "Ready for review."
    assert updated["status"] == "SUBMITTED"
    assert updated["submitted_at"] is not None

    mine_response = client.get(
        "/api/v1/final-projects/submissions/me",
        headers=student,
    )

    assert mine_response.status_code == 200
    mine = mine_response.json()

    assert len(mine) == 1
    assert mine[0]["id"] == created["id"]
    assert mine[0]["project_id"] == project.id


def test_student_cannot_update_submitted_or_approved_submission(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="project-submission-state-student@example.com",
        full_name="Project Submission State Student",
    )
    track_one = _create_track(
        db_session,
        name="Project Submission State Track One",
        slug="project-submission-state-track-one",
    )
    track_two = _create_track(
        db_session,
        name="Project Submission State Track Two",
        slug="project-submission-state-track-two",
    )
    db_session.commit()

    _enroll_student(
        db_session,
        email="project-submission-state-student@example.com",
        track_id=track_one.id,
    )
    _enroll_student(
        db_session,
        email="project-submission-state-student@example.com",
        track_id=track_two.id,
    )

    project_one = _create_project(
        db_session,
        track_id=track_one.id,
    )
    project_two = _create_project(
        db_session,
        track_id=track_two.id,
    )

    submission_one = ProjectSubmission(
        project_id=project_one.id,
        student_id=crud_user.get_by_email(
            db_session,
            email="project-submission-state-student@example.com",
        ).id,
        status="SUBMITTED",
        github_url="https://github.com/example/submitted",
    )
    submission_two = ProjectSubmission(
        project_id=project_two.id,
        student_id=submission_one.student_id,
        status="APPROVED",
        github_url="https://github.com/example/approved",
    )

    db_session.add_all([submission_one, submission_two])
    db_session.commit()

    submitted_response = client.patch(
        f"/api/v1/final-projects/submissions/{submission_one.id}",
        headers=student,
        json={"student_notes": "Unauthorized update."},
    )
    approved_response = client.patch(
        f"/api/v1/final-projects/submissions/{submission_two.id}",
        headers=student,
        json={"student_notes": "Unauthorized update."},
    )

    assert submitted_response.status_code == 403
    assert approved_response.status_code == 403


def test_admin_and_assigned_instructor_can_read_project_submissions(
    client,
    db_session,
):
    admin = _create_user_and_get_token(
        client,
        db_session,
        email="project-submission-admin@example.com",
        full_name="Project Submission Admin",
        is_superuser=True,
    )
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="project-submission-instructor@example.com",
        full_name="Project Submission Instructor",
        role_name="instructor",
    )

    track = _create_track(
        db_session,
        name="Project Submission Access Track",
        slug="project-submission-access-track",
    )
    other_track = _create_track(
        db_session,
        name="Project Submission Other Track",
        slug="project-submission-other-track",
    )
    db_session.commit()

    project = _create_project(
        db_session,
        track_id=track.id,
    )
    other_project = _create_project(
        db_session,
        track_id=other_track.id,
    )

    _assign_instructor(
        db_session,
        email="project-submission-instructor@example.com",
        track_id=track.id,
    )

    student = _create_user_and_get_token(
        client,
        db_session,
        email="project-submission-read-student@example.com",
        full_name="Project Submission Read Student",
    )

    _enroll_student(
        db_session,
        email="project-submission-read-student@example.com",
        track_id=track.id,
    )

    create_response = client.post(
        f"/api/v1/final-projects/{project.id}/submissions",
        headers=student,
        json={
            "github_url": "https://github.com/example/read-access",
        },
    )
    assert create_response.status_code == 201

    admin_response = client.get(
        f"/api/v1/final-projects/{project.id}/submissions",
        headers=admin,
    )
    instructor_response = client.get(
        f"/api/v1/final-projects/{project.id}/submissions",
        headers=instructor,
    )
    denied_response = client.get(
        f"/api/v1/final-projects/{other_project.id}/submissions",
        headers=instructor,
    )

    assert admin_response.status_code == 200
    assert len(admin_response.json()) == 1
    assert instructor_response.status_code == 200
    assert len(instructor_response.json()) == 1
    assert denied_response.status_code == 403


def test_student_can_only_have_one_project_submission(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="project-submission-duplicate@example.com",
        full_name="Project Submission Duplicate Student",
    )
    track = _create_track(
        db_session,
        name="Project Submission Duplicate Track",
        slug="project-submission-duplicate-track",
    )
    db_session.commit()

    _enroll_student(
        db_session,
        email="project-submission-duplicate@example.com",
        track_id=track.id,
    )

    project = _create_project(
        db_session,
        track_id=track.id,
    )

    first_response = client.post(
        f"/api/v1/final-projects/{project.id}/submissions",
        headers=student,
        json={"student_notes": "First submission."},
    )
    second_response = client.post(
        f"/api/v1/final-projects/{project.id}/submissions",
        headers=student,
        json={"student_notes": "Duplicate submission."},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    student_id = crud_user.get_by_email(
        db_session,
        email="project-submission-duplicate@example.com",
    ).id

    count = db_session.scalar(
        select(ProjectSubmission)
        .where(
            ProjectSubmission.project_id == project.id,
            ProjectSubmission.student_id == student_id,
        )
        .with_only_columns(ProjectSubmission.id)
    )

    assert count is not None

