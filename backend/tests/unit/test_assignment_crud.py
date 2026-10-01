from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.crud.crud_assignment import (
    assignment as crud_assignment,
    create_assignment,
    delete_assignment,
    get_assignment,
    get_assignments_by_context,
    update_assignment,
)
from app.models.assignment import Assignment
from app.models.track import Lesson, Track, TrackModule
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
)


def _create_context(db_session, suffix=""):
    track = Track(
        name=f"CRUD Test Track{suffix}",
        slug=f"crud-test-track{suffix}",
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


def _payload(**overrides):
    values = {
        "title": "CRUD contract assignment",
        "description": "Original description",
        "instructions": "Original instructions",
        "difficulty": "beginner",
    }
    values.update(overrides)
    return AssignmentCreate(**values)


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize(
    ("scenario", "error_type", "message"),
    [
        ("missing_track", LookupError, "Track not found"),
        ("missing_module", LookupError, "Track module not found"),
        ("missing_lesson", LookupError, "Lesson not found"),
        ("module_track", ValueError, "module_id does not belong to track_id"),
        ("lesson_module", ValueError, "lesson_id does not belong to module_id"),
        ("lesson_track", ValueError, "lesson_id does not belong to track_id"),
    ],
)
def test_assignment_crud_rejects_invalid_context_without_mutation(
    db_session,
    operation,
    scenario,
    error_type,
    message,
):
    track_a, module_a, lesson_a = _create_context(db_session, "-a")
    track_b, module_b, _ = _create_context(db_session, "-b")
    context = {
        "track_id": track_a.id,
        "module_id": module_a.id,
        "lesson_id": lesson_a.id,
    }
    created = create_assignment(db_session, _payload(**context))
    changes = {
        "missing_track": {"track_id": 999999},
        "missing_module": {"module_id": 999999},
        "missing_lesson": {"lesson_id": 999999},
        "module_track": {"track_id": track_b.id},
        "lesson_module": {"track_id": None, "module_id": module_b.id},
        "lesson_track": {"track_id": track_b.id, "module_id": None},
    }[scenario]
    changes["title"] = "Rejected change"

    with pytest.raises(error_type, match=message):
        if operation == "create":
            create_assignment(db_session, _payload(**(context | changes)))
        else:
            update_assignment(db_session, created, AssignmentUpdate(**changes))

    assert created.title == "CRUD contract assignment"
    assert {name: getattr(created, name) for name in context} == context
    assert created not in db_session.dirty
    assert db_session.scalar(select(func.count()).select_from(Assignment)) == 1
    # Validation errors must leave the session usable without a rollback.
    updated = update_assignment(
        db_session,
        created,
        AssignmentUpdate(title="Valid subsequent change"),
    )
    assert updated.title == "Valid subsequent change"


def test_assignment_crud_partial_update_preserves_omitted_fields(db_session):
    track, module, lesson = _create_context(db_session)
    created = create_assignment(
        db_session,
        _payload(
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
            ordering=5,
            due_days=7,
            estimated_minutes=45,
            evaluation_config={"type": "manual"},
        ),
    )
    before = AssignmentResponse.model_validate(created).model_dump()
    updated = update_assignment(
        db_session,
        created,
        AssignmentUpdate(ordering=0, is_mandatory=False, is_active=False),
    )
    after = AssignmentResponse.model_validate(updated).model_dump()
    for field in before.keys() - {
        "ordering",
        "is_mandatory",
        "is_active",
        "updated_at",
    }:
        assert after[field] == before[field]
    assert (updated.ordering, updated.is_mandatory, updated.is_active) == (
        0,
        False,
        False,
    )


def test_assignment_crud_explicit_null_clears_only_nullable_fields(db_session):
    track, module, lesson = _create_context(db_session)
    created = create_assignment(
        db_session,
        _payload(
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
            due_days=7,
            estimated_minutes=45,
            evaluation_config={"type": "manual"},
        ),
    )
    updated = update_assignment(
        db_session,
        created,
        AssignmentUpdate(
            track_id=None,
            module_id=None,
            lesson_id=None,
            due_days=None,
            estimated_minutes=None,
            evaluation_config=None,
        ),
    )
    db_session.expire_all()
    assert updated.track is None
    assert updated.module is None
    assert updated.lesson is None
    assert updated.due_days is None
    assert updated.estimated_minutes is None
    assert updated.evaluation_config is None
    assert updated.title == "CRUD contract assignment"
    assert track.assignments == module.assignments == lesson.assignments == []


def test_assignment_crud_context_can_move_as_a_consistent_unit(db_session):
    track_a, module_a, lesson_a = _create_context(db_session, "-a")
    track_b, module_b, lesson_b = _create_context(db_session, "-b")
    created = create_assignment(
        db_session,
        _payload(track_id=track_a.id, module_id=module_a.id, lesson_id=lesson_a.id),
    )
    updated = update_assignment(
        db_session,
        created,
        AssignmentUpdate(
            track_id=track_b.id, module_id=module_b.id, lesson_id=lesson_b.id
        ),
    )
    assert updated.track is track_b
    assert updated.module is module_b
    assert updated.lesson is lesson_b
    assert get_assignments_by_context(db_session, track_id=track_a.id) == []
    assert get_assignments_by_context(db_session, track_id=track_b.id) == [updated]


@pytest.mark.parametrize(
    "changes",
    [{"title": None}, {"id": 999999}, {"difficulty": "expert"}],
)
def test_assignment_crud_dictionary_update_cannot_bypass_schema(db_session, changes):
    created = create_assignment(db_session, _payload())
    before = AssignmentResponse.model_validate(created).model_dump()
    with pytest.raises(ValidationError):
        crud_assignment.update(db_session, db_obj=created, obj_in=changes)
    assert AssignmentResponse.model_validate(created).model_dump() == before
    assert created not in db_session.dirty


def test_assignment_crud_dictionary_update_checks_merged_context(db_session):
    track_a, module_a, lesson_a = _create_context(db_session, "-a")
    track_b, _, _ = _create_context(db_session, "-b")
    created = create_assignment(
        db_session,
        _payload(track_id=track_a.id, module_id=module_a.id, lesson_id=lesson_a.id),
    )
    with pytest.raises(ValueError, match="module_id does not belong to track_id"):
        crud_assignment.update(
            db_session, db_obj=created, obj_in={"track_id": track_b.id}
        )
    assert created.track_id == track_a.id
    updated = crud_assignment.update(
        db_session,
        db_obj=created,
        obj_in={"title": "Dictionary update"},
    )
    assert updated.title == "Dictionary update"
    assert updated.module_id == module_a.id


def test_assignment_crud_empty_update_preserves_timestamps(db_session):
    created = create_assignment(db_session, _payload())
    before = AssignmentResponse.model_validate(created).model_dump()
    update_assignment(db_session, created, AssignmentUpdate())
    assert AssignmentResponse.model_validate(created).model_dump() == before


def test_assignment_crud_filters_inherited_context_and_combines_filters(db_session):
    track, module, lesson = _create_context(db_session, "-a")
    track_b, module_b, lesson_b = _create_context(db_session, "-b")
    owned = [
        create_assignment(db_session, _payload(**context))
        for context in (
            {"track_id": track.id},
            {"module_id": module.id},
            {"lesson_id": lesson.id},
            {"track_id": track.id, "module_id": module.id, "lesson_id": lesson.id},
        )
    ]
    create_assignment(db_session, _payload())
    other = create_assignment(db_session, _payload(lesson_id=lesson_b.id))
    assert get_assignments_by_context(db_session, track_id=track.id) == owned
    assert get_assignments_by_context(db_session, module_id=module.id) == owned[1:]
    assert get_assignments_by_context(db_session, lesson_id=lesson.id) == owned[2:]
    assert (
        get_assignments_by_context(
            db_session,
            track_id=track.id,
            module_id=module.id,
            lesson_id=lesson.id,
        )
        == owned[2:]
    )
    assert (
        get_assignments_by_context(
            db_session,
            track_id=track.id,
            module_id=module_b.id,
        )
        == []
    )
    assert get_assignments_by_context(db_session, track_id=track_b.id) == [other]


@pytest.mark.parametrize("method", ["get_by_context", "get_multi"])
def test_assignment_crud_stable_ordering_and_pagination(db_session, method):
    created = [
        create_assignment(
            db_session, _payload(title=f"Assignment {index}", ordering=order)
        )
        for index, order in enumerate([2, 1, 1, 0])
    ]
    expected = [created[3], created[1], created[2], created[0]]
    get_many = getattr(crud_assignment, method)
    assert list(get_many(db_session)) == expected
    assert list(get_many(db_session, skip=1, limit=2)) == expected[1:3]
    assert list(get_many(db_session, skip=0, limit=0)) == []
    assert list(get_many(db_session, skip=10, limit=2)) == []


@pytest.mark.parametrize("method", ["get_by_context", "get_multi"])
@pytest.mark.parametrize("pagination", [{"skip": -1}, {"limit": -1}])
def test_assignment_crud_rejects_negative_pagination(db_session, method, pagination):
    with pytest.raises(ValueError, match="non-negative"):
        getattr(crud_assignment, method)(db_session, **pagination)
    assert get_assignment(db_session, 999999) is None


def test_assignment_crud_missing_records(db_session):
    assert get_assignment(db_session, 999999) is None
    assert delete_assignment(db_session, 999999) is None
    for field in ("track_id", "module_id", "lesson_id"):
        assert get_assignments_by_context(db_session, **{field: 999999}) == []


def test_assignment_crud_delete_preserves_curriculum_and_other_assignments(db_session):
    track, module, lesson = _create_context(db_session)
    context = {"track_id": track.id, "module_id": module.id, "lesson_id": lesson.id}
    removed = create_assignment(db_session, _payload(**context))
    kept = create_assignment(db_session, _payload(**context))
    removed_id = removed.id
    assert delete_assignment(db_session, removed_id).id == removed_id
    assert get_assignment(db_session, removed_id) is None
    assert delete_assignment(db_session, removed_id) is None
    assert get_assignments_by_context(db_session, track_id=track.id) == [kept]
    assert db_session.get(Track, track.id) is track
    assert db_session.get(TrackModule, module.id) is module
    assert db_session.get(Lesson, lesson.id) is lesson
