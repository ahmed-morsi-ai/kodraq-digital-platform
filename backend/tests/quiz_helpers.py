"""Shared quiz fixtures; enrollment is explicit except in legacy happy-path setup."""

from uuid import uuid4
from sqlalchemy import select
from app.core.security import create_access_token
from app.models.user import User
from app.models.role import Role
from app.models.enrollment import Enrollment
from app.models.track import Track
from app.models.quiz import Quiz, Question, QuestionOption, QuizQuestion


def create_user_and_get_token(
    client, db_session, *, email, full_name, role_name=None, is_superuser=False
):
    del client
    role = None
    if role_name:
        role = db_session.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name)
            db_session.add(role)
            db_session.flush()
    user = User(
        email=email,
        full_name=full_name,
        hashed_password="unused-in-quiz-tests",
        role_rel=role,
        is_active=True,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    db_session.commit()
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def enroll_fixture_students(db_session, track_id):
    """Give existing happy-path test students the enrollment their quiz requires."""
    for user in db_session.scalars(select(User)).all():
        if user.is_superuser or (
            user.role_rel and user.role_rel.name.casefold() != "student"
        ):
            continue
        if (
            db_session.scalar(
                select(Enrollment.id).where(
                    Enrollment.track_id == track_id, Enrollment.user_id == user.id
                )
            )
            is None
        ):
            db_session.add(
                Enrollment(user_id=user.id, track_id=track_id, status="active")
            )
    db_session.flush()


def create_quiz(db_session, *, time_limit_minutes=30, track_id=None):
    if track_id is None:
        track = Track(name="Quiz test track", slug=f"quiz-{uuid4().hex}")
        db_session.add(track)
        db_session.flush()
        track_id = track.id
    enroll_fixture_students(db_session, track_id)
    quiz = Quiz(
        title="Test Quiz",
        track_id=track_id,
        passing_score=50,
        time_limit_minutes=time_limit_minutes,
        is_active=True,
        question_links=[
            QuizQuestion(
                ordering=1,
                question=Question(
                    track_id=track_id,
                    text="Which answer is correct?",
                    question_type="MULTIPLE_CHOICE",
                    points=10,
                    difficulty=1,
                    options=[
                        QuestionOption(text="Correct", is_correct=True),
                        QuestionOption(text="Incorrect", is_correct=False),
                    ],
                ),
            )
        ],
    )
    db_session.add(quiz)
    db_session.commit()
    return quiz
