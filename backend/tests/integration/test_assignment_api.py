from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.role import Role
from app.models.track import Lesson, Track, TrackModule
from app.models.track_instructor import TrackInstructor
from app.models.user import User

URL = f"{settings.API_V1_STR}/assignments"


@pytest.fixture(scope="module")
def assignment_password_hash():
    return get_password_hash("AssignmentPassword123!")


def _payload(**context):
    return {
        "title": "HTTP assignment",
        "description": "Assignment description",
        "instructions": "Complete the assignment",
        "difficulty": "beginner",
        **context,
    }


def _context(data, scope, track="a"):
    curriculum = getattr(data, track)
    contexts = {
        "track": {"track_id": curriculum.track.id},
        "module": {"module_id": curriculum.module.id},
        "lesson": {"lesson_id": curriculum.lesson.id},
        "full": {
            "track_id": curriculum.track.id,
            "module_id": curriculum.module.id,
            "lesson_id": curriculum.lesson.id,
        },
        "unscoped": {},
    }
    return contexts[scope]


@pytest.fixture
def assignments_data(db_session, assignment_password_hash):
    roles = {name: Role(name=name) for name in ("student", "instructor", "admin")}
    users = {
        name: User(
            email=f"assignment-{name}@integration.local",
            full_name=f"Assignment {name}",
            hashed_password=assignment_password_hash,
            role_rel=roles.get(name),
            is_superuser=name == "superuser",
        )
        for name in ("student", "instructor", "admin", "superuser", "outsider")
    }
    data = SimpleNamespace(**users)
    for name in ("a", "b"):
        track = Track(name=f"Assignment track {name}", slug=f"assignment-track-{name}")
        module = TrackModule(title=f"Module {name}", track=track)
        lesson = Lesson(title=f"Lesson {name}", module=module)
        setattr(data, name, SimpleNamespace(track=track, module=module, lesson=lesson))
        db_session.add_all([track, module, lesson])
    db_session.add_all(users.values())
    db_session.flush()
    data.enrollment = Enrollment(
        user_id=data.student.id,
        track_id=data.a.track.id,
        status="active",
        enrolled_at=datetime.now(UTC),
    )
    data.instructor_link = TrackInstructor(
        instructor_id=data.instructor.id,
        track_id=data.a.track.id,
    )
    db_session.add_all([data.enrollment, data.instructor_link])
    data.assignments = {}
    # Hidden rows sort first, exposing authorization applied after pagination.
    for track_name in ("b", "a"):
        for scope in ("track", "module", "lesson", "full"):
            item = Assignment(
                **_payload(**_context(data, scope, track_name)), ordering=0
            )
            data.assignments[f"{track_name}_{scope}"] = item
            db_session.add(item)
    data.unscoped = Assignment(**_payload(), ordering=0)
    db_session.add(data.unscoped)
    db_session.commit()
    data.headers = {
        name: {"Authorization": f"Bearer {create_access_token(user.id)}"}
        for name, user in users.items()
    }
    return data


def test_assignment_routes_and_real_login(client, assignments_data):
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": assignments_data.student.email,
            "password": "AssignmentPassword123!",
        },
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get(URL, headers=headers).status_code == 200
    paths = client.get(f"{settings.API_V1_STR}/openapi.json").json()["paths"]
    assert {"get", "post"} <= paths[URL].keys()
    assert {"get", "patch", "delete"} <= paths[f"{URL}/{{assignment_id}}"].keys()


@pytest.mark.parametrize("method", ["list", "get", "post", "patch", "delete"])
def test_assignment_endpoints_require_authentication(client, assignments_data, method):
    item = assignments_data.assignments["a_track"]
    url = URL if method in ("list", "post") else f"{URL}/{item.id}"
    kwargs = (
        {"json": _payload(track_id=assignments_data.a.track.id)}
        if method in ("post", "patch")
        else {}
    )
    response = getattr(client, "get" if method == "list" else method)(url, **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize("token_type", ["invalid", "expired"])
def test_assignment_rejects_invalid_bearer_tokens(client, assignments_data, token_type):
    token = (
        "invalid-token"
        if token_type == "invalid"
        else create_access_token(
            assignments_data.student.id,
            expires_delta=timedelta(seconds=-1),
        )
    )
    assert (
        client.get(URL, headers={"Authorization": f"Bearer {token}"}).status_code == 403
    )


@pytest.mark.parametrize("method", ["list", "get", "post", "patch", "delete"])
def test_inactive_admin_cannot_access_assignments(
    client, db_session, assignments_data, method
):
    data = assignments_data
    data.admin.is_active = False
    db_session.commit()
    url = (
        URL if method in ("list", "post") else f"{URL}/{data.assignments['a_track'].id}"
    )
    kwargs = (
        {"json": _payload(track_id=data.a.track.id)}
        if method in ("post", "patch")
        else {}
    )
    response = getattr(client, "get" if method == "list" else method)(
        url, headers=data.headers["admin"], **kwargs
    )
    assert response.status_code == 400  # Existing active-user dependency contract.


@pytest.mark.parametrize("role", ["student", "instructor"])
def test_assignment_list_is_scoped_before_pagination(client, assignments_data, role):
    data = assignments_data
    expected = [
        data.assignments[f"a_{scope}"].id
        for scope in ("track", "module", "lesson", "full")
    ]
    response = client.get(URL, headers=data.headers[role])
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == expected
    page = client.get(URL, headers=data.headers[role], params={"skip": 1, "limit": 2})
    assert [item["id"] for item in page.json()] == expected[1:3]
    for field, identifier in (
        ("track_id", data.b.track.id),
        ("module_id", data.b.module.id),
        ("lesson_id", data.b.lesson.id),
    ):
        denied = client.get(URL, headers=data.headers[role], params={field: identifier})
        assert denied.status_code == 200
        assert denied.json() == []
    filtered = client.get(
        URL,
        headers=data.headers[role],
        params={
            "track_id": data.a.track.id,
            "module_id": data.a.module.id,
            "lesson_id": data.a.lesson.id,
        },
    )
    assert [item["id"] for item in filtered.json()] == expected[2:]


@pytest.mark.parametrize("role", ["student", "instructor"])
@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full", "unscoped"])
def test_assignment_detail_is_track_isolated(client, assignments_data, role, scope):
    data = assignments_data
    item = data.unscoped if scope == "unscoped" else data.assignments[f"b_{scope}"]
    assert client.get(f"{URL}/{item.id}", headers=data.headers[role]).status_code == 403
    if scope != "unscoped":
        own = data.assignments[f"a_{scope}"]
        response = client.get(f"{URL}/{own.id}", headers=data.headers[role])
        assert response.status_code == 200
        assert response.json()["id"] == own.id


@pytest.mark.parametrize("role", ["student", "outsider"])
@pytest.mark.parametrize("method", ["post", "patch", "delete"])
def test_non_managers_cannot_write_assignments(
    client, db_session, assignments_data, role, method
):
    data = assignments_data
    item = data.assignments["a_track"]
    count = db_session.scalar(select(func.count()).select_from(Assignment))
    url = URL if method == "post" else f"{URL}/{item.id}"
    kwargs = {"json": _payload(track_id=data.a.track.id)} if method != "delete" else {}
    response = getattr(client, method)(url, headers=data.headers[role], **kwargs)
    assert response.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(Assignment)) == count
    db_session.refresh(item)
    assert item.title == "HTTP assignment"


@pytest.mark.parametrize("role", ["instructor", "admin", "superuser"])
@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full"])
def test_authorized_assignment_http_lifecycle(client, assignments_data, role, scope):
    data = assignments_data
    context = _context(data, scope, "a" if role == "instructor" else "b")
    headers = data.headers[role]
    response = client.post(URL, headers=headers, json=_payload(**context))
    assert response.status_code == 201
    item = response.json()
    assert item["created_at"] and item["updated_at"]
    assert all(item[field] == value for field, value in context.items())
    url = f"{URL}/{item['id']}"
    assert client.get(url, headers=headers).status_code == 200
    updated = client.patch(
        url,
        headers=headers,
        json={"title": "Reviewed", "ordering": 0, "is_mandatory": False},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Reviewed"
    assert updated.json()["is_mandatory"] is False
    assert all(updated.json()[field] == value for field, value in context.items())
    deleted = client.delete(url, headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(url, headers=headers).status_code == 404


@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full", "unscoped"])
def test_instructor_cannot_create_outside_assigned_tracks(
    client, db_session, assignments_data, scope
):
    data = assignments_data
    count = db_session.scalar(select(func.count()).select_from(Assignment))
    response = client.post(
        URL,
        headers=data.headers["instructor"],
        json=_payload(**_context(data, scope, "b")),
    )
    assert response.status_code == 403
    assert db_session.scalar(select(func.count()).select_from(Assignment)) == count


@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full", "unscoped"])
@pytest.mark.parametrize("method", ["patch", "delete"])
def test_instructor_cannot_modify_foreign_or_unscoped_assignments(
    client, db_session, assignments_data, scope, method
):
    data = assignments_data
    item = data.unscoped if scope == "unscoped" else data.assignments[f"b_{scope}"]
    kwargs = {"json": {"title": "Forbidden"}} if method == "patch" else {}
    response = getattr(client, method)(
        f"{URL}/{item.id}", headers=data.headers["instructor"], **kwargs
    )
    assert response.status_code == 403
    db_session.refresh(item)
    assert item.title == "HTTP assignment"


@pytest.mark.parametrize("scope", ["track", "module", "lesson", "full", "unscoped"])
def test_patch_checks_destination_track(client, db_session, assignments_data, scope):
    data = assignments_data
    item = data.assignments["a_full"]
    changes = {
        "track_id": None,
        "module_id": None,
        "lesson_id": None,
        **_context(data, scope, "b"),
    }
    response = client.patch(
        f"{URL}/{item.id}", headers=data.headers["instructor"], json=changes
    )
    assert response.status_code == 403
    db_session.refresh(item)
    assert (item.track_id, item.module_id, item.lesson_id) == (
        data.a.track.id,
        data.a.module.id,
        data.a.lesson.id,
    )


def test_patch_checks_source_track_and_allows_authorized_transfer(
    client, db_session, assignments_data
):
    data = assignments_data
    foreign = data.assignments["b_full"]
    response = client.patch(
        f"{URL}/{foreign.id}",
        headers=data.headers["instructor"],
        json=_context(data, "full"),
    )
    assert response.status_code == 403
    db_session.refresh(foreign)
    assert foreign.track_id == data.b.track.id
    db_session.add(
        TrackInstructor(instructor_id=data.instructor.id, track_id=data.b.track.id)
    )
    db_session.commit()
    owned = data.assignments["a_full"]
    response = client.patch(
        f"{URL}/{owned.id}",
        headers=data.headers["instructor"],
        json=_context(data, "full", "b"),
    )
    assert response.status_code == 200
    assert response.json()["track_id"] == data.b.track.id


@pytest.mark.parametrize(
    "enrollment_status", ["active", "completed", "cancelled", "pending_payment"]
)
def test_only_active_enrollment_grants_student_access(
    client, db_session, assignments_data, enrollment_status
):
    data = assignments_data
    data.enrollment.status = enrollment_status
    db_session.commit()
    expected_status = 200 if enrollment_status == "active" else 403
    assert (
        client.get(
            f"{URL}/{data.assignments['a_track'].id}", headers=data.headers["student"]
        ).status_code
        == expected_status
    )
    listing = client.get(URL, headers=data.headers["student"])
    assert listing.status_code == 200
    assert len(listing.json()) == (4 if enrollment_status == "active" else 0)


def test_instructor_enrollment_does_not_replace_track_assignment(
    client, db_session, assignments_data
):
    data = assignments_data
    db_session.add(
        Enrollment(
            user_id=data.instructor.id,
            track_id=data.b.track.id,
            status="active",
            enrolled_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    assert (
        client.get(
            f"{URL}/{data.assignments['b_track'].id}",
            headers=data.headers["instructor"],
        ).status_code
        == 403
    )
    response = client.post(
        URL, headers=data.headers["instructor"], json=_payload(track_id=data.b.track.id)
    )
    assert response.status_code == 403


def test_access_revocation_takes_effect_for_existing_token(
    client, db_session, assignments_data
):
    data = assignments_data
    db_session.delete(data.instructor_link)
    db_session.commit()
    headers = data.headers["instructor"]
    assert client.get(URL, headers=headers).json() == []
    assert (
        client.get(
            f"{URL}/{data.assignments['a_track'].id}", headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            URL, headers=headers, json=_payload(track_id=data.a.track.id)
        ).status_code
        == 403
    )


def test_unenrolled_user_cannot_borrow_another_users_enrollment(
    client, assignments_data
):
    data = assignments_data
    headers = data.headers["outsider"]
    response = client.get(URL, headers=headers)
    assert response.status_code == 200
    assert response.json() == []
    assert (
        client.get(
            f"{URL}/{data.assignments['a_track'].id}", headers=headers
        ).status_code
        == 403
    )


def test_instructor_cannot_borrow_another_instructors_track_link(
    client, db_session, assignments_data, assignment_password_hash
):
    data = assignments_data
    other = User(
        email="other-instructor@integration.local",
        full_name="Other Instructor",
        hashed_password=assignment_password_hash,
        role_rel=data.instructor.role_rel,
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(TrackInstructor(instructor_id=other.id, track_id=data.b.track.id))
    db_session.commit()
    headers = data.headers["instructor"]
    response = client.get(URL, headers=headers, params={"track_id": data.b.track.id})
    assert response.status_code == 200
    assert response.json() == []
    assert (
        client.get(
            f"{URL}/{data.assignments['b_track'].id}", headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            URL, headers=headers, json=_payload(track_id=data.b.track.id)
        ).status_code
        == 403
    )


@pytest.mark.parametrize("role", ["admin", "superuser"])
def test_admin_global_and_unscoped_access(client, assignments_data, role):
    data = assignments_data
    headers = data.headers[role]
    listing = client.get(URL, headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 9
    created = client.post(URL, headers=headers, json=_payload())
    assert created.status_code == 201
    url = f"{URL}/{created.json()['id']}"
    assert client.get(url, headers=headers).status_code == 200
    assert (
        client.patch(
            url, headers=headers, json={"title": "Unscoped update"}
        ).status_code
        == 200
    )
    assert client.delete(url, headers=headers).status_code == 204


@pytest.mark.parametrize(
    "invalid",
    [{"difficulty": "expert"}, {"title": "x" * 256}, {"title": None}, {"id": 100}],
)
@pytest.mark.parametrize("method", ["post", "patch"])
def test_assignment_validation_errors_over_http(
    client, assignments_data, invalid, method
):
    data = assignments_data
    url = URL if method == "post" else f"{URL}/{data.assignments['a_track'].id}"
    payload = (
        _payload(track_id=data.a.track.id) | invalid if method == "post" else invalid
    )
    response = getattr(client, method)(url, headers=data.headers["admin"], json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["post", "patch"])
def test_http_rejects_missing_and_inconsistent_context(
    client, assignments_data, method
):
    data = assignments_data
    url = URL if method == "post" else f"{URL}/{data.assignments['a_full'].id}"
    for context, expected in (
        ({"track_id": 999999}, 404),
        ({"track_id": data.a.track.id, "module_id": data.b.module.id}, 422),
    ):
        payload = _payload(**context) if method == "post" else context
        response = getattr(client, method)(
            url, headers=data.headers["admin"], json=payload
        )
        assert response.status_code == expected


@pytest.mark.parametrize("role", ["admin", "instructor"])
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_assignment_returns_404(client, assignments_data, role, method):
    kwargs = {"json": {"title": "Missing"}} if method == "patch" else {}
    response = getattr(client, method)(
        f"{URL}/999999", headers=assignments_data.headers[role], **kwargs
    )
    assert response.status_code == 404


@pytest.mark.parametrize("mismatch", ["module_track", "lesson_track", "lesson_module"])
def test_legacy_inconsistent_assignments_are_not_exposed(
    client, db_session, assignments_data, mismatch
):
    data = assignments_data
    second_module = TrackModule(track=data.a.track, title="Another owned module")
    db_session.add(second_module)
    db_session.flush()
    context = {
        "module_track": {"track_id": data.a.track.id, "module_id": data.b.module.id},
        "lesson_track": {"track_id": data.a.track.id, "lesson_id": data.b.lesson.id},
        "lesson_module": {"module_id": second_module.id, "lesson_id": data.a.lesson.id},
    }[mismatch]
    malformed = Assignment(**_payload(**context))
    db_session.add(malformed)
    db_session.commit()
    for role in ("student", "instructor"):
        headers = data.headers[role]
        listing = client.get(URL, headers=headers)
        assert malformed.id not in [item["id"] for item in listing.json()]
        assert client.get(f"{URL}/{malformed.id}", headers=headers).status_code == 403
    assert (
        client.patch(
            f"{URL}/{malformed.id}",
            headers=data.headers["instructor"],
            json={"title": "Blocked"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"{URL}/{malformed.id}", headers=data.headers["instructor"]
        ).status_code
        == 403
    )
