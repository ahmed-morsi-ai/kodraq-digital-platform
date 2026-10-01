from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


@pytest.mark.parametrize("schema", [AssignmentCreate, AssignmentUpdate])
@pytest.mark.parametrize(
    "invalid",
    [
        {"title": "x" * 256},
        {"track_id": 0},
        {"module_id": -1},
        {"lesson_id": 0},
        {"difficulty": "expert"},
        {"id": 1},
        {"created_at": "2000-01-01T00:00:00Z"},
    ],
)
def test_assignment_inputs_reject_invalid_values(schema, invalid):
    payload = {}
    if schema is AssignmentCreate:
        payload = {
            "title": "Assignment",
            "description": "Description",
            "instructions": "Instructions",
            "difficulty": "beginner",
        }
    with pytest.raises(ValidationError):
        schema(**(payload | invalid))


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "description",
        "instructions",
        "difficulty",
        "ordering",
        "is_mandatory",
        "is_active",
    ],
)
def test_assignment_update_rejects_explicit_null_for_required_columns(field):
    with pytest.raises(ValidationError):
        AssignmentUpdate(**{field: None})


def test_assignment_update_distinguishes_omitted_null_and_falsy_values():
    assert AssignmentUpdate().model_dump(exclude_unset=True) == {}
    changes = {
        "track_id": None,
        "module_id": None,
        "lesson_id": None,
        "due_days": None,
        "estimated_minutes": None,
        "evaluation_config": None,
        "ordering": 0,
        "is_mandatory": False,
        "is_active": False,
    }
    assert AssignmentUpdate(**changes).model_dump(exclude_unset=True) == changes


def test_assignment_create_preserves_defaults_and_title_boundary():
    payload = AssignmentCreate(
        title="x" * 255,
        description="Description",
        instructions="Instructions",
        difficulty="beginner",
    )
    assert len(payload.title) == 255
    assert payload.track_id is payload.module_id is payload.lesson_id is None
    assert payload.ordering == 0
    assert payload.is_mandatory is True
    assert payload.is_active is True
