from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import status

from app.crud.crud_user import user as crud_user
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.quiz_attempt import QuizAttempt
from app.schemas.user import UserCreate


def _create_user_and_get_token(
    client,
    db_session,
    *,
    email: str,
    full_name: str,
) -> dict[str, str]:
    crud_user.create(
        db_session,
        obj_in=UserCreate(
            email=email,
            password="Password123!",
            full_name=full_name,
        ),
    )

    response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": email,
            "password": "Password123!",
        },
    )
    assert response.status_code == status.HTTP_200_OK

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_quiz(
    db_session,
    *,
    time_limit_minutes: int | None = 30,
) -> Quiz:
    quiz = Quiz(
        title="Scoring Engine Quiz",
        description="TASK-5.3.5 scoring and anti-cheat test quiz.",
        passing_score=50,
        time_limit_minutes=time_limit_minutes,
        is_active=True,
    )

    question = Question(
        text="Which answer is correct?",
        question_type="MULTIPLE_CHOICE",
        difficulty=1,
        points=10,
        options=[
            QuestionOption(text="Correct", is_correct=True),
            QuestionOption(text="Incorrect", is_correct=False),
        ],
    )

    quiz.question_links = [
        QuizQuestion(
            question=question,
            ordering=1,
        )
    ]

    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    return quiz


def _start_attempt(client, student, quiz: Quiz) -> int:
    response = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_perfect_score_calculation_and_passed_outcome(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="scoring-perfect@example.com",
        full_name="Scoring Perfect Student",
    )
    quiz = _create_quiz(db_session)
    attempt_id = _start_attempt(client, student, quiz)

    question = quiz.question_links[0].question
    correct_option = next(
        option for option in question.options if option.is_correct
    )

    response = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student,
        json={
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": correct_option.id,
                }
            ]
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    assert body["score"] == 100.0
    assert body["passed"] is True
    assert body["status"] == "COMPLETED"


def test_failing_score_calculation_and_failed_outcome(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="scoring-failed@example.com",
        full_name="Scoring Failed Student",
    )
    quiz = _create_quiz(db_session)
    attempt_id = _start_attempt(client, student, quiz)

    question = quiz.question_links[0].question
    incorrect_option = next(
        option for option in question.options if not option.is_correct
    )

    response = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student,
        json={
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": incorrect_option.id,
                }
            ]
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    assert body["score"] == 0.0
    assert body["passed"] is False
    assert body["status"] == "COMPLETED"


def test_flagged_attempt_is_automatically_failed_and_zero_score(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="scoring-flagged@example.com",
        full_name="Scoring Flagged Student",
    )
    quiz = _create_quiz(db_session)
    attempt_id = _start_attempt(client, student, quiz)

    question = quiz.question_links[0].question
    correct_option = next(
        option for option in question.options if option.is_correct
    )

    response = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student,
        json={
            "is_flagged": True,
            "flag_reason": "TAB_SWITCH",
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": correct_option.id,
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    assert body["score"] == 0.0
    assert body["passed"] is False
    assert body["status"] == "COMPLETED"
    assert body["is_flagged"] is True
    assert body["flag_reason"] == "TAB_SWITCH"


def test_expired_attempt_is_flagged_and_penalized(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="scoring-expired@example.com",
        full_name="Scoring Expired Student",
    )
    quiz = _create_quiz(db_session, time_limit_minutes=10)
    attempt_id = _start_attempt(client, student, quiz)

    attempt = db_session.get(QuizAttempt, attempt_id)
    assert attempt is not None

    attempt.started_at = datetime.now(UTC) - timedelta(minutes=11)
    db_session.commit()

    question = quiz.question_links[0].question
    correct_option = next(
        option for option in question.options if option.is_correct
    )

    response = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student,
        json={
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": correct_option.id,
                }
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    persisted = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}",
        headers=student,
    )
    assert persisted.status_code == status.HTTP_200_OK

    body = persisted.json()
    assert body["status"] == "COMPLETED"
    assert body["score"] == 0.0
    assert body["passed"] is False
    assert body["is_flagged"] is True
    assert body["flag_reason"] == "TIME_LIMIT_EXCEEDED"


def test_completed_attempt_score_cannot_be_tampered(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="scoring-immutable@example.com",
        full_name="Scoring Immutable Student",
    )
    quiz = _create_quiz(db_session)
    attempt_id = _start_attempt(client, student, quiz)

    question = quiz.question_links[0].question
    correct_option = next(
        option for option in question.options if option.is_correct
    )
    incorrect_option = next(
        option for option in question.options if not option.is_correct
    )

    first = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student,
        json={
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": correct_option.id,
                }
            ]
        },
    )

    assert first.status_code == status.HTTP_200_OK
    assert first.json()["score"] == 100.0

    second = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student,
        json={
            "answers": [
                {
                    "question_id": question.id,
                    "selected_option_id": incorrect_option.id,
                }
            ]
        },
    )

    assert second.status_code == status.HTTP_400_BAD_REQUEST

    persisted = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}",
        headers=student,
    )
    assert persisted.status_code == status.HTTP_200_OK

    body = persisted.json()
    assert body["status"] == "COMPLETED"
    assert body["score"] == 100.0
    assert body["passed"] is True
    assert len(body["answers"]) == 1
    assert body["answers"][0]["selected_option_id"] == correct_option.id
