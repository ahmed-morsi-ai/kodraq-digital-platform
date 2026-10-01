from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.crud.crud_quiz_attempt import quiz_attempt as attempts
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, Question, QuestionOption, QuizQuestion
from app.models.quiz_attempt import QuizAttempt
from app.models.role import Role
from app.models.track import Track, TrackModule, Lesson
from app.models.track_instructor import TrackInstructor
from app.models.user import User
from app.schemas.quiz_attempt import QuizAttemptSubmit


def seed(db):
    tag = uuid4().hex
    roles = {}
    for name in ("student", "instructor", "admin", "employee"):
        roles[name] = db.scalar(select(Role).where(Role.name == name))
        if roles[name] is None:
            roles[name] = Role(name=name)
            db.add(roles[name])
    users = {}
    for name, role in (
        ("owner", "student"),
        ("other", "student"),
        ("outsider", "student"),
        ("instructor", "instructor"),
        ("foreign", "instructor"),
        ("admin", "admin"),
        ("employee", "employee"),
    ):
        users[name] = User(
            email=f"{name}-{tag}@example.com",
            full_name=name,
            hashed_password="unused",
            role_rel=roles[role],
            is_active=True,
        )
        db.add(users[name])
    tracks = [Track(name=f"Quiz {tag} {i}", slug=f"quiz-{tag}-{i}") for i in range(2)]
    db.add_all(tracks)
    db.flush()
    module = TrackModule(title="Module", track_id=tracks[0].id)
    db.add(module)
    db.flush()
    lesson = Lesson(title="Lesson", module_id=module.id)
    db.add(lesson)
    db.flush()
    for name in ("owner", "other"):
        db.add(
            Enrollment(
                user_id=users[name].id,
                track_id=tracks[0].id,
                status="active",
                enrolled_at=datetime.now(UTC),
            )
        )
    db.add_all(
        [
            TrackInstructor(
                track_id=tracks[0].id, instructor_id=users["instructor"].id
            ),
            TrackInstructor(track_id=tracks[1].id, instructor_id=users["foreign"].id),
        ]
    )
    questions = [
        Question(
            track_id=tracks[0].id,
            text=f"Question {i}",
            question_type="TRUE_FALSE" if i == 0 else "MULTIPLE_CHOICE",
            points=weight,
            difficulty=1,
            options=[
                QuestionOption(text="Right", is_correct=True),
                QuestionOption(text="Wrong", is_correct=False),
            ],
        )
        for i, weight in enumerate((2, 1))
    ]
    quiz = Quiz(
        title="Weighted Quiz",
        track_id=tracks[0].id,
        passing_score=67,
        time_limit_minutes=10,
        question_links=[
            QuizQuestion(question=q, ordering=i) for i, q in enumerate(questions)
        ],
    )
    db.add(quiz)
    db.commit()
    return SimpleNamespace(
        users=users,
        tracks=tracks,
        module=module,
        lesson=lesson,
        quiz=quiz,
        questions=questions,
    )


@pytest.fixture
def data(db_session):
    return seed(db_session)


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def start(client, data):
    response = client.post(
        f"/api/v1/quizzes/{data.quiz.id}/attempts", headers=headers(data.users["owner"])
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def answers(data, selections=(0, 0)):
    return {
        "answers": [
            {
                "question_id": q.id,
                "selected_option_id": q.options[choice].id
                if choice is not None
                else None,
            }
            for q, choice in zip(data.questions, selections, strict=True)
        ]
    }


def submit(client, data, attempt_id, payload=None):
    return client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=headers(data.users["owner"]),
        json=payload if payload is not None else answers(data),
    )


@pytest.mark.parametrize("scope", ["track", "module", "lesson"])
@pytest.mark.parametrize("completed", [False, True])
@pytest.mark.parametrize("endpoint", ["list", "read", "results"])
def test_instructor_isolation_all_attempt_reads(
    client, db_session, data, scope, completed, endpoint
):
    if scope != "track":
        data.quiz.track_id = None
        setattr(data.quiz, f"{scope}_id", getattr(data, scope).id)
        db_session.commit()
    attempt_id = start(client, data)
    if completed:
        assert submit(client, data, attempt_id).status_code == 200
    path = (
        f"/api/v1/quizzes/{data.quiz.id}/attempts"
        if endpoint == "list"
        else f"/api/v1/quiz-attempts/{attempt_id}"
        + ("/results" if endpoint == "results" else "")
    )
    assert client.get(path, headers=headers(data.users["foreign"])).status_code == 403
    expected = 400 if endpoint == "results" and not completed else 200
    for name in ("instructor", "admin"):
        assert (
            client.get(path, headers=headers(data.users[name])).status_code == expected
        )


@pytest.mark.parametrize(
    "name", ["instructor", "foreign", "admin", "employee", "outsider"]
)
def test_start_requires_enrolled_student(client, data, name):
    assert (
        client.post(
            f"/api/v1/quizzes/{data.quiz.id}/attempts",
            headers=headers(data.users[name]),
        ).status_code
        == 403
    )


@pytest.mark.parametrize("name", ["other", "outsider", "employee"])
@pytest.mark.parametrize("endpoint", ["read", "results", "submit"])
def test_only_owner_can_use_attempt(client, data, name, endpoint):
    attempt_id = start(client, data)
    path = f"/api/v1/quiz-attempts/{attempt_id}"
    if endpoint == "submit":
        response = client.post(
            path + "/submit", headers=headers(data.users[name]), json=answers(data)
        )
    else:
        response = client.get(
            path + ("/results" if endpoint == "results" else ""),
            headers=headers(data.users[name]),
        )
    assert response.status_code == 403


def test_promoted_instructor_cannot_bypass_track_check_as_old_owner(
    client, db_session, data
):
    attempt_id = start(client, data)
    data.users["owner"].role_rel = data.users["instructor"].role_rel
    db_session.commit()
    for path in (
        f"/api/v1/quiz-attempts/{attempt_id}",
        f"/api/v1/quiz-attempts/{attempt_id}/results",
        f"/api/v1/quizzes/{data.quiz.id}/attempts",
    ):
        assert client.get(path, headers=headers(data.users["owner"])).status_code == 403


@pytest.mark.parametrize(
    "selections,score,earned,passed",
    [
        ((0, 0), 100, 3, True),
        ((0, 1), 66.67, 2, False),
        ((1, 0), 33.33, 1, False),
        ((None, None), 0, 0, False),
        ((0, None), 66.67, 2, False),
    ],
)
def test_weighted_math_and_omissions(client, data, selections, score, earned, passed):
    attempt_id = start(client, data)
    payload = answers(data, selections)
    payload["answers"] = [
        a for a in payload["answers"] if a["selected_option_id"] is not None
    ]
    response = submit(client, data, attempt_id, payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["score"], body["passed"], body["status"]) == (
        score,
        passed,
        "COMPLETED",
    )
    assert len(body["answers"]) == 2
    result = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}/results",
        headers=headers(data.users["owner"]),
    ).json()
    assert (result["percentage"], result["earned_points"], result["max_score"]) == (
        score,
        earned,
        3,
    )
    assert result["questions"][0]["question_text"] == "Question 0"


def test_rounding_does_not_turn_below_threshold_into_pass(client, db_session, data):
    data.questions[0].points = 99999
    data.questions[1].points = 1
    data.quiz.passing_score = 100
    db_session.commit()
    response = submit(client, data, start(client, data), answers(data, (0, 1)))
    assert response.status_code == 200
    assert response.json()["score"] == 100
    assert response.json()["passed"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", 100),
        ("passed", True),
        ("status", "COMPLETED"),
        ("user_id", 1),
        ("completed_at", "2026-01-01"),
        ("is_flagged", "false"),
    ],
)
def test_client_cannot_supply_grade_or_status(client, data, field, value):
    attempt_id = start(client, data)
    response = submit(client, data, attempt_id, answers(data) | {field: value})
    assert response.status_code == 422
    assert (
        client.get(
            f"/api/v1/quiz-attempts/{attempt_id}", headers=headers(data.users["owner"])
        ).json()["status"]
        == "IN_PROGRESS"
    )


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate",
        "foreign_question",
        "foreign_option",
        "missing_option",
        "answer_grade",
    ],
)
def test_invalid_answers_are_atomic(client, db_session, data, kind):
    attempt_id = start(client, data)
    payload = answers(data)
    if kind == "duplicate":
        payload["answers"].append(payload["answers"][0])
    elif kind == "foreign_question":
        payload["answers"][0]["question_id"] = 999999
    elif kind == "foreign_option":
        payload["answers"][0]["selected_option_id"] = data.questions[1].options[0].id
    elif kind == "missing_option":
        payload["answers"][1]["selected_option_id"] = 999999
    else:
        payload["answers"][0]["is_correct"] = True
    response = submit(client, data, attempt_id, payload)
    assert response.status_code == (422 if kind == "answer_grade" else 400)
    record = db_session.get(QuizAttempt, attempt_id)
    assert record.status == "IN_PROGRESS" and record.score is None
    assert record.answers == [] and record.result_snapshot is None


@pytest.mark.parametrize(
    "corruption", ["empty", "no_correct", "two_correct", "unsupported", "one_option"]
)
def test_ungradable_papers_cannot_start(client, db_session, data, corruption):
    if corruption == "empty":
        data.quiz.question_links = []
    elif corruption == "no_correct":
        data.questions[0].options[0].is_correct = False
    elif corruption == "two_correct":
        data.questions[0].options[1].is_correct = True
    elif corruption == "unsupported":
        data.questions[0].question_type = "ESSAY"
    else:
        data.questions[0].options.pop()
    db_session.commit()
    assert (
        client.post(
            f"/api/v1/quizzes/{data.quiz.id}/attempts",
            headers=headers(data.users["owner"]),
        ).status_code
        == 400
    )
    assert (
        db_session.scalar(
            select(QuizAttempt.id).where(QuizAttempt.quiz_id == data.quiz.id)
        )
        is None
    )


def test_deadline_and_threshold_are_fixed_at_start(client, db_session, data):
    attempt_id = start(client, data)
    attempt = db_session.get(QuizAttempt, attempt_id)
    deadline = attempt.deadline_at
    assert deadline - attempt.started_at == timedelta(minutes=10)
    data.quiz.passing_score, data.quiz.time_limit_minutes = 0, 1
    db_session.commit()
    response = submit(client, data, attempt_id, answers(data, (0, 1)))
    assert response.status_code == 200
    assert response.json()["passed"] is False
    assert db_session.get(QuizAttempt, attempt_id).deadline_at == deadline


def test_expiry_is_enforced_without_client_flag_and_results_remain_readable(
    client, db_session, data
):
    attempt_id = start(client, data)
    db_session.get(QuizAttempt, attempt_id).deadline_at = datetime.now(UTC) - timedelta(
        seconds=1
    )
    db_session.commit()
    assert submit(client, data, attempt_id).status_code == 400
    result = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}/results",
        headers=headers(data.users["owner"]),
    ).json()
    assert (result["score"], result["passed"], result["flag_reason"]) == (
        0,
        False,
        "TIME_LIMIT_EXCEEDED",
    )


@pytest.mark.parametrize("change", ["text", "options", "weight", "delete"])
def test_completed_result_is_immutable_after_bank_edit(
    client, db_session, data, change
):
    attempt_id = start(client, data)
    assert submit(client, data, attempt_id).status_code == 200
    path = f"/api/v1/quiz-attempts/{attempt_id}/results"
    before = client.get(path, headers=headers(data.users["owner"])).json()
    question = data.questions[0]
    if change == "text":
        question.text = "Edited question"
    elif change == "options":
        question.options = [
            QuestionOption(text="New answer", is_correct=True),
            QuestionOption(text="Other", is_correct=False),
        ]
    elif change == "weight":
        question.points = 500
    else:
        db_session.delete(question)
    db_session.commit()
    assert client.get(path, headers=headers(data.users["owner"])).json() == before


def test_resume_and_scoped_pagination(client, db_session, data):
    attempt_id = start(client, data)
    assert start(client, data) == attempt_id
    assert submit(client, data, attempt_id).status_code == 200
    newer = start(client, data)
    other = client.post(
        f"/api/v1/quizzes/{data.quiz.id}/attempts", headers=headers(data.users["other"])
    )
    assert other.status_code == 201
    response = client.get(
        f"/api/v1/quizzes/{data.quiz.id}/attempts?limit=1",
        headers=headers(data.users["owner"]),
    )
    assert [item["id"] for item in response.json()] == [newer]
    response = client.get(
        f"/api/v1/quizzes/{data.quiz.id}/attempts?skip=1&limit=1",
        headers=headers(data.users["owner"]),
    )
    assert [item["id"] for item in response.json()] == [attempt_id]


@pytest.mark.parametrize(
    "kind", ["withdrawn", "unscoped", "cross_question", "inactive", "inconsistent"]
)
def test_discovery_and_start_respect_current_access(client, db_session, data, kind):
    expected = 403
    if kind == "withdrawn":
        db_session.scalar(
            select(Enrollment).where(Enrollment.user_id == data.users["owner"].id)
        ).status = "cancelled"
    elif kind == "unscoped":
        data.quiz.track_id = None
    elif kind == "cross_question":
        data.questions[0].track_id = data.tracks[1].id
    elif kind == "inactive":
        data.quiz.is_active = False
        expected = 404
    else:
        data.quiz.track_id = data.tracks[1].id
        data.quiz.module_id = data.module.id
    db_session.commit()
    for verb, suffix in (("get", ""), ("post", "/attempts")):
        assert (
            getattr(client, verb)(
                f"/api/v1/quizzes/{data.quiz.id}{suffix}",
                headers=headers(data.users["owner"]),
            ).status_code
            == expected
        )


def test_historical_owner_results_survive_withdrawal_but_no_new_submission(
    client, db_session, data
):
    attempt_id = start(client, data)
    assert submit(client, data, attempt_id).status_code == 200
    pending = start(client, data)
    db_session.scalar(
        select(Enrollment).where(Enrollment.user_id == data.users["owner"].id)
    ).status = "cancelled"
    db_session.commit()
    assert (
        client.get(
            f"/api/v1/quiz-attempts/{attempt_id}/results",
            headers=headers(data.users["owner"]),
        ).status_code
        == 200
    )
    assert submit(client, data, pending).status_code == 403


def test_discovery_filters_before_pagination_and_never_exposes_answers(
    client, db_session, data
):
    data.quiz.is_active = False
    quiz = Quiz(
        title="Visible",
        lesson_id=data.lesson.id,
        passing_score=70,
        question_links=[QuizQuestion(question=data.questions[0], ordering=0)],
    )
    db_session.add(quiz)
    db_session.commit()
    for params in (
        {"track_id": data.tracks[0].id},
        {"module_id": data.module.id},
        {"lesson_id": data.lesson.id},
    ):
        response = client.get(
            "/api/v1/quizzes",
            params=params | {"limit": 1},
            headers=headers(data.users["owner"]),
        )
        assert response.status_code == 200, response.text
        assert [item["id"] for item in response.json()] == [quiz.id]
        assert (
            "is_correct" not in response.text and "result_snapshot" not in response.text
        )
    assert (
        client.get(
            "/api/v1/quizzes",
            params={"track_id": data.tracks[1].id},
            headers=headers(data.users["owner"]),
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/quizzes/999999",
        "/api/v1/quizzes/999999/attempts",
        "/api/v1/quiz-attempts/999999",
        "/api/v1/quiz-attempts/999999/results",
    ],
)
def test_missing_records(client, data, path):
    assert client.get(path, headers=headers(data.users["owner"])).status_code == 404


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101", "track_id=0"])
def test_http_pagination_validation(client, data, query):
    assert (
        client.get(
            f"/api/v1/quizzes?{query}", headers=headers(data.users["owner"])
        ).status_code
        == 422
    )


def test_failed_commit_rolls_back_grade_and_answers(db_session, data, monkeypatch):
    attempt = attempts.create_for_user(
        db_session, quiz_id=data.quiz.id, actor=data.users["owner"]
    )
    attempt_id = attempt.id
    # Isolate the rollback from this test's outer fixture transaction.
    with Session(
        bind=db_session.connection(), join_transaction_mode="create_savepoint"
    ) as isolated:
        actor = isolated.get(User, data.users["owner"].id)

        def fail_commit():
            isolated.flush()
            raise RuntimeError("Simulated commit failure")

        monkeypatch.setattr(isolated, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="Simulated"):
            attempts.submit(
                isolated,
                attempt_id=attempt_id,
                actor=actor,
                obj_in=QuizAttemptSubmit(**answers(data)),
            )
    db_session.expire_all()
    record = db_session.get(QuizAttempt, attempt_id)
    assert (
        record.status == "IN_PROGRESS" and record.score is None and record.answers == []
    )


@pytest.mark.parametrize("operation", ["start", "submit"])
def test_concurrent_requests_cannot_duplicate_or_regrade_attempt(
    test_engine, operation
):
    with Session(test_engine) as db:
        existing_role_ids = set(db.scalars(select(Role.id)))
        data = seed(db)
        created_role_ids = set(db.scalars(select(Role.id))) - existing_role_ids
        quiz_id, user_id = data.quiz.id, data.users["owner"].id
        user_ids, track_ids = (
            [u.id for u in data.users.values()],
            [t.id for t in data.tracks],
        )
        question_ids = [q.id for q in data.questions]
        payloads = [answers(data), answers(data, (1, 1))]
        attempt_id = (
            attempts.create_for_user(db, quiz_id=quiz_id, actor=data.users["owner"]).id
            if operation == "submit"
            else None
        )
    barrier = Barrier(2)

    def execute(index):
        with Session(test_engine) as db:
            actor = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                if operation == "start":
                    return attempts.create_for_user(db, quiz_id=quiz_id, actor=actor).id
                return attempts.submit(
                    db,
                    attempt_id=attempt_id,
                    actor=actor,
                    obj_in=QuizAttemptSubmit(**payloads[index]),
                ).score
            except ValueError as error:
                return str(error)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, (0, 1)))
        with Session(test_engine) as db:
            records = db.scalars(
                select(QuizAttempt).where(QuizAttempt.quiz_id == quiz_id)
            ).all()
            assert len(records) == 1
            if operation == "start":
                assert results == [records[0].id, records[0].id]
            else:
                assert sum(isinstance(value, str) for value in results) == 1
                assert "Quiz attempt has already been completed." in results
                assert records[0].score in results
                assert len(records[0].answers) == 2
                assert records[0].result_snapshot["score"] == records[0].score
    finally:
        with Session(test_engine) as db:
            db.execute(delete(Quiz).where(Quiz.id == quiz_id))
            db.execute(delete(Question).where(Question.id.in_(question_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.execute(delete(Track).where(Track.id.in_(track_ids)))
            db.execute(delete(Role).where(Role.id.in_(created_role_ids)))
            db.commit()


def test_legacy_results_freeze_existing_grade_on_first_authorized_read(
    client, db_session, data
):
    attempt_id = start(client, data)
    assert submit(client, data, attempt_id).status_code == 200
    attempt = db_session.get(QuizAttempt, attempt_id)
    attempt.result_snapshot = None
    attempt.score = 80
    db_session.commit()
    path = f"/api/v1/quiz-attempts/{attempt_id}/results"
    assert client.get(path, headers=headers(data.users["foreign"])).status_code == 403
    assert attempt.result_snapshot is None
    body = client.get(path, headers=headers(data.users["owner"])).json()
    assert body["score"] == 80
    data.questions[0].text = "Changed after first legacy read"
    db_session.commit()
    assert client.get(path, headers=headers(data.users["owner"])).json() == body


def test_server_flag_cannot_be_cleared_by_student(client, db_session, data):
    attempt_id = start(client, data)
    record = db_session.get(QuizAttempt, attempt_id)
    record.is_flagged, record.flag_reason = True, "EXISTING_FLAG"
    db_session.commit()
    response = submit(client, data, attempt_id, answers(data) | {"is_flagged": False})
    assert response.status_code == 200
    assert (
        response.json()["score"],
        response.json()["is_flagged"],
        response.json()["flag_reason"],
    ) == (0, True, "EXISTING_FLAG")


@pytest.mark.parametrize("operation", ["update", "remove", "get_multi"])
def test_generic_crud_paths_cannot_bypass_scoring_and_scope(db_session, operation):
    with pytest.raises(PermissionError):
        getattr(attempts, operation)(db_session)
