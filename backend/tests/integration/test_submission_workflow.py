from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.submission import SubmissionAttempt, SubmissionFile
from app.services.storage import (
    FileTooLargeError,
    LocalStorageService,
    get_storage_service,
)
from tests.submission_helpers import headers, make_submission

URL = "/api/v1/submissions"


@pytest.fixture
def storage(client, tmp_path):
    service = LocalStorageService(tmp_path, max_file_bytes=32)
    app.dependency_overrides[get_storage_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_storage_service, None)


def upload(
    client, data, submission, content=b"private work", role="student", name="work.txt"
):
    return client.post(
        f"{URL}/{submission.id}/files",
        headers=headers(data, role),
        files={"files": (name, content, "text/plain")},
    )


@pytest.mark.parametrize(
    "role,expected",
    [
        ("student", 200),
        ("other", 403),
        ("instructor", 200),
        ("admin", 200),
        ("superuser", 200),
        ("employee", 403),
    ],
)
def test_private_download_permissions(
    client, db_session, submission_data, storage, role, expected
):
    submission = make_submission(db_session, submission_data)
    record = upload(client, submission_data, submission).json()[0]
    response = client.get(
        f"{URL}/{submission.id}/files/{record['id']}/download",
        headers=headers(submission_data, role),
    )
    assert response.status_code == expected
    if expected == 200:
        assert response.content == b"private work"
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment;")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "private, no-store"


def test_cross_track_instructor_cannot_download(
    client, db_session, submission_data, storage
):
    submission = make_submission(
        db_session, submission_data, scope="other", owner="other"
    )
    record = upload(client, submission_data, submission, role="other").json()[0]
    assert (
        client.get(
            f"{URL}/{submission.id}/files/{record['id']}/download",
            headers=headers(submission_data, "instructor"),
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "role,expected",
    [
        ("student", 201),
        ("other", 403),
        ("instructor", 403),
        ("admin", 201),
        ("superuser", 201),
        ("employee", 403),
    ],
)
def test_upload_roles(client, db_session, submission_data, storage, role, expected):
    submission = make_submission(db_session, submission_data)
    assert (
        upload(client, submission_data, submission, role=role).status_code == expected
    )


def test_upload_batch_rolls_back_bytes_and_records_on_size_error(
    client, db_session, submission_data, storage
):
    submission = make_submission(db_session, submission_data)
    response = client.post(
        f"{URL}/{submission.id}/files",
        headers=headers(submission_data),
        files=[("files", ("small.txt", b"okay")), ("files", ("large.txt", b"x" * 33))],
    )
    assert response.status_code == 413
    assert not any(path.is_file() for path in storage.root.rglob("*"))
    assert db_session.scalar(select(func.count()).select_from(SubmissionFile)) == 0


def test_file_count_limit_includes_existing_uploads(
    client, db_session, submission_data, storage, monkeypatch
):
    monkeypatch.setattr(settings, "SUBMISSION_MAX_FILES", 1)
    submission = make_submission(db_session, submission_data)
    assert upload(client, submission_data, submission).status_code == 201
    assert upload(client, submission_data, submission).status_code == 422
    assert len(list(path for path in storage.root.rglob("*") if path.is_file())) == 1


def test_download_checks_file_parent_and_missing_bytes(
    client, db_session, submission_data, storage
):
    submission = make_submission(db_session, submission_data)
    other = make_submission(db_session, submission_data)
    record = upload(client, submission_data, submission).json()[0]
    for parent, file_id in ((other.id, record["id"]), (submission.id, str(uuid4()))):
        assert (
            client.get(
                f"{URL}/{parent}/files/{file_id}/download",
                headers=headers(submission_data),
            ).status_code
            == 404
        )
    storage.delete_file(object_key=record["file_url"])
    assert (
        client.get(
            f"{URL}/{submission.id}/files/{record['id']}/download",
            headers=headers(submission_data),
        ).status_code
        == 404
    )


def test_upload_name_cannot_control_storage_path(
    client, db_session, submission_data, storage
):
    submission = make_submission(db_session, submission_data)
    response = upload(client, submission_data, submission, name="../../other.txt")
    assert response.status_code == 201
    record = response.json()[0]
    assert ".." not in record["file_url"]
    assert record["file_url"].startswith(f"submissions/{submission.id}/")
    with storage.open_file(object_key=record["file_url"]) as stream:
        assert stream.read() == b"private work"


def test_oversized_filename_rejected_before_storage(
    client, db_session, submission_data, storage
):
    submission = make_submission(db_session, submission_data)
    assert (
        upload(client, submission_data, submission, name="a" * 513).status_code == 422
    )
    assert not any(path.is_file() for path in storage.root.rglob("*"))


@pytest.mark.parametrize(
    "key",
    [
        "../escape",
        "/absolute",
        "a/../../escape",
        "C:/escape",
        "a\\escape",
        "a//b",
        "a/./b",
        "a\x00b",
        "",
    ],
)
def test_storage_rejects_unsafe_keys(tmp_path, key):
    storage = LocalStorageService(tmp_path)
    for operation in (
        lambda: storage.upload_file(file=BytesIO(b"x"), object_key=key),
        lambda: storage.open_file(object_key=key),
        lambda: storage.delete_file(object_key=key),
    ):
        with pytest.raises(ValueError):
            operation()


def test_local_storage_persists_between_instances_and_rejects_overwrite(tmp_path):
    storage = LocalStorageService(tmp_path, max_file_bytes=4)
    storage.upload_file(file=BytesIO(b"1234"), object_key="submissions/file")
    with pytest.raises(FileExistsError):
        storage.upload_file(file=BytesIO(b"oops"), object_key="submissions/file")
    with LocalStorageService(tmp_path).open_file(
        object_key="submissions/file"
    ) as stream:
        assert stream.read() == b"1234"
    with pytest.raises(FileTooLargeError):
        storage.upload_file(file=BytesIO(b"12345"), object_key="too-large")
    assert not (tmp_path / "too-large").exists()


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com",
        "https://github.com/student",
        "http://github.com/student/work",
        "https://github.com.evil/student/work",
        "https://evil@github.com/student/work",
        "https://github.com:443/student/work",
        "https://github.com/student/work/tree/main",
        "https://github.com/student/work?x=1",
        "https://github.com/student/work#readme",
        "https://github.com/student/..",
        "https://github.com/student/.git",
        "https://github.com/student/repo%2fsecret",
        " https://github.com/student/work",
        "https://github.com/-student/work",
        "https://github.com/student/" + "a" * 101,
    ],
)
@pytest.mark.parametrize("method", ["post", "patch"])
def test_repository_url_http_validation(
    client, db_session, submission_data, value, method
):
    submission = make_submission(db_session, submission_data)
    payload = {"github_url": value}
    url = f"{URL}/{submission.id}" if method == "patch" else URL
    if method == "post":
        payload["assignment_id"] = submission.assignment_id
    response = getattr(client, method)(
        url, headers=headers(submission_data), json=payload
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "value,expected",
    [
        ("HTTPS://GITHUB.COM/Student/Work/", "https://github.com/Student/Work"),
        (
            "https://github.com/my-org/project.git",
            "https://github.com/my-org/project.git",
        ),
        (None, None),
    ],
)
def test_repository_url_normalization(
    client, db_session, submission_data, value, expected
):
    submission = make_submission(db_session, submission_data)
    response = client.patch(
        f"{URL}/{submission.id}",
        headers=headers(submission_data),
        json={"github_url": value},
    )
    assert response.status_code == 200
    assert response.json()["github_url"] == expected


def test_full_rework_history_and_assignment_filter(
    client, db_session, submission_data, storage
):
    data = submission_data
    submission = make_submission(db_session, data)
    unrelated = make_submission(db_session, data, scope="module")
    assert unrelated.assignment_id != submission.assignment_id
    record = upload(client, data, submission).json()[0]
    url = f"{URL}/{submission.id}"
    timestamps = []
    for attempt in range(2):
        response = client.patch(
            url, headers=headers(data), json={"status": "SUBMITTED"}
        )
        assert response.status_code == 200
        timestamps.append(response.json()["submitted_at"])
        assert upload(client, data, submission).status_code == 409
        review = client.post(
            f"{url}/review",
            headers=headers(data, "instructor"),
            json={
                "feedback_text": f"Review {attempt}",
                "grade": 80 if attempt else 40,
                "status_transition": "APPROVED" if attempt else "CHANGES_REQUIRED",
            },
        )
        assert review.status_code == 200
    detail = client.get(url, headers=headers(data)).json()
    assert [attempt["submitted_at"] for attempt in detail["attempts"]] == timestamps
    assert [review["status_transition"] for review in detail["reviews"]] == [
        "CHANGES_REQUIRED",
        "APPROVED",
    ]
    assert detail["grade"] == 80
    assert (
        client.get(
            f"{url}/files/{record['id']}/download", headers=headers(data)
        ).content
        == b"private work"
    )
    own = client.get(
        f"{URL}/me",
        headers=headers(data),
        params={"assignment_id": submission.assignment_id, "limit": 1},
    ).json()
    assert [item["id"] for item in own] == [submission.id]
    db_session.delete(submission)
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(SubmissionAttempt)) == 0
