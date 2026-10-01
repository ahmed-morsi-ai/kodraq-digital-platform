from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.main import app
from app.models.submission import Submission
from tests.submission_helpers import headers, make_submission

URL = "/api/v1/submissions"


@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full"])
def test_student_creates_owned_draft_in_enrolled_track(
    client, db_session, submission_data, scope
):
    data = submission_data
    response = client.post(
        URL,
        headers=headers(data),
        json={"assignment_id": data.assignments[scope].id, "content": "My work"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == data.users["student"].id
    assert body["status"] == "DRAFT"
    assert body["grade"] is body["submitted_at"] is None
    assert (
        db_session.get(Submission, body["id"]).assignment_id
        == data.assignments[scope].id
    )


@pytest.mark.parametrize("scope", ["other", "unscoped", "inconsistent", "inactive"])
def test_creation_denies_inaccessible_assignments(
    client, db_session, submission_data, scope
):
    response = client.post(
        URL,
        headers=headers(submission_data),
        json={"assignment_id": submission_data.assignments[scope].id},
    )
    assert response.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(Submission)) == 0


@pytest.mark.parametrize(
    "enrollment_status", ["pending_payment", "cancelled", "completed"]
)
def test_inactive_enrollment_denies_writes_but_preserves_own_history(
    client, db_session, submission_data, enrollment_status
):
    data = submission_data
    submission = make_submission(db_session, data)
    data.enrollment.status = enrollment_status
    db_session.flush()
    assert (
        client.post(
            URL, headers=headers(data), json={"assignment_id": submission.assignment_id}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"{URL}/{submission.id}", headers=headers(data), json={"content": "Blocked"}
        ).status_code
        == 403
    )
    assert (
        client.get(f"{URL}/{submission.id}", headers=headers(data)).status_code == 200
    )


@pytest.mark.parametrize("role", ["instructor", "employee"])
def test_non_student_cannot_create_or_list_own_work(client, submission_data, role):
    data = submission_data
    assert (
        client.post(
            URL,
            headers=headers(data, role),
            json={"assignment_id": data.assignments["track"].id},
        ).status_code
        == 403
    )
    assert client.get(f"{URL}/me", headers=headers(data, role)).status_code == 403


@pytest.mark.parametrize("role", ["admin", "superuser"])
@pytest.mark.parametrize("scope", ["other", "unscoped", "inactive"])
def test_admin_has_global_create_and_update_access(
    client, db_session, submission_data, role, scope
):
    data = submission_data
    own = client.post(
        URL,
        headers=headers(data, role),
        json={"assignment_id": data.assignments[scope].id},
    )
    assert own.status_code == 201
    assert own.json()["user_id"] == data.users[role].id
    target = make_submission(db_session, data, scope=scope, state="APPROVED")
    response = client.patch(
        f"{URL}/{target.id}",
        headers=headers(data, role),
        json={"content": "Admin correction"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Admin correction"
    assert response.json()["user_id"] == data.users["student"].id
    assert response.json()["status"] == "APPROVED"


@pytest.mark.parametrize(
    "role,scope,expected",
    [
        ("instructor", "track", 200),
        ("instructor", "module", 200),
        ("instructor", "lesson", 200),
        ("instructor", "full", 200),
        ("instructor", "other", 403),
        ("instructor", "unscoped", 403),
        ("instructor", "inconsistent", 403),
        ("other", "track", 403),
        ("employee", "track", 403),
        ("admin", "other", 200),
        ("admin", "unscoped", 200),
        ("admin", "inconsistent", 200),
        ("superuser", "other", 200),
        ("student", "track", 403),
    ],
)
def test_grading_and_read_access_boundaries(
    client, db_session, submission_data, role, scope, expected
):
    data = submission_data
    submission = make_submission(db_session, data, scope=scope, state="SUBMITTED")
    auth = headers(data, role)
    detail = client.get(f"{URL}/{submission.id}", headers=auth)
    assert detail.status_code == (200 if role == "student" else expected)
    listing = client.get(
        f"/api/v1/assignments/{submission.assignment_id}/submissions", headers=auth
    )
    assert listing.status_code == expected
    response = client.post(
        f"{URL}/{submission.id}/review",
        headers=auth,
        json={
            "feedback_text": "Reviewed",
            "status_transition": "APPROVED",
            "grade": 90,
        },
    )
    assert response.status_code == expected
    db_session.refresh(submission)
    assert submission.status == ("APPROVED" if expected == 200 else "SUBMITTED")
    assert len(submission.reviews) == (1 if expected == 200 else 0)


@pytest.mark.parametrize("role", ["other", "instructor", "employee"])
def test_non_owner_cannot_edit_student_content(
    client, db_session, submission_data, role
):
    record = make_submission(db_session, submission_data)
    response = client.patch(
        f"{URL}/{record.id}",
        headers=headers(submission_data, role),
        json={"content": "Tampered"},
    )
    assert response.status_code == 403
    db_session.refresh(record)
    assert record.content == "Original work"


@pytest.mark.parametrize(
    "state",
    ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUIRED", "APPROVED", "REJECTED"],
)
@pytest.mark.parametrize(
    "target", ["UNDER_REVIEW", "CHANGES_REQUIRED", "APPROVED", "REJECTED"]
)
def test_review_transition_matrix(client, db_session, submission_data, state, target):
    data = submission_data
    record = make_submission(db_session, data, state=state)
    allowed = state == "SUBMITTED" or (
        state == "UNDER_REVIEW" and target != "UNDER_REVIEW"
    )
    response = client.post(
        f"{URL}/{record.id}/review",
        headers=headers(data, "instructor"),
        json={
            "feedback_text": "  Useful feedback  ",
            "status_transition": target,
            "grade": 87,
        },
    )
    assert response.status_code == (200 if allowed else 409)
    db_session.refresh(record)
    assert record.status == (target if allowed else state)
    assert record.grade == (87 if allowed else None)
    if allowed:
        detail = client.get(f"{URL}/{record.id}", headers=headers(data)).json()
        review = detail["reviews"][0]
        assert review["reviewer_id"] == data.users["instructor"].id
        assert review["feedback_text"] == "Useful feedback"
        assert review["status_transition"] == target
        assert review["grade"] == 87
        assert review["created_at"]
    else:
        assert record.reviews == []


@pytest.mark.parametrize(
    "state",
    ["DRAFT", "CHANGES_REQUIRED", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"],
)
def test_student_edit_and_resubmit_states(client, db_session, submission_data, state):
    data = submission_data
    record = make_submission(db_session, data, state=state)
    earlier = datetime(2020, 1, 1, tzinfo=UTC)
    record.submitted_at, record.grade = earlier, 40
    db_session.flush()
    response = client.patch(
        f"{URL}/{record.id}",
        headers=headers(data),
        json={"status": "SUBMITTED", "content": "Revised work"},
    )
    allowed = state in {"DRAFT", "CHANGES_REQUIRED"}
    assert response.status_code == (200 if allowed else 409)
    db_session.refresh(record)
    assert record.status == ("SUBMITTED" if allowed else state)
    assert record.content == ("Revised work" if allowed else "Original work")
    assert record.grade == (None if allowed else 40)
    assert (record.submitted_at > earlier) is allowed


def test_patch_preserves_omissions_and_clears_nullable_fields(
    client, db_session, submission_data
):
    record = make_submission(db_session, submission_data)
    response = client.patch(
        f"{URL}/{record.id}",
        headers=headers(submission_data),
        json={"github_url": None},
    )
    assert response.status_code == 200
    assert response.json()["github_url"] is None
    assert response.json()["content"] == "Original work"
    assert response.json()["status"] == "DRAFT"
    assert response.json()["submitted_at"] is None


@pytest.mark.parametrize(
    "method,extra",
    [
        ("post", {"user_id": 999}),
        ("post", {"grade": 100}),
        ("post", {"status": "APPROVED"}),
        ("post", {"submitted_at": "2026-01-01"}),
        ("patch", {"user_id": 999}),
        ("patch", {"assignment_id": 999}),
        ("patch", {"grade": 100}),
        ("patch", {"status": "DRAFT"}),
        ("patch", {"status": "APPROVED"}),
        ("patch", {"status": None}),
        ("patch", {"updated_at": "2026-01-01"}),
    ],
)
def test_submission_rejects_mass_assignment(
    client, db_session, submission_data, method, extra
):
    record = make_submission(db_session, submission_data)
    payload = (
        {"assignment_id": record.assignment_id, **extra} if method == "post" else extra
    )
    response = getattr(client, method)(
        URL if method == "post" else f"{URL}/{record.id}",
        headers=headers(submission_data),
        json=payload,
    )
    assert response.status_code == 422
    db_session.refresh(record)
    assert record.status == "DRAFT"
    assert record.grade is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"feedback_text": " ", "status_transition": "APPROVED"},
        {"feedback_text": "Review", "status_transition": "DRAFT"},
        {"feedback_text": "Review", "status_transition": "SUBMITTED"},
        {
            "feedback_text": "Review",
            "status_transition": "APPROVED",
            "reviewer_id": 999,
        },
        {"feedback_text": "Review", "status_transition": "APPROVED", "grade": True},
        {"feedback_text": "Review", "status_transition": "APPROVED", "grade": 1.5},
        {"feedback_text": "Review", "status_transition": "APPROVED", "grade": 2**31},
        {"status": "APPROVED"},
    ],
)
def test_review_validation_cannot_change_state(
    client, db_session, submission_data, payload
):
    record = make_submission(db_session, submission_data, state="SUBMITTED")
    response = client.post(
        f"{URL}/{record.id}/review",
        headers=headers(submission_data, "admin"),
        json=payload,
    )
    assert response.status_code == 422
    db_session.refresh(record)
    assert record.status == "SUBMITTED"
    assert record.reviews == []


def test_full_review_revision_resubmission_cycle(client, db_session, submission_data):
    data = submission_data
    record = make_submission(db_session, data)
    student, instructor = headers(data), headers(data, "instructor")
    assert (
        client.patch(
            f"{URL}/{record.id}", headers=student, json={"status": "SUBMITTED"}
        ).status_code
        == 200
    )
    for target in ("UNDER_REVIEW", "CHANGES_REQUIRED"):
        response = client.post(
            f"{URL}/{record.id}/review",
            headers=instructor,
            json={"feedback_text": target, "status_transition": target, "grade": 50},
        )
        assert response.status_code == 200
    resubmitted = client.patch(
        f"{URL}/{record.id}",
        headers=student,
        json={"status": "SUBMITTED", "content": "Fixed"},
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["grade"] is None
    reviewed = client.post(
        f"{URL}/{record.id}/review",
        headers=instructor,
        json={
            "feedback_text": "Approved",
            "status_transition": "APPROVED",
            "grade": 95,
        },
    )
    assert reviewed.status_code == 200
    detail = client.get(f"{URL}/{record.id}", headers=student).json()
    assert detail["grade"] == 95
    assert len(detail["reviews"]) == 3
    assert sorted(review["grade"] for review in detail["reviews"]) == [50, 50, 95]


def test_list_pagination_is_scoped_and_stable(client, db_session, submission_data):
    data = submission_data
    records = [make_submission(db_session, data) for _ in range(3)]
    make_submission(db_session, data, owner="other")
    make_submission(db_session, data, scope="other", owner="other")
    mine = client.get(f"{URL}/me?skip=1&limit=1", headers=headers(data))
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()] == [records[1].id]
    assigned = client.get(
        f"/api/v1/assignments/{records[0].assignment_id}/submissions?skip=1&limit=1",
        headers=headers(data, "instructor"),
    )
    assert assigned.status_code == 200
    assert [item["id"] for item in assigned.json()] == [records[2].id]
    assert client.get(f"{URL}/me?limit=0", headers=headers(data)).json() == []


@pytest.mark.parametrize("query", ["skip=-1", "limit=-1", "skip=nope", "limit=nope"])
def test_pagination_validation(client, submission_data, query):
    data = submission_data
    assert client.get(f"{URL}/me?{query}", headers=headers(data)).status_code == 422
    assert (
        client.get(
            f"/api/v1/assignments/{data.assignments['track'].id}/submissions?{query}",
            headers=headers(data, "admin"),
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", URL, {"assignment_id": 999999}),
        ("get", f"{URL}/999999", None),
        ("patch", f"{URL}/999999", {"content": "Missing"}),
        (
            "post",
            f"{URL}/999999/review",
            {"feedback_text": "Missing", "status_transition": "APPROVED"},
        ),
        ("get", "/api/v1/assignments/999999/submissions", None),
    ],
)
def test_missing_records(client, submission_data, method, path, body):
    response = client.request(
        method, path, headers=headers(submission_data, "admin"), json=body
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", URL, {"assignment_id": 1}),
        ("get", f"{URL}/me", None),
        ("get", f"{URL}/1", None),
        ("patch", f"{URL}/1", {"content": "Blocked"}),
        (
            "post",
            f"{URL}/1/review",
            {"feedback_text": "Blocked", "status_transition": "APPROVED"},
        ),
        ("get", "/api/v1/assignments/1/submissions", None),
    ],
)
def test_authentication_and_inactive_users(client, submission_data, method, path, body):
    assert client.request(method, path, json=body).status_code == 401
    assert (
        client.request(
            method, path, headers=headers(submission_data, "inactive"), json=body
        ).status_code
        == 400
    )


def test_only_canonical_review_route_is_registered(client):
    paths = app.openapi()["paths"]
    assert f"{URL}/{{submission_id}}/review" in paths
    assert f"{URL}/{{submission_id}}/reviews" not in paths
    assert client.post(f"{URL}/1/reviews", json={}).status_code == 404


@pytest.mark.parametrize(
    "fields",
    [
        {"github_url": "https://github.com/" + "x" * 513},
        {"github_url": "https://github.com/" + "\u00e9" * 100},
        {"github_url": "https://github.com.evil.example/owner/work"},
        {"file_path_or_url": "x" * 1025},
    ],
)
def test_submission_url_validation_matches_storage_limits(
    client, db_session, submission_data, fields
):
    data = submission_data
    created = client.post(
        URL,
        headers=headers(data),
        json={"assignment_id": data.assignments["track"].id, **fields},
    )
    assert created.status_code == 422
    record = make_submission(db_session, data)
    updated = client.patch(f"{URL}/{record.id}", headers=headers(data), json=fields)
    assert updated.status_code == 422
    db_session.refresh(record)
    assert record.github_url == "https://github.com/student/work"
