from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import status

from app.crud.crud_user import user as crud_user
from tests.quiz_helpers import create_user_and_get_token as _create_user_and_get_token
from tests.quiz_helpers import create_quiz as _create_quiz


def test_student_can_start_quiz_attempt(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-student@example.com",
        full_name="Attempt Student",
    )
    quiz = _create_quiz(db_session)

    response = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()

    assert body["quiz_id"] == quiz.id
    assert body["status"] == "IN_PROGRESS"
    assert body["score"] is None
    assert body["passed"] is False
    assert body["completed_at"] is None
    assert body["answers"] == []


def test_attempt_owner_is_required_for_read_and_submit(client, db_session):
    owner = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-owner@example.com",
        full_name="Attempt Owner",
    )
    other_student = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-other@example.com",
        full_name="Other Student",
    )
    quiz = _create_quiz(db_session)

    started = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=owner,
    )
    assert started.status_code == status.HTTP_201_CREATED
    attempt_id = started.json()["id"]

    read_by_other = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}",
        headers=other_student,
    )
    assert read_by_other.status_code == status.HTTP_403_FORBIDDEN

    submit_by_other = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=other_student,
        json={
            "answers": [
                {
                    "question_id": quiz.question_links[0].question_id,
                    "selected_option_id": (
                        quiz.question_links[0].question.options[0].id
                    ),
                }
            ]
        },
    )
    assert submit_by_other.status_code == status.HTTP_403_FORBIDDEN


def test_assigned_instructor_can_list_all_quiz_attempts(client, db_session):
    student_one = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-list-student-one@example.com",
        full_name="Attempt List Student One",
    )
    student_two = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-list-student-two@example.com",
        full_name="Attempt List Student Two",
    )
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-list-instructor@example.com",
        full_name="Attempt List Instructor",
        role_name="instructor",
    )
    quiz = _create_quiz(db_session)

    from app.models.track_instructor import TrackInstructor

    manager = crud_user.get_by_email(
        db_session, email="attempt-list-instructor@example.com"
    )
    db_session.add(TrackInstructor(track_id=quiz.track_id, instructor_id=manager.id))
    db_session.commit()

    first = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student_one,
    )
    second = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student_two,
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED

    response = client.get(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=instructor,
    )

    assert response.status_code == status.HTTP_200_OK
    attempt_ids = {item["id"] for item in response.json()}
    assert {first.json()["id"], second.json()["id"]}.issubset(attempt_ids)


def test_submit_completes_attempt_and_locks_it(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-submit-student@example.com",
        full_name="Attempt Submit Student",
    )
    quiz = _create_quiz(db_session)

    started = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student,
    )
    assert started.status_code == status.HTTP_201_CREATED

    attempt_id = started.json()["id"]
    question = quiz.question_links[0].question
    correct_option = next(option for option in question.options if option.is_correct)

    submitted = client.post(
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

    assert submitted.status_code == status.HTTP_200_OK
    body = submitted.json()

    assert body["status"] == "COMPLETED"
    assert body["score"] == 100.0
    assert body["passed"] is True
    assert body["completed_at"] is not None
    assert len(body["answers"]) == 1
    assert body["answers"][0]["is_correct"] is True

    second_submit = client.post(
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

    assert second_submit.status_code == status.HTTP_400_BAD_REQUEST


def test_expired_attempt_cannot_be_submitted(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="attempt-expired-student@example.com",
        full_name="Attempt Expired Student",
    )
    quiz = _create_quiz(db_session, time_limit_minutes=10)

    started = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student,
    )
    assert started.status_code == status.HTTP_201_CREATED
    attempt_id = started.json()["id"]

    from app.models.quiz_attempt import QuizAttempt

    attempt = db_session.get(QuizAttempt, attempt_id)
    assert attempt is not None

    attempt.started_at = datetime.now(UTC) - timedelta(minutes=11)
    attempt.deadline_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    question = quiz.question_links[0].question
    correct_option = next(option for option in question.options if option.is_correct)

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
