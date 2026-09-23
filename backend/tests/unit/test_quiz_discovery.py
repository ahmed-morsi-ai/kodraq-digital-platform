from __future__ import annotations

from fastapi import status

from app.crud.crud_user import user as crud_user
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.track import Track
from app.schemas.user import UserCreate


def _create_student_and_get_token(client, db_session) -> dict[str, str]:
    email = "quiz-discovery-student@example.com"

    crud_user.create(
        db_session,
        obj_in=UserCreate(
            email=email,
            password="Password123!",
            full_name="Quiz Discovery Student",
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


def _create_quiz(db_session, *, track_id: int | None = None) -> Quiz:
    if track_id is not None:
        track = db_session.get(Track, track_id)

        if track is None:
            track = Track(
                id=track_id,
                name=f"Quiz Discovery Track {track_id}",
                slug=f"quiz-discovery-track-{track_id}",
                description="TASK-5.3.7 discovery integration test track.",
            )
            db_session.add(track)
            db_session.flush()

    quiz = Quiz(
        title="Student Discovery Quiz",
        description="TASK-5.3.7 discovery integration test.",
        track_id=track_id,
        passing_score=70,
        time_limit_minutes=20,
        is_active=True,
    )

    question = Question(
        text="Which answer is correct?",
        question_type="MULTIPLE_CHOICE",
        points=10,
        difficulty=1,
        track_id=track_id,
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


def test_student_can_list_active_quizzes_without_answer_key(
    client,
    db_session,
):
    student = _create_student_and_get_token(client, db_session)
    quiz = _create_quiz(db_session, track_id=101)

    response = client.get(
        "/api/v1/quizzes",
        params={"track_id": quiz.track_id},
        headers=student,
    )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == quiz.id
    assert body[0]["title"] == quiz.title

    option = body[0]["questions"][0]["question"]["options"][0]
    assert option["id"]
    assert option["text"] == "Correct"
    assert "is_correct" not in option


def test_inactive_quiz_is_not_discoverable(client, db_session):
    student = _create_student_and_get_token(client, db_session)
    active_quiz = _create_quiz(db_session, track_id=102)
    inactive_quiz = _create_quiz(db_session, track_id=102)
    inactive_quiz.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/quizzes",
        params={"track_id": active_quiz.track_id},
        headers=student,
    )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    ids = {item["id"] for item in body}

    assert active_quiz.id in ids
    assert inactive_quiz.id not in ids


def test_student_can_read_active_quiz_without_answer_key(
    client,
    db_session,
):
    student = _create_student_and_get_token(client, db_session)
    quiz = _create_quiz(db_session, track_id=103)

    response = client.get(
        f"/api/v1/quizzes/{quiz.id}",
        headers=student,
    )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["id"] == quiz.id
    assert body["passing_score"] == 70
    assert body["questions"][0]["question"]["text"] == (
        "Which answer is correct?"
    )

    options = body["questions"][0]["question"]["options"]
    assert all("is_correct" not in option for option in options)


def test_quiz_discovery_requires_track_or_lesson(
    client,
    db_session,
):
    student = _create_student_and_get_token(client, db_session)

    response = client.get(
        "/api/v1/quizzes",
        headers=student,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == (
        "Quiz discovery requires a track_id or lesson_id."
    )


def test_inactive_quiz_detail_returns_not_found(client, db_session):
    student = _create_student_and_get_token(client, db_session)
    quiz = _create_quiz(db_session, track_id=104)
    quiz.is_active = False
    db_session.commit()

    response = client.get(
        f"/api/v1/quizzes/{quiz.id}",
        headers=student,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Quiz not found"
