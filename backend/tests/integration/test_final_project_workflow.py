from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.crud.crud_final_project import training_project as projects
from app.crud.crud_project_submission import project_submission as submissions
from app.models.enrollment import Enrollment
from app.models.final_project import ProjectRequirement, ProjectReview, TrainingProject
from app.models.project_submission import ProjectSubmission
from app.models.role import Role
from app.models.track import Track
from app.models.user import User
from app.schemas.final_project import (
    ProjectSubmissionCreate,
    ProjectSubmissionUpdate,
    ProjectReviewCreate,
    TrainingProjectCreate,
)
from tests.final_project_helpers import seed_final_projects, headers


@pytest.fixture
def data(db_session):
    return seed_final_projects(db_session)


def create(client, data, *, name="student", project=None, payload=None):
    return client.post(
        f"/api/v1/final-projects/{project or data.project.id}/submissions",
        headers=headers(data.users[name]),
        json=payload
        if payload is not None
        else {"github_url": "https://github.com/owner/capstone"},
    )


def submitted(client, data):
    response = create(client, data)
    assert response.status_code == 201, response.text
    record_id = response.json()["id"]
    response = patch(client, data, record_id, {"status": "SUBMITTED"})
    assert response.status_code == 200, response.text
    return record_id


def patch(client, data, record_id, payload, name="student"):
    return client.patch(
        f"/api/v1/final-projects/submissions/{record_id}",
        headers=headers(data.users[name]),
        json=payload,
    )


def review(client, data, record_id, payload=None, name="instructor"):
    return client.post(
        f"/api/v1/final-projects/submissions/{record_id}/reviews",
        headers=headers(data.users[name]),
        json=payload if payload is not None else {"score": 90, "feedback": "Good work"},
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        ("admin", 201),
        ("superuser", 201),
        ("instructor", 201),
        ("foreign", 403),
        ("student", 403),
        ("employee", 403),
    ],
)
def test_create_project_requires_assigned_manager(client, data, name, expected):
    response = client.post(
        f"/api/v1/tracks/{data.tracks[2].id}/final-project",
        headers=headers(data.users[name]),
        json={
            "title": " New project ",
            "requirements": [{"description": " Tests ", "order": 0}],
        },
    )
    assert response.status_code == expected, response.text
    if expected == 201:
        assert response.json()["title"] == "New project"
        assert response.json()["requirements"][0]["description"] == "Tests"
        assert response.json()["passing_score"] == 75
        assert (
            client.post(
                f"/api/v1/tracks/{data.tracks[2].id}/final-project",
                headers=headers(data.users[name]),
                json={"title": "Duplicate"},
            ).status_code
            == 409
        )


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
@pytest.mark.parametrize("name", ["foreign", "outsider", "employee"])
def test_project_track_isolation(client, data, method, name):
    kwargs = {"json": {"title": "Forbidden"}} if method == "patch" else {}
    response = getattr(client, method)(
        f"/api/v1/final-projects/{data.project.id}",
        headers=headers(data.users[name]),
        **kwargs,
    )
    assert response.status_code == 403


def test_partial_update_requirements_order_and_removal(client, db_session, data):
    path = f"/api/v1/final-projects/{data.project.id}"
    initial = client.get(path, headers=headers(data.users["student"])).json()
    assert [row["description"] for row in initial["requirements"]] == [
        "First",
        "Same order",
        "Later",
    ]
    response = client.patch(
        path, headers=headers(data.users["instructor"]), json={"description": None}
    )
    assert response.status_code == 200
    assert response.json()["requirements"] == initial["requirements"]
    response = client.patch(
        path,
        headers=headers(data.users["instructor"]),
        json={"requirements": [{"description": "New", "order": 1}]},
    )
    assert response.status_code == 200
    old_ids = [row["id"] for row in initial["requirements"]]
    assert not db_session.scalars(
        select(ProjectRequirement).where(ProjectRequirement.id.in_(old_ids))
    ).all()
    response = client.patch(
        path, headers=headers(data.users["admin"]), json={"requirements": []}
    )
    assert response.json()["requirements"] == []


@pytest.mark.parametrize(
    "name", ["instructor", "admin", "superuser", "foreign", "employee", "outsider"]
)
def test_only_enrolled_students_can_create_work(client, data, name):
    assert create(client, data, name=name).status_code == 403


@pytest.mark.parametrize("change", ["withdraw", "inactive_project"])
def test_access_rechecked_on_update_and_resubmit(client, db_session, data, change):
    record = create(client, data).json()
    if change == "withdraw":
        db_session.scalar(
            select(Enrollment).where(Enrollment.user_id == data.users["student"].id)
        ).status = "cancelled"
    else:
        data.project.is_active = False
    db_session.commit()
    expected = 403 if change == "withdraw" else 404
    assert create(client, data).status_code == expected
    assert (
        patch(client, data, record["id"], {"status": "SUBMITTED"}).status_code
        == expected
    )
    assert (
        patch(client, data, record["id"], {"student_notes": "change"}).status_code
        == expected
    )
    # Student keeps historical access to their own work and feedback.
    assert (
        client.get(
            f"/api/v1/final-projects/submissions/{record['id']}",
            headers=headers(data.users["student"]),
        ).status_code
        == 200
    )


@pytest.mark.parametrize("name", ["other", "outsider", "foreign", "employee"])
@pytest.mark.parametrize("action", ["read", "reviews", "update", "review"])
def test_submission_rbac_boundaries(client, data, name, action):
    record_id = submitted(client, data)
    path = f"/api/v1/final-projects/submissions/{record_id}"
    if action == "update":
        response = patch(client, data, record_id, {"student_notes": "tamper"}, name)
    elif action == "review":
        response = review(client, data, record_id, name=name)
    else:
        response = client.get(
            path + ("/reviews" if action == "reviews" else ""),
            headers=headers(data.users[name]),
        )
    assert response.status_code == 403


@pytest.mark.parametrize("name", ["admin", "superuser", "instructor"])
def test_managers_can_grade_and_list_own_tracks(client, data, name):
    record_id = submitted(client, data)
    response = review(client, data, record_id, name=name)
    assert response.status_code == 201, response.text
    assert response.json()["status_decision"] == "APPROVED"
    listing = client.get(
        f"/api/v1/final-projects/{data.project.id}/submissions",
        headers=headers(data.users[name]),
    )
    assert listing.status_code == 200 and listing.json()[0]["id"] == record_id
    assert listing.json()[0]["reviews"][0]["score"] == 90
    foreign = client.get(
        f"/api/v1/final-projects/{data.foreign_project.id}/submissions",
        headers=headers(data.users[name]),
    )
    assert foreign.status_code == (403 if name == "instructor" else 200)


def test_student_cannot_review_own_work_and_promoted_owner_cannot_self_grade(
    client, db_session, data
):
    record_id = submitted(client, data)
    assert review(client, data, record_id, name="student").status_code == 403
    data.users["student"].is_superuser = True
    db_session.commit()
    assert review(client, data, record_id, name="student").status_code == 403


def test_draft_submit_revision_resubmit_approval_history(client, db_session, data):
    record = create(client, data, payload={}).json()
    record_id = record["id"]
    assert record["status"] == "DRAFT" and record["submitted_at"] is None
    empty = patch(
        client,
        data,
        record_id,
        {"status": "SUBMITTED", "student_notes": "not evidence"},
    )
    assert empty.status_code == 400
    assert db_session.get(ProjectSubmission, record_id).student_notes is None
    first = patch(
        client,
        data,
        record_id,
        {"status": "SUBMITTED", "file_url": "https://example.com/work.zip"},
    )
    assert first.status_code == 200
    claimed = review(
        client,
        data,
        record_id,
        {"status_decision": "UNDER_REVIEW", "feedback": "Review started"},
    )
    assert claimed.status_code == 201 and claimed.json()["score"] is None
    assert (
        review(
            client,
            data,
            record_id,
            {"status_decision": "UNDER_REVIEW", "feedback": "Again"},
        ).status_code
        == 400
    )
    revision = review(client, data, record_id, {"score": 60, "feedback": "Add tests"})
    assert revision.json()["status_decision"] == "CHANGES_REQUIRED"
    assert review(client, data, record_id).status_code == 400
    draft = patch(
        client,
        data,
        record_id,
        {
            "student_notes": "Tests added",
            "file_url": None,
            "github_url": "https://github.com/owner/final/",
        },
    )
    assert draft.status_code == 200 and draft.json()["status"] == "CHANGES_REQUIRED"
    assert draft.json()["submitted_at"] == first.json()["submitted_at"]
    second = patch(client, data, record_id, {"status": "SUBMITTED"})
    assert (
        second.status_code == 200
        and second.json()["submitted_at"] >= first.json()["submitted_at"]
    )
    assert second.json()["github_url"] == "https://github.com/owner/final"
    assert (
        review(
            client, data, record_id, {"score": 75, "feedback": "Meets threshold"}
        ).status_code
        == 201
    )
    history = client.get(
        f"/api/v1/final-projects/submissions/{record_id}/reviews",
        headers=headers(data.users["student"]),
    ).json()
    assert [row["status_decision"] for row in history] == [
        "UNDER_REVIEW",
        "CHANGES_REQUIRED",
        "APPROVED",
    ]
    assert [row["feedback"] for row in history] == [
        "Review started",
        "Add tests",
        "Meets threshold",
    ]
    assert patch(client, data, record_id, {"status": "SUBMITTED"}).status_code == 403


@pytest.mark.parametrize("state", ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"])
def test_students_cannot_edit_locked_states(client, db_session, data, state):
    record_id = submitted(client, data)
    db_session.get(ProjectSubmission, record_id).status = state
    db_session.commit()
    assert (
        patch(client, data, record_id, {"student_notes": "not allowed"}).status_code
        == 403
    )


@pytest.mark.parametrize("state", ["DRAFT", "CHANGES_REQUIRED", "APPROVED", "REJECTED"])
def test_review_requires_waiting_for_review(client, db_session, data, state):
    record_id = create(client, data).json()["id"]
    db_session.get(ProjectSubmission, record_id).status = state
    db_session.commit()
    assert review(client, data, record_id).status_code == 400
    assert db_session.get(ProjectSubmission, record_id).reviews == []


@pytest.mark.parametrize(
    "decision,score,expected",
    [
        ("APPROVED", 74, 400),
        ("APPROVED", 75, 201),
        ("CHANGES_REQUIRED", 90, 201),
        ("REJECTED", None, 201),
    ],
)
def test_explicit_review_decisions_and_threshold(
    client, data, decision, score, expected
):
    record_id = submitted(client, data)
    response = review(
        client,
        data,
        record_id,
        {"score": score, "feedback": "Decision details", "status_decision": decision},
    )
    assert response.status_code == expected, response.text
    if expected == 201:
        assert response.json()["status_decision"] == decision


@pytest.mark.parametrize(
    "payload",
    [
        {"title": " "},
        {"title": "x" * 256},
        {"passing_score": -1},
        {"passing_score": 101},
        {"passing_score": True},
        {"passing_score": 75.5},
        {"passing_score": "75"},
        {"is_active": 1},
        {"title": None},
        {"passing_score": None},
        {"is_active": None},
        {"requirements": None},
        {"track_id": 123},
        {"requirements": [{"description": " "}]},
        {"requirements": [{"description": "valid", "order": -1}]},
        {"requirements": [{"description": "valid", "order": False}]},
        {"requirements": [{"description": "valid", "is_mandatory": "true"}]},
    ],
)
def test_project_http_validation(client, db_session, data, payload):
    response = client.patch(
        f"/api/v1/final-projects/{data.project.id}",
        headers=headers(data.users["admin"]),
        json=payload,
    )
    assert response.status_code == 422
    db_session.refresh(data.project)
    assert data.project.title == "Project 0"


@pytest.mark.parametrize(
    "payload",
    [
        {"score": -1, "feedback": "x"},
        {"score": 101, "feedback": "x"},
        {"score": True, "feedback": "x"},
        {"score": 90.5, "feedback": "x"},
        {"score": "90", "feedback": "x"},
        {"score": 90, "feedback": " "},
        {"feedback": "x"},
        {"score": None, "feedback": "x", "status_decision": "APPROVED"},
        {"score": 90, "feedback": "x", "reviewer_id": 1},
        {"score": 90, "feedback": "x", "status_decision": "DRAFT"},
        {"score": 90, "feedback": "x", "rubric_scores": {"all": 100}},
    ],
)
def test_review_http_validation(client, data, payload):
    record_id = submitted(client, data)
    assert review(client, data, record_id, payload).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"student_id": 1},
        {"project_id": 1},
        {"score": 100},
        {"status": "APPROVED"},
        {"status": None},
        {"github_url": "https://github.com.evil/user/repo"},
        {"github_url": "https://github.com/user"},
        {"live_url": "javascript:alert(1)"},
        {"file_url": "file:///secret"},
        {"live_url": "https://user:password@example.com"},
        {"file_url": "https://example.com/white space"},
        {"file_url": "https://example.com:999999/"},
        {"file_url": "x" * 513},
    ],
)
def test_submission_http_validation(client, data, payload):
    record_id = create(client, data).json()["id"]
    assert patch(client, data, record_id, payload).status_code == 422


def test_listing_filters_before_stable_pagination(client, data):
    own = create(client, data).json()["id"]
    another = create(client, data, name="other").json()["id"]
    mine = client.get(
        "/api/v1/final-projects/submissions/me?limit=1",
        headers=headers(data.users["student"]),
    )
    assert [item["id"] for item in mine.json()] == [own]
    assert (
        client.get(
            "/api/v1/final-projects/submissions/me?skip=1",
            headers=headers(data.users["student"]),
        ).json()
        == []
    )
    assert (
        client.get(
            f"/api/v1/final-projects/submissions/me?project_id={data.foreign_project.id}",
            headers=headers(data.users["student"]),
        ).json()
        == []
    )
    listed = client.get(
        f"/api/v1/final-projects/{data.project.id}/submissions?limit=1",
        headers=headers(data.users["instructor"]),
    )
    assert [item["id"] for item in listed.json()] == [another]
    assert create(client, data).status_code == 409


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101", "project_id=0"])
def test_invalid_pagination(client, data, query):
    assert (
        client.get(
            f"/api/v1/final-projects/submissions/me?{query}",
            headers=headers(data.users["student"]),
        ).status_code
        == 422
    )


def test_legacy_routes_are_absent(client, data):
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/final-projects/submissions/{submission_id}/review" not in paths
    assert "post" not in paths.get("/api/v1/final-projects/submissions", {})
    record_id = submitted(client, data)
    assert (
        client.post(
            f"/api/v1/final-projects/submissions/{record_id}/review",
            headers=headers(data.users["foreign"]),
            json={"status_decision": "APPROVED"},
        ).status_code
        == 404
    )


def test_legacy_nullable_review_data_serializes(client, db_session, data):
    record_id = submitted(client, data)
    db_session.add(
        ProjectReview(
            submission_id=record_id,
            reviewer_id=data.users["instructor"].id,
            score=None,
            feedback=None,
            rubric_scores={"legacy": 85},
            status_decision="CHANGES_REQUIRED",
        )
    )
    db_session.commit()
    response = client.get(
        f"/api/v1/final-projects/submissions/{record_id}/reviews",
        headers=headers(data.users["student"]),
    )
    assert response.status_code == 200 and response.json()[0]["score"] is None


@pytest.mark.parametrize("target", ["project", "submission", "reviews"])
def test_missing_records(client, data, target):
    path = {
        "project": "/api/v1/final-projects/999999",
        "submission": "/api/v1/final-projects/submissions/999999",
        "reviews": "/api/v1/final-projects/submissions/999999/reviews",
    }[target]
    assert client.get(path, headers=headers(data.users["admin"])).status_code == 404


@pytest.mark.parametrize("operation", ["create", "update", "review"])
def test_persistence_failures_rollback_whole_operation(
    db_session, data, monkeypatch, operation
):
    record = submissions.create(
        db_session,
        project_id=data.project.id,
        actor=data.users["student"],
        obj_in=ProjectSubmissionCreate(github_url="https://github.com/owner/repo"),
    )
    if operation == "review":
        record = submissions.update(
            db_session,
            submission_id=record.id,
            actor=data.users["student"],
            obj_in=ProjectSubmissionUpdate(status="SUBMITTED"),
        )
    record_id = record.id
    with Session(
        bind=db_session.connection(), join_transaction_mode="create_savepoint"
    ) as isolated:
        student = isolated.get(User, data.users["student"].id)
        manager = isolated.get(User, data.users["admin"].id)

        def fail():
            isolated.flush()
            raise RuntimeError("Persistence failure")

        monkeypatch.setattr(isolated, "commit", fail)
        with pytest.raises(RuntimeError, match="Persistence failure"):
            if operation == "create":
                projects.create(
                    isolated,
                    track_id=data.tracks[2].id,
                    actor=manager,
                    obj_in=TrainingProjectCreate(
                        title="Atomic", requirements=[{"description": "Required"}]
                    ),
                )
            elif operation == "update":
                submissions.update(
                    isolated,
                    submission_id=record_id,
                    actor=student,
                    obj_in=ProjectSubmissionUpdate(
                        student_notes="Should roll back", status="SUBMITTED"
                    ),
                )
            else:
                submissions.create_review(
                    isolated,
                    submission_id=record_id,
                    actor=manager,
                    obj_in=ProjectReviewCreate(score=99, feedback="Should roll back"),
                )
    db_session.expire_all()
    record = db_session.get(ProjectSubmission, record_id)
    assert record.student_notes is None and record.reviews == []
    assert record.status == ("SUBMITTED" if operation == "review" else "DRAFT")
    assert (
        db_session.scalar(
            select(TrainingProject.id).where(
                TrainingProject.track_id == data.tracks[2].id
            )
        )
        is None
    )


@pytest.mark.parametrize("operation", ["project", "submission", "review", "resubmit"])
def test_concurrent_writes_cannot_duplicate_or_override_decisions(
    test_engine, operation
):
    with Session(test_engine) as db:
        old_role_ids = set(db.scalars(select(Role.id)))
        data = seed_final_projects(db)
        created_role_ids = set(db.scalars(select(Role.id))) - old_role_ids
        user_ids, track_ids = (
            [u.id for u in data.users.values()],
            [t.id for t in data.tracks],
        )
        student_id, manager_id, project_id, empty_track = (
            data.users["student"].id,
            data.users["admin"].id,
            data.project.id,
            data.tracks[2].id,
        )
        record_id = None
        if operation in {"review", "resubmit"}:
            record = submissions.create(
                db,
                project_id=project_id,
                actor=data.users["student"],
                obj_in=ProjectSubmissionCreate(file_url="https://example.com/work.zip"),
            )
            record_id = record.id
            if operation == "review":
                submissions.update(
                    db,
                    submission_id=record_id,
                    actor=data.users["student"],
                    obj_in=ProjectSubmissionUpdate(status="SUBMITTED"),
                )
    barrier = Barrier(2)

    def execute(index):
        with Session(test_engine) as db:
            actor = db.get(
                User, manager_id if operation in {"review", "project"} else student_id
            )
            barrier.wait(timeout=10)
            try:
                if operation == "project":
                    projects.create(
                        db,
                        track_id=empty_track,
                        actor=actor,
                        obj_in=TrainingProjectCreate(title="Concurrent"),
                    )
                elif operation == "submission":
                    submissions.create(
                        db,
                        project_id=project_id,
                        actor=actor,
                        obj_in=ProjectSubmissionCreate(),
                    )
                elif operation == "resubmit":
                    submissions.update(
                        db,
                        submission_id=record_id,
                        actor=actor,
                        obj_in=ProjectSubmissionUpdate(
                            status="SUBMITTED", student_notes=str(index)
                        ),
                    )
                else:
                    submissions.create_review(
                        db,
                        submission_id=record_id,
                        actor=actor,
                        obj_in=ProjectReviewCreate(
                            score=90 if index == 0 else 50, feedback=str(index)
                        ),
                    )
                return "committed"
            except (ValueError, PermissionError):
                return "denied"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, (0, 1)))
        assert sorted(results) == ["committed", "denied"]
        with Session(test_engine) as db:
            if operation == "project":
                assert (
                    len(
                        db.scalars(
                            select(TrainingProject).where(
                                TrainingProject.track_id == empty_track
                            )
                        ).all()
                    )
                    == 1
                )
            else:
                records = db.scalars(
                    select(ProjectSubmission).where(
                        ProjectSubmission.project_id == project_id
                    )
                ).all()
                assert len(records) == 1
                if operation == "review":
                    assert len(records[0].reviews) == 1
                    assert records[0].status == records[0].reviews[0].status_decision
    finally:
        with Session(test_engine) as db:
            db.execute(delete(Track).where(Track.id.in_(track_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.execute(delete(Role).where(Role.id.in_(created_role_ids)))
            db.commit()
