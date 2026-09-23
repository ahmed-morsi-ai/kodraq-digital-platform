from __future__ import annotations

from app.crud.crud_user import user as crud_user
from app.models.enrollment import Enrollment
from app.models.final_project import ProjectReview, TrainingProject
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
        description="Final project review test track",
    )
    db_session.add(track)
    db_session.flush()
    return track


def _create_project(
    db_session,
    *,
    track_id: int,
    passing_score: int,
) -> TrainingProject:
    project = TrainingProject(
        track_id=track_id,
        title="Final Review Project",
        description="Project review test project.",
        passing_score=passing_score,
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
) -> int:
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

    return instructor.id


def _create_submitted_submission(
    db_session,
    *,
    project_id: int,
    student_id: int,
) -> ProjectSubmission:
    submission = ProjectSubmission(
        project_id=project_id,
        student_id=student_id,
        github_url="https://github.com/example/final-project",
        status="SUBMITTED",
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    return submission


def test_instructor_can_review_and_approve_submission(
    client,
    db_session,
):
    _student = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-student@example.com",
        full_name="Final Review Student",
    )
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-instructor@example.com",
        full_name="Final Review Instructor",
        role_name="instructor",
    )

    track = _create_track(
        db_session,
        name="Final Review Approved Track",
        slug="final-review-approved-track",
    )
    db_session.commit()

    student_id = _enroll_student(
        db_session,
        email="final-review-student@example.com",
        track_id=track.id,
    )
    instructor_id = _assign_instructor(
        db_session,
        email="final-review-instructor@example.com",
        track_id=track.id,
    )

    project = _create_project(
        db_session,
        track_id=track.id,
        passing_score=75,
    )
    submission = _create_submitted_submission(
        db_session,
        project_id=project.id,
        student_id=student_id,
    )

    response = client.post(
        f"/api/v1/final-projects/submissions/{submission.id}/reviews",
        headers=instructor,
        json={
            "score": 90,
            "feedback": "Excellent final project.",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["submission_id"] == submission.id
    assert body["reviewer_id"] == instructor_id
    assert body["score"] == 90
    assert body["feedback"] == "Excellent final project."

    db_session.expire_all()
    persisted = db_session.get(ProjectSubmission, submission.id)

    assert persisted is not None
    assert persisted.status == "APPROVED"


def test_low_score_transitions_submission_to_changes_required(
    client,
    db_session,
):
    _student = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-low-student@example.com",
        full_name="Final Review Low Student",
    )
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-low-instructor@example.com",
        full_name="Final Review Low Instructor",
        role_name="instructor",
    )

    track = _create_track(
        db_session,
        name="Final Review Changes Track",
        slug="final-review-changes-track",
    )
    db_session.commit()

    student_id = _enroll_student(
        db_session,
        email="final-review-low-student@example.com",
        track_id=track.id,
    )
    _assign_instructor(
        db_session,
        email="final-review-low-instructor@example.com",
        track_id=track.id,
    )

    project = _create_project(
        db_session,
        track_id=track.id,
        passing_score=80,
    )
    submission = _create_submitted_submission(
        db_session,
        project_id=project.id,
        student_id=student_id,
    )

    response = client.post(
        f"/api/v1/final-projects/submissions/{submission.id}/reviews",
        headers=instructor,
        json={
            "score": 65,
            "feedback": "Please address the required changes.",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    persisted = db_session.get(ProjectSubmission, submission.id)

    assert persisted is not None
    assert persisted.status == "CHANGES_REQUIRED"


def test_student_cannot_write_project_review(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-denied-student@example.com",
        full_name="Final Review Denied Student",
    )

    track = _create_track(
        db_session,
        name="Final Review Denied Track",
        slug="final-review-denied-track",
    )
    db_session.commit()

    student_id = _enroll_student(
        db_session,
        email="final-review-denied-student@example.com",
        track_id=track.id,
    )

    project = _create_project(
        db_session,
        track_id=track.id,
        passing_score=75,
    )
    submission = _create_submitted_submission(
        db_session,
        project_id=project.id,
        student_id=student_id,
    )

    response = client.post(
        f"/api/v1/final-projects/submissions/{submission.id}/reviews",
        headers=student,
        json={
            "score": 95,
            "feedback": "Student-created review.",
        },
    )

    assert response.status_code == 403


def test_student_can_view_own_reviews_and_outsider_is_denied(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-history-student@example.com",
        full_name="Final Review History Student",
    )
    _instructor = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-history-instructor@example.com",
        full_name="Final Review History Instructor",
        role_name="instructor",
    )
    other_student = _create_user_and_get_token(
        client,
        db_session,
        email="final-review-history-other@example.com",
        full_name="Final Review History Other",
    )

    track = _create_track(
        db_session,
        name="Final Review History Track",
        slug="final-review-history-track",
    )
    other_track = _create_track(
        db_session,
        name="Final Review History Other Track",
        slug="final-review-history-other-track",
    )
    db_session.commit()

    student_id = _enroll_student(
        db_session,
        email="final-review-history-student@example.com",
        track_id=track.id,
    )
    other_student_id = _enroll_student(
        db_session,
        email="final-review-history-other@example.com",
        track_id=other_track.id,
    )

    instructor_id = _assign_instructor(
        db_session,
        email="final-review-history-instructor@example.com",
        track_id=track.id,
    )

    project = _create_project(
        db_session,
        track_id=track.id,
        passing_score=75,
    )
    submission = _create_submitted_submission(
        db_session,
        project_id=project.id,
        student_id=student_id,
    )

    review = ProjectReview(
        submission_id=submission.id,
        reviewer_id=instructor_id,
        score=85,
        feedback="Good work.",
        status_decision="APPROVED",
    )
    submission.status = "APPROVED"

    other_project = _create_project(
        db_session,
        track_id=other_track.id,
        passing_score=75,
    )
    other_submission = _create_submitted_submission(
        db_session,
        project_id=other_project.id,
        student_id=other_student_id,
    )

    db_session.add(review)
    db_session.add(submission)
    db_session.add(other_submission)
    db_session.commit()

    student_response = client.get(
        f"/api/v1/final-projects/submissions/{submission.id}/reviews",
        headers=student,
    )
    outsider_response = client.get(
        f"/api/v1/final-projects/submissions/{submission.id}/reviews",
        headers=other_student,
    )

    assert student_response.status_code == 200
    assert len(student_response.json()) == 1
    assert student_response.json()[0]["score"] == 85

    assert outsider_response.status_code == 403
