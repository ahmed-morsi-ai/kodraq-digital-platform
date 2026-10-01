import pytest
from sqlalchemy import func, select

from app.models.graduation import GraduationResult, GraduationRule
from tests.final_project_helpers import headers
from tests.graduation_helpers import seed_graduation


@pytest.fixture
def data(db_session):
    return seed_graduation(db_session)


def status_url(data, student="student"):
    return f"/api/v1/graduation/status?track_id={data.tracks[0].id}&user_id={data.users[student].id}"


def finalize_url(data):
    return f"/api/v1/graduation/finalize/{data.users['student'].id}?track_id={data.tracks[0].id}"


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("student", 200),
        ("other", 403),
        ("outsider", 403),
        ("instructor", 200),
        ("foreign", 403),
        ("admin", 200),
        ("superuser", 200),
        ("employee", 403),
    ],
)
def test_status_read_permissions_and_track_isolation(
    client, db_session, data, actor, expected
):
    response = client.get(status_url(data), headers=headers(data.users[actor]))
    assert response.status_code == expected, response.text
    if expected == 200:
        body = response.json()
        assert body["status"] == "ELIGIBLE" and body["is_eligible"]
        assert body["overall_score"] == 94.5
        assert len(body["gate_checks"]) == 6
        assert body["finalized_result"] is None
    assert db_session.scalar(select(func.count()).select_from(GraduationResult)) == 0
    assert db_session.scalar(select(func.count()).select_from(GraduationRule)) == 0


@pytest.mark.parametrize("action", ["evaluate", "finalize"])
@pytest.mark.parametrize(
    "actor,expected",
    [
        ("student", 403),
        ("other", 403),
        ("instructor", 200),
        ("foreign", 403),
        ("admin", 200),
        ("superuser", 200),
        ("employee", 403),
    ],
)
def test_only_track_managers_may_evaluate_or_finalize(
    client, db_session, data, actor, expected, action
):
    response = client.post(
        f"/api/v1/graduation/{action}/{data.users['student'].id}?track_id={data.tracks[0].id}",
        headers=headers(data.users[actor]),
        json={},
    )
    assert response.status_code == expected, response.text
    persisted = db_session.scalar(select(func.count()).select_from(GraduationResult))
    assert persisted == int(expected == 200 and action == "finalize")
    if expected == 200:
        assert response.json()["status"] == (
            "GRADUATED" if action == "finalize" else "ELIGIBLE"
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "GRADUATED"),
        ("eligible", True),
        ("overall_score", 100),
        ("checks", []),
        ("student_id", 999),
        ("track_id", 999),
        ("finalized_by", 999),
    ],
)
def test_finalization_rejects_client_calculated_or_forged_fields(
    client, db_session, data, field, value
):
    response = client.post(
        finalize_url(data), headers=headers(data.users["admin"]), json={field: value}
    )
    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(GraduationResult)) == 0


def test_failing_one_gate_returns_not_graduated_even_with_high_overall(
    client, db_session, data
):
    data.review.score = 74
    db_session.commit()
    response = client.get(status_url(data), headers=headers(data.users["student"]))
    assert response.status_code == 200
    body = response.json()
    assert body["overall_score"] > 90
    assert body["status"] == "NOT_GRADUATED" and not body["is_eligible"]
    failed = [gate for gate in body["gate_checks"] if not gate["passed"]]
    assert len(failed) == 1 and failed[0]["gate_key"] == "final_project_score"
    assert failed[0]["actual_value"] == 74 and failed[0]["required_value"] == 75
    assert failed[0]["failure_reason"]
    finalized = client.post(
        finalize_url(data), headers=headers(data.users["instructor"])
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "NOT_GRADUATED"
    assert finalized.json()["finalized_at"] is None


def test_student_reads_own_progress_before_any_staff_evaluation(client, data):
    response = client.get(
        f"/api/v1/graduation/status?track_id={data.tracks[0].id}",
        headers=headers(data.users["other"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_GRADUATED"
    assert not response.json()["is_eligible"]


@pytest.mark.parametrize("student", ["outsider", "instructor", "employee"])
def test_cannot_graduate_unenrolled_or_nonstudent_targets(client, data, student):
    response = client.post(
        f"/api/v1/graduation/finalize/{data.users[student].id}?track_id={data.tracks[0].id}",
        headers=headers(data.users["admin"]),
    )
    assert response.status_code == 403


def test_self_finalization_is_rejected(client, data):
    response = client.post(
        f"/api/v1/graduation/finalize/{data.users['instructor'].id}?track_id={data.tracks[0].id}",
        headers=headers(data.users["instructor"]),
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "parameter",
    ["track_id=0", "track_id=-1", "track_id=abc", "user_id=0", "user_id=-1"],
)
def test_positive_ids_are_validated(client, data, parameter):
    query = (
        parameter
        if parameter.startswith("track_id")
        else f"track_id={data.tracks[0].id}&{parameter}"
    )
    assert (
        client.get(
            f"/api/v1/graduation/status?{query}", headers=headers(data.users["student"])
        ).status_code
        == 422
    )


def test_missing_track_is_required_no_unscoped_latest_record_fallback(client, data):
    assert (
        client.get(
            "/api/v1/graduation/status", headers=headers(data.users["instructor"])
        ).status_code
        == 422
    )


def test_missing_student_or_track_returns_404_for_admin(client, data):
    for query in [
        f"track_id={data.tracks[0].id}&user_id=2147483647",
        f"track_id=2147483647&user_id={data.users['student'].id}",
    ]:
        assert (
            client.get(
                f"/api/v1/graduation/status?{query}",
                headers=headers(data.users["admin"]),
            ).status_code
            == 404
        )
    assert (
        client.get(
            "/api/v1/graduation/results/2147483647",
            headers=headers(data.users["admin"]),
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("student", 200),
        ("other", 403),
        ("instructor", 200),
        ("foreign", 403),
        ("admin", 200),
        ("employee", 403),
    ],
)
def test_persisted_result_read_is_owner_or_assigned_manager_only(
    client, data, actor, expected
):
    created = client.post(finalize_url(data), headers=headers(data.users["admin"]))
    assert created.status_code == 200
    response = client.get(
        f"/api/v1/graduation/results/{created.json()['id']}",
        headers=headers(data.users[actor]),
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    "actor,expected",
    [("student", 403), ("instructor", 200), ("foreign", 403), ("admin", 200)],
)
def test_result_list_is_track_scoped_and_paginated(client, data, actor, expected):
    client.post(finalize_url(data), headers=headers(data.users["admin"]))
    response = client.get(
        f"/api/v1/graduation/results?track_id={data.tracks[0].id}&skip=0&limit=1",
        headers=headers(data.users[actor]),
    )
    assert response.status_code == expected
    if expected == 200:
        assert len(response.json()) == 1
        assert (
            client.get(
                f"/api/v1/graduation/results?track_id={data.tracks[0].id}&skip=1&limit=1",
                headers=headers(data.users[actor]),
            ).json()
            == []
        )


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "skip=-1"])
def test_invalid_pagination_rejected(client, data, query):
    assert (
        client.get(
            f"/api/v1/graduation/results?track_id={data.tracks[0].id}&{query}",
            headers=headers(data.users["admin"]),
        ).status_code
        == 422
    )


def test_status_reflects_new_grades_and_finalization_is_idempotent(
    client, db_session, data
):
    data.review.score = 74
    db_session.commit()
    assert (
        client.get(status_url(data), headers=headers(data.users["student"])).json()[
            "status"
        ]
        == "NOT_GRADUATED"
    )
    data.review.score = 90
    db_session.commit()
    first = client.post(
        finalize_url(data), headers=headers(data.users["instructor"])
    ).json()
    again = client.post(finalize_url(data), headers=headers(data.users["admin"])).json()
    assert first == again
    status = client.get(status_url(data), headers=headers(data.users["student"])).json()
    assert status["status"] == "GRADUATED"
    assert status["finalized_result"]["id"] == first["id"]
    assert len(status["finalized_result"]["checks"]) == 6


@pytest.mark.parametrize("action", ["status", "finalize"])
def test_inactive_and_unauthenticated_access_rejected(client, db_session, data, action):
    request = client.get if action == "status" else client.post
    url = status_url(data) if action == "status" else finalize_url(data)
    assert request(url).status_code == 401
    data.users["instructor"].is_active = False
    db_session.commit()
    assert request(url, headers=headers(data.users["instructor"])).status_code == 400


def test_existing_certificate_routes_cannot_bypass_track_isolation_or_finalization(
    client, db_session, data
):
    pending = GraduationResult(
        student_id=data.users["student"].id,
        track_id=data.tracks[0].id,
        status="GRADUATED",
        eligible=True,
        overall_score=100,
    )
    db_session.add(pending)
    db_session.commit()
    issue = f"/api/v1/certificates/graduation-results/{pending.id}/issue"
    assert (
        client.post(
            issue, headers=headers(data.users["instructor"]), json={}
        ).status_code
        == 400
    )
    approved = client.post(
        finalize_url(data), headers=headers(data.users["instructor"])
    )
    assert approved.status_code == 200
    assert (
        client.post(issue, headers=headers(data.users["foreign"]), json={}).status_code
        == 403
    )
    assert (
        client.post(issue, headers=headers(data.users["student"]), json={}).status_code
        == 403
    )
    certificate = client.post(issue, headers=headers(data.users["instructor"]), json={})
    assert certificate.status_code == 201, certificate.text
    assert certificate.json()["final_score"] == 94.5
    assert (
        client.get(
            f"/api/v1/certificates/{certificate.json()['id']}",
            headers=headers(data.users["foreign"]),
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/certificates/{certificate.json()['id']}",
            headers=headers(data.users["student"]),
        ).status_code
        == 200
    )


def test_legacy_student_graduate_endpoint_cannot_finalize(client, data):
    assert (
        client.post(
            "/api/v1/graduation/graduate",
            headers=headers(data.users["student"]),
            json={"track_id": data.tracks[0].id},
        ).status_code
        == 404
    )
