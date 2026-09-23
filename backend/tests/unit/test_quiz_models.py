from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.quiz import Question, Quiz, QuizQuestion
from app.models.track import Lesson, Track, TrackModule


def _create_learning_scope(db_session):
    track = Track(
        name="Quiz Model Track",
        slug="quiz-model-track",
        description="Quiz model test track",
        ordering=1,
    )
    db_session.add(track)
    db_session.flush()

    module = TrackModule(
        track_id=track.id,
        title="Assessment Module",
        description="Quiz model test module",
        ordering=1,
    )
    db_session.add(module)
    db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        title="Assessment Lesson",
        content="Quiz model test lesson",
        ordering=1,
    )
    db_session.add(lesson)
    db_session.flush()

    return track, module, lesson


def test_quiz_creation_and_relationships(db_session):
    track, _, lesson = _create_learning_scope(db_session)

    question = Question(
        track_id=track.id,
        lesson_id=lesson.id,
        text="What is Python?",
        question_type="MULTIPLE_CHOICE",
        difficulty=2,
        points=5,
    )

    quiz = Quiz(
        track_id=track.id,
        lesson_id=lesson.id,
        title="Python Fundamentals Quiz",
        description="Assessment for the Python fundamentals lesson.",
        passing_score=70,
        time_limit_minutes=20,
        is_active=True,
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

    assert quiz.id is not None
    assert quiz.track_id == track.id
    assert quiz.lesson_id == lesson.id
    assert quiz.title == "Python Fundamentals Quiz"
    assert quiz.passing_score == 70
    assert quiz.time_limit_minutes == 20
    assert quiz.is_active is True

    assert quiz.track is not None
    assert quiz.track.id == track.id

    assert quiz.lesson is not None
    assert quiz.lesson.id == lesson.id

    assert quiz in track.quizzes
    assert quiz in lesson.quizzes

    assert len(quiz.question_links) == 1

    link = quiz.question_links[0]
    assert link.quiz_id == quiz.id
    assert link.question_id == question.id
    assert link.ordering == 1
    assert link.question.id == question.id
    assert link.question.quiz_questions[0].quiz.id == quiz.id


def test_quiz_defaults(db_session):
    track, _, _ = _create_learning_scope(db_session)

    quiz = Quiz(
        track_id=track.id,
        title="Default Quiz",
        passing_score=75,
    )

    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    assert quiz.id is not None
    assert quiz.track_id == track.id
    assert quiz.passing_score == 75
    assert quiz.time_limit_minutes is None
    assert quiz.is_active is True


def test_quiz_question_unique_constraint(db_session):
    track, _, lesson = _create_learning_scope(db_session)

    question = Question(
        track_id=track.id,
        lesson_id=lesson.id,
        text="Duplicate link test",
        question_type="TRUE_FALSE",
    )

    quiz = Quiz(
        track_id=track.id,
        lesson_id=lesson.id,
        title="Unique Link Quiz",
        passing_score=70,
    )

    db_session.add_all([question, quiz])
    db_session.commit()

    db_session.add(
        QuizQuestion(
            quiz_id=quiz.id,
            question_id=question.id,
            ordering=1,
        )
    )
    db_session.commit()

    duplicate = QuizQuestion(
        quiz_id=quiz.id,
        question_id=question.id,
        ordering=2,
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(duplicate)
            db_session.flush()
