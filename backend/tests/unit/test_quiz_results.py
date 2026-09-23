from __future__ import annotations

from fastapi import status

from app.crud.crud_user import user as crud_user
from app.models.quiz import Question, QuestionOption, Quiz, QuizQuestion
from app.models.role import Role
from app.models.track import Track
from app.models.track_instructor import TrackInstructor
from app.schemas.user import UserCreate


def _create_user_and_get_token(
    client,
    db_session,
    *,
    email: str,
    full_name: str,
    role_name: str | None = None,
    is_superuser: bool = False,
) -> dict[str, str]:
    role_id = None

    if role_name:
        role = db_session.query(Role).filter(Role.name == role_name).first()
        if role is None:
            role = Role(name=role_name, description=f"{role_name} role")
            db_session.add(role)
            db_session.flush()
        role_id = role.id

    crud_user.create(
        db_session,
        obj_in=UserCreate(
            email=email,
            password="Password123!",
            full_name=full_name,
            role_id=role_id,
            is_superuser=is_superuser,
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


def _create_track(
    db_session,
    *,
    name: str,
    slug: str,
) -> Track:
    track = Track(
        name=name,
        slug=slug,
        description=f"{name} description",
    )
    db_session.add(track)
    db_session.flush()
    return track


def _assign_instructor(
    db_session,
    *,
    instructor_email: str,
    track_id: int,
) -> None:
    instructor = crud_user.get_by_email(
        db_session,
        email=instructor_email,
    )
    assert instructor is not None

    db_session.add(
        TrackInstructor(
            track_id=track_id,
            instructor_id=instructor.id,
        )
    )
    db_session.commit()


def _create_quiz(
    db_session,
    *,
    track_id: int,
) -> Quiz:
    quiz = Quiz(
        title="Results Quiz",
        description="TASK-5.3.6 results integration test.",
        track_id=track_id,
        passing_score=50,
        time_limit_minutes=30,
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


def _complete_attempt(
    client,
    student_headers,
    quiz: Quiz,
) -> int:
    started = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student_headers,
    )
    assert started.status_code == status.HTTP_201_CREATED

    attempt_id = started.json()["id"]
    question = quiz.question_links[0].question
    correct_option = next(
        option for option in question.options if option.is_correct
    )

    submitted = client.post(
        f"/api/v1/quiz-attempts/{attempt_id}/submit",
        headers=student_headers,
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

    return attempt_id


def test_student_can_view_own_completed_quiz_result(client, db_session):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="results-own-student@example.com",
        full_name="Results Own Student",
    )
    track = _create_track(
        db_session,
        name="Results Own Track",
        slug="results-own-track",
    )
    db_session.commit()

    quiz = _create_quiz(db_session, track_id=track.id)
    attempt_id = _complete_attempt(client, student, quiz)

    response = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}/results",
        headers=student,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    assert body["attempt_id"] == attempt_id
    assert body["quiz_id"] == quiz.id
    assert body["score"] == 100.0
    assert body["max_score"] == 10
    assert body["percentage"] == 100.0
    assert body["passed"] is True
    assert body["time_taken_seconds"] >= 0
    assert body["is_flagged"] is False
    assert body["flag_reason"] is None

    assert len(body["questions"]) == 1
    item = body["questions"][0]
    question = quiz.question_links[0].question
    correct_option = next(
        option for option in question.options if option.is_correct
    )

    assert item["question_id"] == question.id
    assert item["question_text"] == question.text
    assert item["points"] == 10
    assert item["selected_option_id"] == correct_option.id
    assert item["selected_option_text"] == correct_option.text
    assert item["correct_option_ids"] == [correct_option.id]
    assert item["correct_option_texts"] == [correct_option.text]
    assert item["is_correct"] is True


def test_student_cannot_view_another_students_quiz_result(
    client,
    db_session,
):
    owner = _create_user_and_get_token(
        client,
        db_session,
        email="results-owner@example.com",
        full_name="Results Owner",
    )
    other_student = _create_user_and_get_token(
        client,
        db_session,
        email="results-other@example.com",
        full_name="Results Other",
    )
    track = _create_track(
        db_session,
        name="Results Ownership Track",
        slug="results-ownership-track",
    )
    db_session.commit()

    quiz = _create_quiz(db_session, track_id=track.id)
    attempt_id = _complete_attempt(client, owner, quiz)

    response = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}/results",
        headers=other_student,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_instructor_can_view_only_assigned_track_results(
    client,
    db_session,
):
    instructor = _create_user_and_get_token(
        client,
        db_session,
        email="results-instructor@example.com",
        full_name="Results Instructor",
        role_name="instructor",
    )
    student = _create_user_and_get_token(
        client,
        db_session,
        email="results-instructor-student@example.com",
        full_name="Results Instructor Student",
    )
    assigned_track = _create_track(
        db_session,
        name="Results Assigned Track",
        slug="results-assigned-track",
    )
    other_track = _create_track(
        db_session,
        name="Results Other Track",
        slug="results-other-track",
    )
    db_session.commit()

    _assign_instructor(
        db_session,
        instructor_email="results-instructor@example.com",
        track_id=assigned_track.id,
    )

    allowed_quiz = _create_quiz(
        db_session,
        track_id=assigned_track.id,
    )
    denied_quiz = _create_quiz(
        db_session,
        track_id=other_track.id,
    )

    allowed_attempt_id = _complete_attempt(
        client,
        student,
        allowed_quiz,
    )
    denied_attempt_id = _complete_attempt(
        client,
        student,
        denied_quiz,
    )

    allowed = client.get(
        f"/api/v1/quiz-attempts/{allowed_attempt_id}/results",
        headers=instructor,
    )
    assert allowed.status_code == status.HTTP_200_OK

    denied = client.get(
        f"/api/v1/quiz-attempts/{denied_attempt_id}/results",
        headers=instructor,
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN


def test_in_progress_attempt_does_not_expose_full_results(
    client,
    db_session,
):
    student = _create_user_and_get_token(
        client,
        db_session,
        email="results-progress@example.com",
        full_name="Results Progress Student",
    )
    track = _create_track(
        db_session,
        name="Results Progress Track",
        slug="results-progress-track",
    )
    db_session.commit()

    quiz = _create_quiz(db_session, track_id=track.id)

    started = client.post(
        f"/api/v1/quizzes/{quiz.id}/attempts",
        headers=student,
    )
    assert started.status_code == status.HTTP_201_CREATED

    attempt_id = started.json()["id"]

    response = client.get(
        f"/api/v1/quiz-attempts/{attempt_id}/results",
        headers=student,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
