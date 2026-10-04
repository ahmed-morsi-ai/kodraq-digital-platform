"""SAFE-01 HTTP regressions using synthetic actors and no database connection.

Run from the repository root with the backend environment's Python. This file is
outside backend/tests deliberately: that tree's autouse fixtures use a database.
SAFE01_BASELINE_COMMIT optionally loads only the old tracks router from git for
the locked-curriculum regression, without changing any checkout or database.
"""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "safe01-synthetic-test-secret-never-production"
os.environ["DEBUG"] = "True"
sys.path.insert(0, str(ROOT / "backend"))

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.sql import visitors  # noqa: E402

from app.api import admin_dashboard, deps  # noqa: E402
from app.api.v1 import enrollments, tracks as fixed_tracks  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.admin_identity import PLATFORM_ADMIN_EMAIL  # noqa: E402
from app.core.security import ALGORITHM  # noqa: E402
from app.db.session import engine, get_db  # noqa: E402
from app.models.enrollment import Enrollment  # noqa: E402
from app.models.track import Lesson, Track  # noqa: E402

TRACK_ID = 9001
OTHER_TRACK_ID = 9002
LESSON_ID = 9201
ENROLLMENT_ID = 9301
PROGRESS_ID = 9401
STUDENT_ID = 9101
OTHER_STUDENT_ID = 9102
ADMIN_ID = 9999
VIDEO = "https://synthetic.invalid/protected-video-safe01"
RESOURCE = "https://synthetic.invalid/protected-resource-safe01.pdf"
CONTENT = "SYNTHETIC PROTECTED LESSON CONTENT SAFE01"
EXPLANATION = "SYNTHETIC ANSWER EXPLANATION SAFE01"
ANSWER_KEYS = {"correct_index", "explanation", "is_correct", "answer_key"}


def _tracks_module() -> ModuleType:
    baseline = os.environ.get("SAFE01_BASELINE_COMMIT")
    if not baseline:
        return fixed_tracks
    result = subprocess.run(
        ["git", "show", f"{baseline}:backend/app/api/v1/tracks.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    name = "app.api.v1.safe01_baseline_tracks"
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, None))
    sys.modules[name] = module
    exec(compile(result.stdout, f"{baseline}/tracks.py", "exec"), module.__dict__)
    return module


tracks = _tracks_module()


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def _assert_no_answers(value):
    assert not (set(_keys(value)) & ANSWER_KEYS)
    assert EXPLANATION not in json.dumps(value)


def _assert_locked(value):
    _assert_no_answers(value)
    assert not (set(_keys(value)) & {"content", "video_url", "file_url", "quiz_data"})
    encoded = json.dumps(value)
    for secret in (VIDEO, RESOURCE, CONTENT):
        assert secret not in encoded


class SyntheticSession:
    """Only expected read queries are served; real SQL and session writes fail."""

    def __init__(self, fixture):
        self.fixture = fixture

    def scalar(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        params = statement.compile().params
        if entity is Enrollment:
            enrollment = self.fixture.enrollment
            if enrollment is None:
                return None
            if (
                params.get("user_id_1") == enrollment.user_id
                and params.get("track_id_1") == enrollment.track_id
            ):
                return enrollment
            return None
        if entity is Lesson:
            # Honor the active-track predicate only when the actual SQL has it;
            # removing that predicate must make the inactive-track test fail.
            requires_active_track = any(
                getattr(node, "name", None) == "is_active"
                and getattr(getattr(node, "table", None), "name", None) == "tracks"
                for node in visitors.iterate(statement.whereclause)
            )
            if (
                params.get("id_1") == self.fixture.lesson.id
                and params.get("track_id_1") == self.fixture.track.id
                and (not requires_active_track or self.fixture.track.is_active)
            ):
                return self.fixture.lesson
            return None
        raise AssertionError(f"Unexpected SQL entity: {entity}")

    def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Track:
            return SimpleNamespace(all=lambda: [self.fixture.track])
        raise AssertionError("Unexpected SQL scalars")

    def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        params = statement.compile().params
        if entity is Lesson and params.get("id_2", params.get("id_1")) == self.fixture.lesson.id:
            return SimpleNamespace(scalar_one_or_none=lambda: self.fixture.lesson)
        raise AssertionError("Unexpected SQL execute")

    def get(self, entity, identity):
        if entity is Track and identity == self.fixture.track.id:
            return self.fixture.track
        raise AssertionError("Unexpected SQL get")

    def __getattr__(self, name):
        if name in {"commit", "flush", "add", "delete", "rollback", "refresh"}:
            raise AssertionError(f"Database mutation is forbidden: {name}")
        raise AttributeError(name)


@pytest.fixture(autouse=True)
def forbid_database_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SAFE-01 tests must not connect to a database or network")

    assert str(engine.url) == "sqlite://"
    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def fixture(monkeypatch):
    actors = {
        identity: SimpleNamespace(
            id=identity,
            email=f"synthetic-{identity}@example.invalid",
            is_active=True,
            is_superuser=identity == ADMIN_ID,
            role_rel=SimpleNamespace(name="admin" if identity == ADMIN_ID else "student"),
        )
        for identity in (STUDENT_ID, OTHER_STUDENT_ID, ADMIN_ID)
    }
    actors[ADMIN_ID].email = PLATFORM_ADMIN_EMAIL
    questions = [
        {
            "id": 1,
            "question": "Synthetic question one?",
            "options": ["A", "B", "C"],
            "correct_index": 1,
            "explanation": EXPLANATION,
            "answer_key": "SHOULD NEVER BE RETURNED",
        },
        {
            "id": 2,
            "question": "Synthetic question two?",
            "options": ["D", "E"],
            "correct_index": 0,
            "explanation": EXPLANATION,
        },
    ]
    lesson = SimpleNamespace(
        id=LESSON_ID,
        module_id=9501,
        title="Synthetic lesson",
        description="Safe lesson description",
        content=CONTENT,
        video_url=VIDEO,
        ordering=1,
        quiz_data=questions,
    )
    resource = SimpleNamespace(
        id=9601,
        module_id=9501,
        title="Synthetic reference",
        file_url=RESOURCE,
        resource_type="document",
    )
    module = SimpleNamespace(
        id=9501,
        track_id=TRACK_ID,
        title="Synthetic module",
        description="Safe module description",
        ordering=1,
        is_active=True,
        lessons=[lesson],
        resources=[resource],
    )
    lesson.module = module
    track = SimpleNamespace(
        id=TRACK_ID,
        name="Synthetic paid curriculum",
        slug="synthetic-safe01",
        description="Safe track description",
        ordering=1,
        is_active=True,
        is_premium=True,
        price=100.0,
        currency="EGP",
        modules=[module],
    )
    progress = SimpleNamespace(
        id=PROGRESS_ID,
        enrollment_id=ENROLLMENT_ID,
        lesson_id=LESSON_ID,
        status="in_progress",
        progress_percentage=20,
        started_at=datetime(2020, 1, 1, tzinfo=UTC),
        completed_at=None,
        lesson=lesson,
    )
    enrollment = SimpleNamespace(
        id=ENROLLMENT_ID,
        user_id=STUDENT_ID,
        track_id=TRACK_ID,
        status="active",
        enrolled_at=datetime(2020, 1, 1, tzinfo=UTC),
        completed_at=None,
        track=track,
        progress=[progress],
    )
    state = SimpleNamespace(
        actors=actors,
        track=track,
        lesson=lesson,
        enrollment=enrollment,
        progress=progress,
    )
    state.session = SyntheticSession(state)

    # Preserve actual OAuth2 extraction, JWT validation and active-user checks.
    monkeypatch.setattr(
        deps.crud_user,
        "get",
        lambda session, *, id: actors.get(int(id)) if id is not None else None,
    )
    monkeypatch.setattr(deps.crud_user, "ensure_designated_admin", lambda session, user: False)
    monkeypatch.setattr(
        tracks.crud_track,
        "get_with_curriculum",
        lambda session, *, id: track if id == TRACK_ID else None,
    )
    monkeypatch.setattr(tracks.crud_track, "get_active", lambda *args, **kwargs: [track])
    monkeypatch.setattr(
        enrollments.crud_track,
        "get",
        lambda session, *, id: track if id == TRACK_ID else None,
    )
    monkeypatch.setattr(
        enrollments.crud_enrollment,
        "get_detail",
        lambda session, *, id: state.enrollment
        if state.enrollment is not None and id == state.enrollment.id
        else None,
    )
    monkeypatch.setattr(
        enrollments.crud_enrollment,
        "get",
        lambda session, *, id: state.enrollment
        if state.enrollment is not None and id == state.enrollment.id
        else None,
    )
    monkeypatch.setattr(
        enrollments.crud_enrollment,
        "get_multi_by_user",
        lambda session, *, user_id: [state.enrollment]
        if state.enrollment is not None and user_id == state.enrollment.user_id
        else [],
    )
    monkeypatch.setattr(
        enrollments.crud_enrollment,
        "get_multi_by_track",
        lambda session, *, track_id: [state.enrollment]
        if state.enrollment is not None and track_id == state.enrollment.track_id
        else [],
    )
    monkeypatch.setattr(
        enrollments.crud_student_progress,
        "get_multi_by_enrollment",
        lambda session, *, enrollment_id: [progress]
        if enrollment_id == ENROLLMENT_ID
        else [],
    )
    monkeypatch.setattr(
        enrollments.crud_student_progress,
        "get_detail",
        lambda session, *, id: progress if id == PROGRESS_ID else None,
    )
    monkeypatch.setattr(
        enrollments.crud_student_progress,
        "update",
        lambda session, *, db_obj, obj_in: db_obj,
    )
    monkeypatch.setattr(
        enrollments.crud_student_progress,
        "create",
        lambda session, *, obj_in: progress,
    )
    monkeypatch.setattr(
        enrollments.crud_student_progress,
        "get_by_enrollment_and_lesson",
        lambda *args, **kwargs: None,
    )
    app = FastAPI()
    app.include_router(tracks.router, prefix="/api/v1/tracks")
    app.include_router(enrollments.router, prefix="/api/v1/enrollments")
    app.include_router(admin_dashboard.router)
    app.dependency_overrides[get_db] = lambda: state.session
    state.client = TestClient(app)

    def headers(identity=STUDENT_ID, *, expired=False):
        token = jwt.encode(
            {
                "sub": str(identity),
                "exp": datetime.now(UTC)
                + timedelta(minutes=-1 if expired else 5),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        return {"Authorization": f"Bearer {token}"}

    state.headers = headers
    yield state
    state.client.close()


def _curriculum(fixture, identity=STUDENT_ID):
    return fixture.client.get(
        f"/api/v1/tracks/{TRACK_ID}/curriculum", headers=fixture.headers(identity)
    )


def _submit(fixture, answers=None, identity=STUDENT_ID, track_id=TRACK_ID, lesson_id=LESSON_ID):
    return fixture.client.post(
        f"/api/v1/tracks/{track_id}/lessons/{lesson_id}/quiz/submit",
        headers=fixture.headers(identity),
        json={"answers": answers if answers is not None else [
            {"question_id": 1, "selected_index": 1},
            {"question_id": 2, "selected_index": 0},
        ]},
    )


def test_anonymous_curriculum_is_unauthenticated(fixture):
    response = fixture.client.get(f"/api/v1/tracks/{TRACK_ID}/curriculum")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    _assert_locked(response.json())


@pytest.mark.parametrize("token_type", ["invalid", "expired", "missing-user", "inactive"])
def test_existing_authentication_rejects_invalid_actors(fixture, token_type):
    headers = fixture.headers()
    expected = 403
    if token_type == "invalid":
        headers = {"Authorization": "Bearer synthetic-invalid-token"}
    elif token_type == "expired":
        headers = fixture.headers(expired=True)
    elif token_type == "missing-user":
        headers = fixture.headers(999999)
        expected = 404
    else:
        fixture.actors[STUDENT_ID].is_active = False
        expected = 400
    response = fixture.client.get(f"/api/v1/tracks/{TRACK_ID}/curriculum", headers=headers)
    assert response.status_code == expected
    _assert_locked(response.json())


@pytest.mark.parametrize("status", [None, "pending", "cancelled", "completed", "wrong-track"])
def test_locked_curriculum_never_exposes_protected_data(fixture, status):
    if status is None:
        fixture.enrollment = None
    elif status == "wrong-track":
        fixture.enrollment.track_id = OTHER_TRACK_ID
    else:
        fixture.enrollment.status = status
    response = _curriculum(fixture)
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == TRACK_ID
    assert payload["price"] == 100.0
    assert payload["modules"][0]["lessons"][0]["title"] == "Synthetic lesson"
    assert payload["modules"][0]["resources"][0]["title"] == "Synthetic reference"
    _assert_locked(payload)


def test_other_users_active_enrollment_does_not_grant_access(fixture):
    response = _curriculum(fixture, OTHER_STUDENT_ID)
    assert response.status_code == 200
    _assert_locked(response.json())


@pytest.mark.parametrize("field,secret", [("video_url", VIDEO), ("file_url", RESOURCE)])
def test_nonenrolled_curriculum_has_no_protected_media_url(fixture, field, secret):
    fixture.enrollment = None
    response = _curriculum(fixture)
    assert response.status_code == 200
    assert field not in set(_keys(response.json()))
    assert secret not in response.text


@pytest.mark.parametrize("identity", [STUDENT_ID, ADMIN_ID])
def test_entitled_curriculum_keeps_content_but_only_quiz_prompts(fixture, identity):
    if identity == ADMIN_ID:
        fixture.enrollment = None
    response = _curriculum(fixture, identity)
    assert response.status_code == 200
    payload = response.json()
    lesson = payload["modules"][0]["lessons"][0]
    resource = payload["modules"][0]["resources"][0]
    assert lesson["video_url"] == VIDEO
    assert lesson["content"] == CONTENT
    assert resource["file_url"] == RESOURCE
    assert lesson["quiz_data"] == [
        {"id": 1, "question": "Synthetic question one?", "options": ["A", "B", "C"]},
        {"id": 2, "question": "Synthetic question two?", "options": ["D", "E"]},
    ]
    _assert_no_answers(payload)


def test_authorized_explicit_null_lesson_fields_keep_existing_shape(fixture):
    fixture.lesson.content = None
    fixture.lesson.video_url = None
    response = _curriculum(fixture)
    assert response.status_code == 200
    lesson = response.json()["modules"][0]["lessons"][0]
    assert "content" in lesson and lesson["content"] is None
    assert "video_url" in lesson and lesson["video_url"] is None
    _assert_no_answers(response.json())


@pytest.mark.parametrize("role", ["admin", "instructor"])
def test_role_label_alone_does_not_expand_curriculum_entitlement(fixture, role):
    fixture.enrollment = None
    fixture.actors[STUDENT_ID].role_rel.name = role
    response = _curriculum(fixture)
    assert response.status_code == 200
    _assert_locked(response.json())


def test_public_track_listing_keeps_metadata_without_curriculum(fixture):
    response = fixture.client.get("/api/v1/tracks")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == TRACK_ID
    assert payload[0]["slug"] == "synthetic-safe01"
    assert payload[0]["currency"] == "EGP"
    assert "modules" not in payload[0]
    _assert_locked(payload)


@pytest.mark.parametrize("state", ["missing", "inactive"])
def test_unknown_or_inactive_curriculum_keeps_404(fixture, state):
    if state == "inactive":
        fixture.track.is_active = False
    response = fixture.client.get(
        f"/api/v1/tracks/{TRACK_ID if state == 'inactive' else OTHER_TRACK_ID}/curriculum",
        headers=fixture.headers(),
    )
    assert response.status_code == 404
    _assert_locked(response.json())


@pytest.mark.parametrize("identity", [STUDENT_ID, ADMIN_ID])
def test_authorized_quiz_submit_retains_server_scoring_and_feedback(fixture, identity):
    if identity == ADMIN_ID:
        fixture.enrollment = None
    response = _submit(fixture, identity=identity)
    assert response.status_code == 200
    result = response.json()
    assert (result["score"], result["total"], result["percentage"]) == (2, 2, 100)
    assert [answer["correct_index"] for answer in result["answers"]] == [1, 0]
    assert all(answer["is_correct"] for answer in result["answers"])
    assert all(answer["explanation"] == EXPLANATION for answer in result["answers"])


def test_authorized_quiz_submit_scores_incorrect_answers(fixture):
    response = _submit(fixture, answers=[
        {"question_id": 1, "selected_index": 0},
        {"question_id": 2, "selected_index": 0},
    ])
    assert response.status_code == 200
    result = response.json()
    assert (result["score"], result["total"], result["percentage"]) == (1, 2, 50)
    assert [answer["is_correct"] for answer in result["answers"]] == [False, True]


@pytest.mark.parametrize("status", [None, "pending", "cancelled", "completed", "wrong-track"])
def test_unauthorized_quiz_submit_is_forbidden_without_answers(fixture, status):
    if status is None:
        fixture.enrollment = None
    elif status == "wrong-track":
        fixture.enrollment.track_id = OTHER_TRACK_ID
    else:
        fixture.enrollment.status = status
    response = _submit(fixture)
    assert response.status_code == 403
    _assert_locked(response.json())


def test_anonymous_quiz_submit_remains_unauthenticated(fixture):
    response = fixture.client.post(
        f"/api/v1/tracks/{TRACK_ID}/lessons/{LESSON_ID}/quiz/submit",
        json={"answers": [{"question_id": 1, "selected_index": 0}]},
    )
    assert response.status_code == 401
    _assert_locked(response.json())


@pytest.mark.parametrize("answers", [
    [],
    [{"question_id": 1, "selected_index": 1}],
    [{"question_id": 1, "selected_index": 1}, {"question_id": 1, "selected_index": 0}],
    [{"question_id": 1, "selected_index": 3}, {"question_id": 2, "selected_index": 0}],
    [{"question_id": 1, "selected_index": -1}, {"question_id": 2, "selected_index": 0}],
    [{"question_id": 1, "selected_index": 1}, {"question_id": 99, "selected_index": 0}],
    [{"question_id": 1, "selected_index": "bad"}, {"question_id": 2, "selected_index": 0}],
])
def test_invalid_quiz_submissions_are_rejected_without_answer_keys(fixture, answers):
    response = _submit(fixture, answers=answers)
    assert response.status_code == 422
    _assert_no_answers(response.json())


@pytest.mark.parametrize("track_id,lesson_id", [(OTHER_TRACK_ID, LESSON_ID), (TRACK_ID, 999999)])
def test_quiz_submission_does_not_accept_cross_track_or_missing_lesson(fixture, track_id, lesson_id):
    response = _submit(fixture, track_id=track_id, lesson_id=lesson_id)
    assert response.status_code == 404
    _assert_locked(response.json())


@pytest.mark.parametrize("raw_quiz", [None, [], "invalid JSON", [{"id": 1}]])
def test_missing_or_malformed_quiz_has_no_answer_disclosure(fixture, raw_quiz):
    fixture.lesson.quiz_data = raw_quiz
    response = _submit(fixture)
    assert response.status_code == 404
    _assert_locked(response.json())


def test_legacy_json_quiz_storage_still_scores_authorized_submission(fixture):
    fixture.lesson.quiz_data = json.dumps(fixture.lesson.quiz_data)
    response = _submit(fixture)
    assert response.status_code == 200
    assert response.json()["score"] == 2


@pytest.mark.parametrize("route", ["me", str(ENROLLMENT_ID), f"{ENROLLMENT_ID}/progress"])
@pytest.mark.parametrize("status", ["pending", "cancelled", "completed"])
def test_nonactive_owner_enrollment_routes_hide_nested_protected_lessons(fixture, route, status):
    fixture.enrollment.status = status
    response = fixture.client.get(f"/api/v1/enrollments/{route}", headers=fixture.headers())
    assert response.status_code == 200
    _assert_locked(response.json())


@pytest.mark.parametrize("route", ["me", str(ENROLLMENT_ID), f"{ENROLLMENT_ID}/progress"])
def test_active_owner_enrollment_routes_keep_content_without_answer_keys(fixture, route):
    response = fixture.client.get(f"/api/v1/enrollments/{route}", headers=fixture.headers())
    assert response.status_code == 200
    payload = response.json()
    assert VIDEO in json.dumps(payload)
    assert CONTENT in json.dumps(payload)
    _assert_no_answers(payload)


@pytest.mark.parametrize("route", [str(ENROLLMENT_ID), f"{ENROLLMENT_ID}/progress"])
def test_other_users_cannot_read_enrollment_or_progress(fixture, route):
    response = fixture.client.get(
        f"/api/v1/enrollments/{route}", headers=fixture.headers(OTHER_STUDENT_ID)
    )
    assert response.status_code == 403
    _assert_locked(response.json())


def test_student_cannot_read_admin_track_enrollments(fixture):
    response = fixture.client.get(
        f"/api/v1/enrollments/track/{TRACK_ID}", headers=fixture.headers()
    )
    assert response.status_code == 403
    _assert_locked(response.json())


@pytest.mark.parametrize("route", [str(ENROLLMENT_ID), f"track/{TRACK_ID}", f"{ENROLLMENT_ID}/progress"])
def test_explicit_superuser_enrollment_access_keeps_content_without_answer_keys(fixture, route):
    fixture.enrollment.status = "pending"
    response = fixture.client.get(
        f"/api/v1/enrollments/{route}", headers=fixture.headers(ADMIN_ID)
    )
    assert response.status_code == 200
    payload = response.json()
    assert VIDEO in json.dumps(payload)
    _assert_no_answers(payload)


@pytest.mark.parametrize("status", ["active", "pending"])
@pytest.mark.parametrize("method", ["post", "patch"])
def test_synthetic_progress_write_responses_obey_same_security_contract(fixture, status, method):
    fixture.enrollment.status = status
    if method == "post":
        response = fixture.client.post(
            f"/api/v1/enrollments/{ENROLLMENT_ID}/progress",
            headers=fixture.headers(),
            json={"enrollment_id": ENROLLMENT_ID, "lesson_id": LESSON_ID},
        )
        assert response.status_code == 201
    else:
        response = fixture.client.patch(
            f"/api/v1/enrollments/{ENROLLMENT_ID}/progress/{PROGRESS_ID}",
            headers=fixture.headers(),
            json={"progress_percentage": 30},
        )
        assert response.status_code == 200
    payload = response.json()
    if status == "active":
        assert VIDEO in json.dumps(payload)
        _assert_no_answers(payload)
    else:
        _assert_locked(payload)


@pytest.mark.parametrize("identity", [None, STUDENT_ID, OTHER_STUDENT_ID])
def test_admin_content_source_rejects_anonymous_and_ordinary_students(fixture, identity):
    response = fixture.client.get(
        "/api/admin/content/tracks",
        headers=fixture.headers(identity) if identity is not None else {},
    )
    assert response.status_code == (401 if identity is None else 403)
    _assert_locked(response.json())


def test_designated_admin_cms_keeps_full_private_source(fixture):
    response = fixture.client.get(
        "/api/admin/content/tracks", headers=fixture.headers(ADMIN_ID)
    )
    assert response.status_code == 200
    module = response.json()[0]["modules"][0]
    lesson = module["lessons"][0]
    assert lesson["video_url"] == VIDEO
    assert lesson["content"] == CONTENT
    assert module["resources"][0]["file_url"] == RESOURCE
    assert lesson["quiz_data"][0]["correct_index"] == 1
    assert lesson["quiz_data"][0]["explanation"] == EXPLANATION


def test_role_label_cannot_grant_private_admin_cms_access(fixture):
    fixture.actors[STUDENT_ID].role_rel.name = "admin"
    response = fixture.client.get(
        "/api/admin/content/tracks", headers=fixture.headers()
    )
    assert response.status_code == 403
    _assert_locked(response.json())


def test_quiz_submit_keeps_inactive_track_unavailable(fixture):
    fixture.track.is_active = False
    response = _submit(fixture)
    assert response.status_code == 404
    _assert_locked(response.json())
