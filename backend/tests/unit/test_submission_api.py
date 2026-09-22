from __future__ import annotations

from fastapi import status

from app.crud.crud_user import user as crud_user
from app.models.role import Role
from app.models.submission import (
    Submission,
    SubmissionFile,
    SubmissionReview,
    SubmissionStatus,
)
from app.models.track_instructor import TrackInstructor
from app.schemas.user import UserCreate


def create_user_and_get_token(
    client,
    db_session,
    *,
    email: str,
    password: str,
    full_name: str,
    is_superuser: bool = False,
    role_name: str | None = None,
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
            is_superuser=is_superuser,
            role_id=role_id,
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


def create_track(client, admin_headers, *, name: str, slug: str) -> int:
    response = client.post(
        "/api/v1/tracks",
        headers=admin_headers,
        json={
            "name": name,
            "slug": slug,
            "description": f"{name} description",
            "ordering": 1,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def create_assignment(client, admin_headers, *, track_id: int) -> int:
    response = client.post(
        "/api/v1/assignments",
        headers=admin_headers,
        json={
            "track_id": track_id,
            "title": f"Assignment {track_id}",
            "description": "Assignment description",
            "instructions": "Complete the assignment.",
            "difficulty": "beginner",
            "ordering": 1,
            "is_mandatory": True,
            "is_active": True,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def create_submission(client, headers, assignment_id: int, *, content: str):
    response = client.post(
        "/api/v1/submissions",
        headers=headers,
        json={
            "assignment_id": assignment_id,
            "content": content,
            "github_url": "https://github.com/example/submission",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response


def test_admin_review_creates_log_and_transitions_submission(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task526-review-student@example.com",
        password="Password123!",
        full_name="Review Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task526-review-admin@example.com",
        password="AdminPassword123!",
        full_name="Review Admin",
        is_superuser=True,
    )
    track_id = create_track(
        client,
        admin,
        name="Review Track",
        slug="review-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)
    submission = create_submission(
        client,
        student,
        assignment_id,
        content="Review me",
    ).json()
    db_submission = db_session.get(Submission, submission["id"])
    assert db_submission is not None
    db_submission.status = SubmissionStatus.SUBMITTED.value
    db_session.commit()

    response = client.post(
        f"/api/v1/submissions/{db_submission.id}/reviews",
        headers=admin,
        json={
            "feedback": "Strong implementation",
            "score": 95,
            "resulting_status": "APPROVED",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "APPROVED"
    review = (
        db_session.query(SubmissionReview)
        .filter(SubmissionReview.submission_id == db_submission.id)
        .one()
    )
    admin_model = crud_user.get_by_email(
        db_session,
        email="task526-review-admin@example.com",
    )
    assert admin_model is not None
    assert review.reviewer_id == admin_model.id
    assert review.feedback == "Strong implementation"
    assert review.score == 95


def test_student_cannot_create_submission_review(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task526-student-reviewer@example.com",
        password="Password123!",
        full_name="Student Reviewer",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task526-student-reviewer-admin@example.com",
        password="AdminPassword123!",
        full_name="Student Review Admin",
        is_superuser=True,
    )
    track_id = create_track(
        client,
        admin,
        name="Student Review Track",
        slug="student-review-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)
    submission = create_submission(
        client,
        student,
        assignment_id,
        content="Student review denial",
    ).json()
    db_submission = db_session.get(Submission, submission["id"])
    assert db_submission is not None
    db_submission.status = SubmissionStatus.SUBMITTED.value
    db_session.commit()

    response = client.post(
        f"/api/v1/submissions/{db_submission.id}/reviews",
        headers=student,
        json={
            "feedback": "Should be denied",
            "resulting_status": "CHANGES_REQUIRED",
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_instructor_cannot_review_submission_outside_assigned_track(
    client,
    db_session,
):
    instructor = create_user_and_get_token(
        client,
        db_session,
        email="task526-scoped-instructor@example.com",
        password="InstructorPassword123!",
        full_name="Scoped Instructor",
        role_name="instructor",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task526-scoped-admin@example.com",
        password="AdminPassword123!",
        full_name="Scoped Admin",
        is_superuser=True,
    )
    student = create_user_and_get_token(
        client,
        db_session,
        email="task526-scoped-student@example.com",
        password="Password123!",
        full_name="Scoped Student",
    )
    allowed_track_id = create_track(
        client,
        admin,
        name="Allowed Review Track",
        slug="allowed-review-track",
    )
    denied_track_id = create_track(
        client,
        admin,
        name="Denied Review Track",
        slug="denied-review-track",
    )
    denied_assignment_id = create_assignment(
        client,
        admin,
        track_id=denied_track_id,
    )
    instructor_model = crud_user.get_by_email(
        db_session,
        email="task526-scoped-instructor@example.com",
    )
    assert instructor_model is not None
    db_session.add(
        TrackInstructor(
            track_id=allowed_track_id,
            instructor_id=instructor_model.id,
        )
    )
    db_session.commit()

    denied_submission = create_submission(
        client,
        student,
        denied_assignment_id,
        content="Out of scope",
    ).json()
    db_submission = db_session.get(Submission, denied_submission["id"])
    assert db_submission is not None
    db_submission.status = SubmissionStatus.SUBMITTED.value
    db_session.commit()

    response = client.post(
        f"/api/v1/submissions/{db_submission.id}/reviews",
        headers=instructor,
        json={
            "feedback": "Out of scope review",
            "resulting_status": "CHANGES_REQUIRED",
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_draft_submission_cannot_be_reviewed(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task526-draft-student@example.com",
        password="Password123!",
        full_name="Draft Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task526-draft-admin@example.com",
        password="AdminPassword123!",
        full_name="Draft Admin",
        is_superuser=True,
    )
    track_id = create_track(
        client,
        admin,
        name="Draft Review Track",
        slug="draft-review-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)
    submission = create_submission(
        client,
        student,
        assignment_id,
        content="Still draft",
    ).json()

    response = client.post(
        f"/api/v1/submissions/{submission['id']}/reviews",
        headers=admin,
        json={
            "feedback": "Cannot review yet",
            "resulting_status": "APPROVED",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_submission_detail_includes_files_and_reviews(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task525-detail-student@example.com",
        password="Password123!",
        full_name="Detail Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task525-detail-admin@example.com",
        password="AdminPassword123!",
        full_name="Detail Admin",
        is_superuser=True,
    )
    track_id = create_track(
        client,
        admin,
        name="History Track",
        slug="history-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)
    submission = create_submission(
        client,
        student,
        assignment_id,
        content="History content",
    ).json()

    db_submission = db_session.get(Submission, submission["id"])
    assert db_submission is not None
    db_session.add(
        SubmissionFile(
            submission_id=db_submission.id,
            file_name="solution.py",
            file_path="submissions/solution.py",
            file_size=128,
            content_type="text/x-python",
        )
    )
    db_session.add(
        SubmissionReview(
            submission_id=db_submission.id,
            feedback="Good work",
            score=92,
            resulting_status="APPROVED",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/submissions/{db_submission.id}",
        headers=student,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == db_submission.id
    assert body["content"] == "History content"
    assert body["github_url"] == "https://github.com/example/submission"
    assert body["files"][0]["file_name"] == "solution.py"
    assert body["files"][0]["file_size_bytes"] == 128
    assert body["reviews"][0]["feedback"] == "Good work"
    assert body["reviews"][0]["score"] == 92
    assert body["reviews"][0]["resulting_state"] == "APPROVED"
    assert body["reviews"][0]["reviewed_at"]


def test_submission_owner_is_derived_from_jwt_and_me_isolated(
    client,
    db_session,
):
    student_a = create_user_and_get_token(
        client,
        db_session,
        email="task522-student-a@example.com",
        password="Password123!",
        full_name="Student A",
    )
    student_b = create_user_and_get_token(
        client,
        db_session,
        email="task522-student-b@example.com",
        password="Password123!",
        full_name="Student B",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task522-admin-a@example.com",
        password="AdminPassword123!",
        full_name="Admin",
        is_superuser=True,
    )

    track_id = create_track(
        client,
        admin,
        name="Task 5.2.2 Track A",
        slug="task-5-2-2-track-a",
    )
    assignment_id = create_assignment(
        client,
        admin,
        track_id=track_id,
    )

    first = create_submission(
        client,
        student_a,
        assignment_id,
        content="Student A work",
    )
    second = create_submission(
        client,
        student_b,
        assignment_id,
        content="Student B work",
    )

    assert first.json()["user_id"] != second.json()["user_id"]

    mine = client.get(
        "/api/v1/submissions/me",
        headers=student_a,
    )
    assert mine.status_code == status.HTTP_200_OK
    assert [item["id"] for item in mine.json()] == [first.json()["id"]]
    assert first.json()["github_url"] == "https://github.com/example/submission"


def test_submission_rejects_non_github_url(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task524-invalid-create@example.com",
        password="Password123!",
        full_name="Invalid Create Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task524-invalid-create-admin@example.com",
        password="AdminPassword123!",
        full_name="Invalid Create Admin",
        is_superuser=True,
    )
    track_id = create_track(
        client,
        admin,
        name="Invalid URL Track",
        slug="invalid-url-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)

    response = client.post(
        "/api/v1/submissions",
        headers=student,
        json={
            "assignment_id": assignment_id,
            "content": "Invalid URL submission",
            "github_url": "https://gitlab.com/example/submission",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_submission_rejects_invalid_github_url_on_update(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task524-invalid-update@example.com",
        password="Password123!",
        full_name="Invalid Update Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task524-invalid-update-admin@example.com",
        password="AdminPassword123!",
        full_name="Invalid Update Admin",
        is_superuser=True,
    )
    track_id = create_track(
        client,
        admin,
        name="Invalid Update URL Track",
        slug="invalid-update-url-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)
    submission = create_submission(
        client,
        student,
        assignment_id,
        content="Valid submission",
    ).json()

    response = client.patch(
        f"/api/v1/submissions/{submission['id']}",
        headers=student,
        json={"github_url": "https://bitbucket.org/example/submission"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_student_cannot_read_or_update_another_student_submission(
    client,
    db_session,
):
    student_a = create_user_and_get_token(
        client,
        db_session,
        email="task522-owner@example.com",
        password="Password123!",
        full_name="Owner",
    )
    student_b = create_user_and_get_token(
        client,
        db_session,
        email="task522-attacker@example.com",
        password="Password123!",
        full_name="Other Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task522-admin-owner@example.com",
        password="AdminPassword123!",
        full_name="Admin",
        is_superuser=True,
    )

    track_id = create_track(
        client,
        admin,
        name="Task 5.2.2 RBAC Track",
        slug="task-5-2-2-rbac-track",
    )
    assignment_id = create_assignment(
        client,
        admin,
        track_id=track_id,
    )

    submission = create_submission(
        client,
        student_a,
        assignment_id,
        content="Private work",
    ).json()

    read_other = client.get(
        f"/api/v1/submissions/{submission['id']}",
        headers=student_b,
    )
    assert read_other.status_code == status.HTTP_403_FORBIDDEN

    detail_other = client.get(
        f"/api/v1/submissions/{submission['id']}",
        headers=student_b,
    )
    assert detail_other.status_code == status.HTTP_403_FORBIDDEN

    update_other = client.patch(
        f"/api/v1/submissions/{submission['id']}",
        headers=student_b,
        json={"content": "Tampered"},
    )
    assert update_other.status_code == status.HTTP_403_FORBIDDEN

    assignment_list = client.get(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=student_b,
    )
    assert assignment_list.status_code == status.HTTP_403_FORBIDDEN


def test_instructor_track_scoped_access(client, db_session):
    instructor = create_user_and_get_token(
        client,
        db_session,
        email="task522-instructor@example.com",
        password="InstructorPassword123!",
        full_name="Instructor",
        role_name="instructor",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task522-admin-instructor@example.com",
        password="AdminPassword123!",
        full_name="Admin",
        is_superuser=True,
    )
    student = create_user_and_get_token(
        client,
        db_session,
        email="task522-student-instructor@example.com",
        password="Password123!",
        full_name="Student",
    )

    allowed_track_id = create_track(
        client,
        admin,
        name="Instructor Allowed Track",
        slug="instructor-allowed-track",
    )
    denied_track_id = create_track(
        client,
        admin,
        name="Instructor Denied Track",
        slug="instructor-denied-track",
    )

    allowed_assignment_id = create_assignment(
        client,
        admin,
        track_id=allowed_track_id,
    )
    denied_assignment_id = create_assignment(
        client,
        admin,
        track_id=denied_track_id,
    )

    instructor_model = crud_user.get_by_email(
        db_session,
        email="task522-instructor@example.com",
    )
    assert instructor_model is not None

    db_session.add(
        TrackInstructor(
            track_id=allowed_track_id,
            instructor_id=instructor_model.id,
        )
    )
    db_session.commit()

    allowed_submission = create_submission(
        client,
        student,
        allowed_assignment_id,
        content="Allowed track submission",
    )
    denied_submission = create_submission(
        client,
        student,
        denied_assignment_id,
        content="Denied track submission",
    )
    allowed_submission_id = allowed_submission.json()["id"]
    denied_submission_id = denied_submission.json()["id"]

    allowed_response = client.get(
        f"/api/v1/assignments/{allowed_assignment_id}/submissions",
        headers=instructor,
    )
    assert allowed_response.status_code == status.HTTP_200_OK
    assert len(allowed_response.json()) == 1

    denied_response = client.get(
        f"/api/v1/assignments/{denied_assignment_id}/submissions",
        headers=instructor,
    )
    assert denied_response.status_code == status.HTTP_403_FORBIDDEN

    allowed_detail = client.get(
        f"/api/v1/submissions/{allowed_submission_id}",
        headers=instructor,
    )
    assert allowed_detail.status_code == status.HTTP_200_OK

    denied_detail = client.get(
        f"/api/v1/submissions/{denied_submission_id}",
        headers=instructor,
    )
    assert denied_detail.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_read_all_assignment_submissions(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task522-admin-student@example.com",
        password="Password123!",
        full_name="Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task522-admin-b@example.com",
        password="AdminPassword123!",
        full_name="Admin",
        is_superuser=True,
    )

    track_id = create_track(
        client,
        admin,
        name="Admin Submission Track",
        slug="admin-submission-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)

    create_submission(
        client,
        student,
        assignment_id,
        content="Admin-visible submission",
    )

    response = client.get(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=admin,
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


def test_submission_state_machine(client, db_session):
    student = create_user_and_get_token(
        client,
        db_session,
        email="task522-state-student@example.com",
        password="Password123!",
        full_name="State Student",
    )
    admin = create_user_and_get_token(
        client,
        db_session,
        email="task522-state-admin@example.com",
        password="AdminPassword123!",
        full_name="State Admin",
        is_superuser=True,
    )

    track_id = create_track(
        client,
        admin,
        name="State Machine Track",
        slug="state-machine-track",
    )
    assignment_id = create_assignment(client, admin, track_id=track_id)

    submission = create_submission(
        client,
        student,
        assignment_id,
        content="Draft content",
    ).json()

    draft_update = client.patch(
        f"/api/v1/submissions/{submission['id']}",
        headers=student,
        json={
            "content": "Updated draft",
            "github_url": "https://github.com/example/updated",
        },
    )
    assert draft_update.status_code == status.HTTP_200_OK
    assert draft_update.json()["status"] == "DRAFT"

    submit = client.patch(
        f"/api/v1/submissions/{submission['id']}",
        headers=student,
        json={"status": "SUBMITTED"},
    )
    assert submit.status_code == status.HTTP_200_OK
    assert submit.json()["status"] == "SUBMITTED"

    for locked_status in ("UNDER_REVIEW", "APPROVED", "REJECTED"):
        db_submission = db_session.get(Submission, submission["id"])
        assert db_submission is not None
        db_submission.status = locked_status
        db_session.commit()

        response = client.patch(
            f"/api/v1/submissions/{submission['id']}",
            headers=student,
            json={
                "github_url": (
                    "https://github.com/example/blocked-"
                    f"{locked_status.lower()}"
                )
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    db_submission = db_session.get(Submission, submission["id"])
    assert db_submission is not None
    db_submission.status = "CHANGES_REQUIRED"
    db_session.commit()

    resubmit = client.patch(
        f"/api/v1/submissions/{submission['id']}",
        headers=student,
        json={
            "content": "Reworked submission",
            "status": "SUBMITTED",
        },
    )
    assert resubmit.status_code == status.HTTP_200_OK
    assert resubmit.json()["status"] == "SUBMITTED"
