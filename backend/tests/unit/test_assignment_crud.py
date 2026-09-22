from __future__ import annotations

from app.crud.crud_assignment import (
    create_assignment,
    delete_assignment,
    get_assignment,
    get_assignments_by_context,
    update_assignment,
)
from app.models.track import Lesson, Track, TrackModule
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


def _create_context(db_session):
    track = Track(
        name="CRUD Test Track",
        slug="crud-test-track",
        description="CRUD test track",
        ordering=1,
    )
    db_session.add(track)
    db_session.flush()

    module = TrackModule(
        track_id=track.id,
        title="CRUD Test Module",
        description="CRUD test module",
        ordering=1,
    )
    db_session.add(module)
    db_session.flush()

    lesson = Lesson(
        module_id=module.id,
        title="CRUD Test Lesson",
        content="CRUD test lesson",
        ordering=1,
    )
    db_session.add(lesson)
    db_session.flush()

    return track, module, lesson


def test_assignment_crud_create_and_get(db_session):
    track, module, lesson = _create_context(db_session)

    payload = AssignmentCreate(
        track_id=track.id,
        module_id=module.id,
        lesson_id=lesson.id,
        title="Create Assignment",
        description="CRUD create test",
        instructions="Create an assignment",
        difficulty="beginner",
        ordering=1,
        is_mandatory=True,
        is_active=True,
    )

    created = create_assignment(db_session, payload)

    assert created.id is not None
    assert created.title == "Create Assignment"
    assert created.track_id == track.id
    assert created.module_id == module.id
    assert created.lesson_id == lesson.id

    fetched = get_assignment(db_session, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Create Assignment"


def test_assignment_crud_update(db_session):
    track, module, lesson = _create_context(db_session)

    payload = AssignmentCreate(
        track_id=track.id,
        module_id=module.id,
        lesson_id=lesson.id,
        title="Original Assignment",
        description="Original description",
        instructions="Original instructions",
        difficulty="beginner",
        ordering=1,
    )

    created = create_assignment(db_session, payload)

    updated = update_assignment(
        db_session,
        created,
        AssignmentUpdate(
            title="Updated Assignment",
            difficulty="advanced",
            ordering=5,
            is_mandatory=False,
        ),
    )

    assert updated.id == created.id
    assert updated.title == "Updated Assignment"
    assert updated.difficulty == "advanced"
    assert updated.ordering == 5
    assert updated.is_mandatory is False
    assert updated.description == "Original description"


def test_assignment_crud_filtering_by_context(db_session):
    track_a, module_a, lesson_a = _create_context(db_session)

    track_b = Track(
        name="Second CRUD Track",
        slug="second-crud-track",
        description="Second CRUD track",
        ordering=2,
    )
    db_session.add(track_b)
    db_session.flush()

    assignment_a = create_assignment(
        db_session,
        AssignmentCreate(
            track_id=track_a.id,
            module_id=module_a.id,
            lesson_id=lesson_a.id,
            title="Track A Assignment",
            description="Track A",
            instructions="Track A",
            difficulty="beginner",
            ordering=1,
        ),
    )

    assignment_b = create_assignment(
        db_session,
        AssignmentCreate(
            track_id=track_b.id,
            title="Track B Assignment",
            description="Track B",
            instructions="Track B",
            difficulty="intermediate",
            ordering=2,
        ),
    )

    track_results = get_assignments_by_context(
        db_session,
        track_id=track_a.id,
    )

    assert [item.id for item in track_results] == [assignment_a.id]
    assert assignment_b.id not in [item.id for item in track_results]

    module_results = get_assignments_by_context(
        db_session,
        module_id=module_a.id,
    )

    assert [item.id for item in module_results] == [assignment_a.id]

    lesson_results = get_assignments_by_context(
        db_session,
        lesson_id=lesson_a.id,
    )

    assert [item.id for item in lesson_results] == [assignment_a.id]


def test_assignment_crud_ordering_and_limit(db_session):
    track, module, lesson = _create_context(db_session)

    first = create_assignment(
        db_session,
        AssignmentCreate(
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
            title="Second",
            description="Second",
            instructions="Second",
            difficulty="beginner",
            ordering=2,
        ),
    )

    second = create_assignment(
        db_session,
        AssignmentCreate(
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
            title="First",
            description="First",
            instructions="First",
            difficulty="beginner",
            ordering=1,
        ),
    )

    results = get_assignments_by_context(
        db_session,
        track_id=track.id,
        limit=1,
    )

    assert len(results) == 1
    assert results[0].id == second.id
    assert results[0].ordering == 1
    assert first.id != second.id


def test_assignment_crud_delete(db_session):
    track, module, lesson = _create_context(db_session)

    created = create_assignment(
        db_session,
        AssignmentCreate(
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
            title="Delete Assignment",
            description="Delete test",
            instructions="Delete test",
            difficulty="beginner",
            ordering=1,
        ),
    )

    deleted = delete_assignment(db_session, created.id)

    assert deleted is not None
    assert deleted.id == created.id

    assert get_assignment(db_session, created.id) is None
