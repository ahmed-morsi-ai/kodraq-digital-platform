from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.assignment import Assignment
from app.models.track import Lesson, Track, TrackModule


def test_assignment_creation_and_relationships(db_session):
    track = Track(
        name="Python Backend Test",
        slug="python-backend-test",
        description="Assignment model test track",
        ordering=1,
    )
    db_session.add(track)
    db_session.flush()

    module = TrackModule(
        track_id=track.id,
        title="FastAPI Fundamentals",
        description="Test module",
        ordering=1,
    )
    db_session.add(module)
    db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        title="Dependency Injection",
        content="Test lesson",
        ordering=1,
    )
    db_session.add(lesson)
    db_session.flush()

    assignment = Assignment(
        track_id=track.id,
        module_id=module.id,
        lesson_id=lesson.id,
        title="Build a FastAPI API",
        description="Create a small production-style API.",
        instructions="Implement routes, validation, and error handling.",
        difficulty="intermediate",
        ordering=3,
        is_mandatory=False,
        is_active=True,
        due_days=7,
        estimated_minutes=90,
        evaluation_config={"type": "manual"},
    )

    db_session.add(assignment)
    db_session.commit()
    db_session.refresh(assignment)

    assert assignment.id is not None
    assert assignment.track_id == track.id
    assert assignment.module_id == module.id
    assert assignment.lesson_id == lesson.id

    assert assignment.track is not None
    assert assignment.track.id == track.id

    assert assignment.module is not None
    assert assignment.module.id == module.id

    assert assignment.lesson is not None
    assert assignment.lesson.id == lesson.id

    assert assignment in track.assignments
    assert assignment in module.assignments
    assert assignment in lesson.assignments

    assert assignment.is_mandatory is False
    assert assignment.is_active is True
    assert assignment.ordering == 3
    assert assignment.difficulty == "intermediate"
    assert assignment.due_days == 7
    assert assignment.estimated_minutes == 90
    assert assignment.evaluation_config == {"type": "manual"}


def test_assignment_difficulty_constraint(db_session):
    assignment = Assignment(
        title="Invalid Difficulty Assignment",
        description="Should fail.",
        instructions="Should fail.",
        difficulty="expert",
        ordering=1,
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(assignment)
            db_session.flush()


def test_assignment_defaults(db_session):
    assignment = Assignment(
        title="Default Values Assignment",
        description="Test defaults.",
        instructions="Test defaults.",
        difficulty="beginner",
    )

    db_session.add(assignment)
    db_session.commit()
    db_session.refresh(assignment)

    assert assignment.ordering == 0
    assert assignment.is_mandatory is True
    assert assignment.is_active is True
