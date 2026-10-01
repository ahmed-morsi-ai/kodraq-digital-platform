from __future__ import annotations

from datetime import datetime, timezone

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
    assert assignment.title == "Build a FastAPI API"
    assert assignment.description == "Create a small production-style API."
    assert assignment.instructions == "Implement routes, validation, and error handling."
    assert assignment.created_at is not None
    assert assignment.created_at.tzinfo is not None
    assert assignment.updated_at is not None
    assert assignment.updated_at.tzinfo is not None
    assert assignment.updated_at >= assignment.created_at


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


def _create_curriculum(db_session, suffix):
    track = Track(name=f"Ownership {suffix}", slug=f"ownership-{suffix}")
    module = TrackModule(title=f"Module {suffix}", track=track)
    lesson = Lesson(title=f"Lesson {suffix}", module=module)
    db_session.add_all([track, module, lesson])
    db_session.flush()
    return track, module, lesson


def test_assignment_track_ownership(db_session):
    track_a, module_a, lesson_a = _create_curriculum(db_session, "a")
    track_b, module_b, lesson_b = _create_curriculum(db_session, "b")
    assignment_a = Assignment(
        track=track_a,
        module=module_a,
        lesson=lesson_a,
        title="Track A assignment",
        description="Owned by track A",
        instructions="Complete track A work",
        difficulty="beginner",
    )
    assignment_b = Assignment(
        track=track_b,
        module=module_b,
        lesson=lesson_b,
        title="Track B assignment",
        description="Owned by track B",
        instructions="Complete track B work",
        difficulty="advanced",
    )
    db_session.add_all([assignment_a, assignment_b])
    db_session.commit()
    # Reload from PostgreSQL so ownership is verified beyond the identity map.
    db_session.expire_all()

    assert assignment_a.track is assignment_a.module.track
    assert assignment_a.track is assignment_a.lesson.module.track
    assert assignment_b.track is assignment_b.module.track
    assert assignment_b.track is assignment_b.lesson.module.track
    for owner in (track_a, module_a, lesson_a):
        assert owner.assignments == [assignment_a]
        assert assignment_b not in owner.assignments
    for owner in (track_b, module_b, lesson_b):
        assert owner.assignments == [assignment_b]
        assert assignment_a not in owner.assignments


@pytest.mark.parametrize("context", ["track", "module", "lesson"])
def test_assignment_optional_context_relationships(db_session, context):
    track, module, lesson = _create_curriculum(db_session, context)
    owner = {"track": track, "module": module, "lesson": lesson}[context]
    assignment = Assignment(
        **{context: owner},
        title=f"{context} assignment",
        description="Assignment with a single curriculum context",
        instructions="Complete the work",
        difficulty="beginner",
    )
    db_session.add(assignment)
    db_session.commit()
    db_session.expire_all()

    assert getattr(assignment, context) is owner
    assert owner.assignments == [assignment]
    for other_context in {"track", "module", "lesson"} - {context}:
        assert getattr(assignment, f"{other_context}_id") is None
        assert getattr(assignment, other_context) is None

    if context == "module":
        assert assignment.module.track is track
    elif context == "lesson":
        assert assignment.lesson.module.track is track


@pytest.mark.parametrize("foreign_key", ["track_id", "module_id", "lesson_id"])
def test_assignment_rejects_missing_context(db_session, foreign_key):
    assignment = Assignment(
        **{foreign_key: -1},
        title="Invalid reference",
        description="A nonexistent context must be rejected",
        instructions="Complete the work",
        difficulty="beginner",
    )

    with pytest.raises(IntegrityError) as exc_info:
        with db_session.begin_nested():
            db_session.add(assignment)
            db_session.flush()

    assert exc_info.value.orig.pgcode == "23503"  # PostgreSQL foreign_key_violation.


def test_assignment_update_preserves_creation_timestamp(db_session):
    original_timestamp = datetime(2000, 1, 1, tzinfo=timezone.utc)
    assignment = Assignment(
        title="Original title",
        description="Timestamp update check",
        instructions="Complete the work",
        difficulty="beginner",
        created_at=original_timestamp,
        updated_at=original_timestamp,
    )
    db_session.add(assignment)
    db_session.commit()

    assignment.title = "Updated title"
    db_session.commit()
    db_session.refresh(assignment)

    assert assignment.created_at == original_timestamp
    assert assignment.updated_at > original_timestamp
    assert assignment.updated_at.tzinfo is not None
