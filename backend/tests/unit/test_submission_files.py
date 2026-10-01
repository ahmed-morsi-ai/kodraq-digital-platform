from __future__ import annotations

from datetime import UTC, datetime

from io import BytesIO

import pytest

from app.core.security import create_access_token
from app.main import app
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.role import Role
from app.models.submission import Submission, SubmissionFile, SubmissionStatus
from app.models.track import Track
from app.models.user import User
from app.services.storage import LocalStorageService, get_storage_service


def _make_user(
    db_session,
    *,
    email: str,
    role_name: str = "student",
    is_superuser: bool = False,
) -> User:
    role = db_session.query(Role).filter(Role.name == role_name).first()
    if role is None:
        role = Role(name=role_name, description=f"{role_name} role")
        db_session.add(role)
        db_session.flush()

    user = User(
        email=email,
        hashed_password="test-password",
        full_name=email.split("@")[0],
        is_active=True,
        is_superuser=is_superuser,
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _make_submission(db_session, user: User, *, status: str = "DRAFT") -> Submission:
    track = Track(
        name=f"File Track {user.id} {status}",
        slug=f"file-track-{user.id}-{status.lower()}",
        description="File submission test track",
    )
    db_session.add(track)
    db_session.flush()

    assignment = Assignment(
        track_id=track.id,
        title=f"File Assignment {user.id} {status}",
        description="File submission test assignment",
        instructions="Upload a file",
        difficulty="beginner",
        ordering=1,
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(assignment)
    db_session.flush()

    db_session.add(
        Enrollment(
            user_id=user.id,
            track_id=track.id,
            status="active",
            enrolled_at=datetime.now(UTC),
        )
    )
    submission = Submission(
        assignment_id=assignment.id,
        user_id=user.id,
        status=status,
        content="submission content",
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    return submission


@pytest.fixture
def local_storage(client, tmp_path):
    storage = LocalStorageService(tmp_path)
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_service, None)


def test_local_storage_upload_and_delete(tmp_path):
    storage = LocalStorageService(tmp_path)
    stored = storage.upload_file(
        file=BytesIO(b"hello"),
        object_key="submissions/1/example.txt",
        content_type="text/plain",
    )

    assert stored.size_bytes == 5
    with storage.open_file(object_key=stored.object_key) as stream:
        assert stream.read() == b"hello"

    storage.delete_file(object_key=stored.object_key)

    assert not (storage.root / stored.object_key).exists()


def test_owner_can_upload_file(db_session, client, local_storage):
    owner = _make_user(
        db_session,
        email="file-owner@example.com",
    )
    submission = _make_submission(db_session, owner)

    response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(owner),
        files={
            "files": (
                "report.pdf",
                b"hello",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert len(body) == 1
    assert body[0]["file_name"] == "report.pdf"
    assert body[0]["file_size_bytes"] == 5
    assert body[0]["file_type"] == "application/pdf"

    file_path = body[0]["file_url"]
    assert (local_storage.root / file_path).exists()

    db_file = db_session.get(SubmissionFile, body[0]["id"])
    assert db_file is not None
    assert db_file.submission_id == submission.id
    assert db_file.file_size == 5


def test_owner_can_upload_multiple_files(db_session, client, local_storage):
    owner = _make_user(
        db_session,
        email="multi-file-owner@example.com",
    )
    submission = _make_submission(db_session, owner)

    response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(owner),
        files=[
            ("files", ("one.txt", b"one", "text/plain")),
            ("files", ("two.txt", b"two-two", "text/plain")),
        ],
    )

    assert response.status_code == 201
    body = response.json()

    assert len(body) == 2
    assert {item["file_name"] for item in body} == {"one.txt", "two.txt"}
    assert len([p for p in local_storage.root.rglob("*") if p.is_file()]) == 2


def test_other_student_cannot_upload_file(db_session, client, local_storage):
    owner = _make_user(
        db_session,
        email="upload-owner@example.com",
    )
    other = _make_user(
        db_session,
        email="upload-other@example.com",
    )
    submission = _make_submission(db_session, owner)

    response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(other),
        files={
            "files": (
                "blocked.txt",
                b"blocked",
                "text/plain",
            )
        },
    )

    assert response.status_code == 403
    assert not any(p.is_file() for p in local_storage.root.rglob("*"))


@pytest.mark.parametrize(
    "locked_status",
    [
        SubmissionStatus.SUBMITTED.value,
        SubmissionStatus.UNDER_REVIEW.value,
        SubmissionStatus.APPROVED.value,
        SubmissionStatus.REJECTED.value,
    ],
)
def test_locked_submission_rejects_upload(
    db_session,
    client,
    local_storage,
    locked_status,
):
    owner = _make_user(
        db_session,
        email=f"locked-upload-{locked_status.lower()}@example.com",
    )
    submission = _make_submission(
        db_session,
        owner,
        status=locked_status,
    )

    response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(owner),
        files={
            "files": (
                "blocked.txt",
                b"blocked",
                "text/plain",
            )
        },
    )

    assert response.status_code == 409
    assert not any(p.is_file() for p in local_storage.root.rglob("*"))


def test_owner_can_delete_file(db_session, client, local_storage):
    owner = _make_user(
        db_session,
        email="delete-owner@example.com",
    )
    submission = _make_submission(db_session, owner)

    upload_response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(owner),
        files={
            "files": (
                "delete-me.txt",
                b"delete me",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    file_body = upload_response.json()[0]
    file_id = file_body["id"]
    file_path = file_body["file_url"]

    delete_response = client.delete(
        f"/api/v1/submissions/{submission.id}/files/{file_id}",
        headers=_auth_headers(owner),
    )

    assert delete_response.status_code == 204
    assert not (local_storage.root / file_path).exists()
    assert db_session.get(SubmissionFile, file_id) is None


def test_other_student_cannot_delete_file(db_session, client, local_storage):
    owner = _make_user(
        db_session,
        email="delete-owner-2@example.com",
    )
    other = _make_user(
        db_session,
        email="delete-other@example.com",
    )
    submission = _make_submission(db_session, owner)

    upload_response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(owner),
        files={
            "files": (
                "protected.txt",
                b"protected",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    file_body = upload_response.json()[0]
    file_id = file_body["id"]
    file_path = file_body["file_url"]

    delete_response = client.delete(
        f"/api/v1/submissions/{submission.id}/files/{file_id}",
        headers=_auth_headers(other),
    )

    assert delete_response.status_code == 403
    assert (local_storage.root / file_path).exists()
    assert db_session.get(SubmissionFile, file_id) is not None


@pytest.mark.parametrize(
    "locked_status",
    [
        SubmissionStatus.SUBMITTED.value,
        SubmissionStatus.UNDER_REVIEW.value,
        SubmissionStatus.APPROVED.value,
        SubmissionStatus.REJECTED.value,
    ],
)
def test_locked_submission_rejects_delete(
    db_session,
    client,
    local_storage,
    locked_status,
):
    owner = _make_user(
        db_session,
        email=f"locked-delete-{locked_status.lower()}@example.com",
    )
    submission = _make_submission(db_session, owner)

    upload_response = client.post(
        f"/api/v1/submissions/{submission.id}/files",
        headers=_auth_headers(owner),
        files={
            "files": (
                "protected.txt",
                b"protected",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    file_body = upload_response.json()[0]
    file_id = file_body["id"]
    file_path = file_body["file_url"]

    submission.status = locked_status
    db_session.commit()

    delete_response = client.delete(
        f"/api/v1/submissions/{submission.id}/files/{file_id}",
        headers=_auth_headers(owner),
    )

    assert delete_response.status_code == 409
    assert (local_storage.root / file_path).exists()
    assert db_session.get(SubmissionFile, file_id) is not None
