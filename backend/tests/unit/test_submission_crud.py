from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.crud.crud_submission import SubmissionStateError
from app.crud.crud_submission import submission as crud
from app.models.assignment import Assignment
from app.models.submission import Submission, SubmissionReview
from app.models.user import User
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionReviewCreate,
    SubmissionUpdate,
)
from tests.submission_helpers import make_submission


@pytest.mark.parametrize("role", ["student", "other", "employee"])
def test_crud_review_enforces_roles(db_session, submission_data, role):
    record = make_submission(db_session, submission_data, state="SUBMITTED")
    with pytest.raises(PermissionError):
        crud.create_review_and_transition(
            db_session,
            db_obj=record,
            actor=submission_data.users[role],
            obj_in=SubmissionReviewCreate(
                feedback_text="Denied", status_transition="APPROVED", grade=100
            ),
        )
    assert record.status == "SUBMITTED"
    assert db_session.scalar(select(func.count()).select_from(SubmissionReview)) == 0


@pytest.mark.parametrize("scope", ["other", "unscoped", "inconsistent"])
def test_crud_instructor_scope_is_not_only_an_api_check(
    db_session, submission_data, scope
):
    data = submission_data
    record = make_submission(db_session, data, scope=scope, state="SUBMITTED")
    with pytest.raises(PermissionError):
        crud.create_review_and_transition(
            db_session,
            db_obj=record,
            actor=data.users["instructor"],
            obj_in=SubmissionReviewCreate(
                feedback_text="Denied", status_transition="APPROVED"
            ),
        )
    with pytest.raises(PermissionError):
        crud.get_for_user(
            db_session, submission_id=record.id, actor=data.users["instructor"]
        )


@pytest.mark.parametrize(
    "extra",
    [
        {"grade": 100},
        {"user_id": 999},
        {"assignment_id": 999},
        {"status": "APPROVED"},
        {"status": None},
    ],
)
def test_crud_update_revalidates_dicts(db_session, submission_data, extra):
    record = make_submission(db_session, submission_data)
    with pytest.raises(ValidationError):
        crud.update(
            db_session,
            db_obj=record,
            actor=submission_data.users["student"],
            obj_in=extra,
        )
    assert record.grade is None
    assert record.status == "DRAFT"


def test_crud_update_revalidates_constructed_schemas(db_session, submission_data):
    record = make_submission(db_session, submission_data)
    with pytest.raises(ValidationError):
        crud.update(
            db_session,
            db_obj=record,
            actor=submission_data.users["student"],
            obj_in=SubmissionUpdate.model_construct(status="APPROVED"),
        )
    assert record.status == "DRAFT"


def test_crud_checks_ownership_without_http(db_session, submission_data):
    record = make_submission(db_session, submission_data)
    with pytest.raises(PermissionError):
        crud.update(
            db_session,
            db_obj=record,
            actor=submission_data.users["other"],
            obj_in=SubmissionUpdate(content="Tampered"),
        )
    with pytest.raises(PermissionError):
        crud.get_for_user(
            db_session, submission_id=record.id, actor=submission_data.users["other"]
        )
    assert record.content == "Original work"


def test_crud_handles_default_student_role(db_session, submission_data):
    data = submission_data
    data.users["student"].role_rel = None
    db_session.flush()
    record = crud.create(
        db_session,
        actor=data.users["student"],
        obj_in=SubmissionCreate(assignment_id=data.assignments["track"].id),
    )
    assert record.status == "DRAFT"
    assert record.user_id == data.users["student"].id


@pytest.mark.parametrize("state", ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"])
def test_crud_rejects_edits_to_locked_states(db_session, submission_data, state):
    record = make_submission(db_session, submission_data, state=state)
    with pytest.raises(SubmissionStateError):
        crud.update(
            db_session,
            db_obj=record,
            actor=submission_data.users["student"],
            obj_in=SubmissionUpdate(content="Blocked"),
        )
    assert record.content == "Original work"


@pytest.mark.parametrize("operation", ["update", "review"])
def test_crud_refreshes_stale_state_before_mutating(
    db_session, submission_data, operation
):
    data = submission_data
    record = make_submission(
        db_session, data, state="DRAFT" if operation == "update" else "SUBMITTED"
    )
    db_session.execute(
        text("UPDATE submissions SET status = 'APPROVED' WHERE id = :id"),
        {"id": record.id},
    )
    assert record.status != "APPROVED"
    with pytest.raises(SubmissionStateError):
        if operation == "update":
            crud.update(
                db_session,
                db_obj=record,
                actor=data.users["student"],
                obj_in=SubmissionUpdate(status="SUBMITTED"),
            )
        else:
            crud.create_review_and_transition(
                db_session,
                db_obj=record,
                actor=data.users["admin"],
                obj_in=SubmissionReviewCreate(
                    feedback_text="Duplicate", status_transition="REJECTED"
                ),
            )
    assert record.status == "APPROVED"
    assert db_session.scalar(select(func.count()).select_from(SubmissionReview)) == 0


def test_crud_review_can_clear_grade(db_session, submission_data):
    record = make_submission(db_session, submission_data, state="SUBMITTED")
    record.grade = 75
    db_session.flush()
    reviewed = crud.create_review_and_transition(
        db_session,
        db_obj=record,
        actor=submission_data.users["admin"],
        obj_in=SubmissionReviewCreate(
            feedback_text="More work required",
            status_transition="CHANGES_REQUIRED",
            grade=None,
        ),
    )
    assert reviewed.grade is None
    assert reviewed.reviews[0].score is None


def test_draft_edit_does_not_change_submission_time_or_grade(
    db_session, submission_data
):
    record = make_submission(db_session, submission_data, state="CHANGES_REQUIRED")
    earlier = datetime(2020, 1, 1, tzinfo=UTC)
    record.submitted_at, record.grade = earlier, 60
    db_session.flush()
    updated = crud.update(
        db_session,
        db_obj=record,
        actor=submission_data.users["student"],
        obj_in=SubmissionUpdate(content="Working on feedback"),
    )
    assert updated.submitted_at == earlier
    assert updated.grade == 60
    assert updated.status == "CHANGES_REQUIRED"


@pytest.mark.parametrize("operation", ["create", "update", "review"])
def test_crud_rolls_back_failed_transaction(
    db_session, submission_data, monkeypatch, operation
):
    data = submission_data
    record = make_submission(
        db_session, data, state="SUBMITTED" if operation == "review" else "DRAFT"
    )
    expected_count = db_session.scalar(select(func.count()).select_from(Submission))
    with Session(
        bind=db_session.connection(), join_transaction_mode="create_savepoint"
    ) as isolated:
        actor = isolated.get(
            User, data.users["admin" if operation == "review" else "student"].id
        )
        loaded = isolated.get(Submission, record.id)

        def failed_commit():
            isolated.flush()
            raise RuntimeError("Simulated database failure after flush")

        monkeypatch.setattr(isolated, "commit", failed_commit)
        with pytest.raises(RuntimeError, match="after flush"):
            if operation == "create":
                crud.create(
                    isolated,
                    actor=actor,
                    obj_in=SubmissionCreate(assignment_id=record.assignment_id),
                )
            elif operation == "update":
                crud.update(
                    isolated,
                    db_obj=loaded,
                    actor=actor,
                    obj_in=SubmissionUpdate(
                        status="SUBMITTED", content="Should roll back"
                    ),
                )
            else:
                crud.create_review_and_transition(
                    isolated,
                    db_obj=loaded,
                    actor=actor,
                    obj_in=SubmissionReviewCreate(
                        feedback_text="Should roll back",
                        status_transition="APPROVED",
                        grade=99,
                    ),
                )
    db_session.refresh(record)
    assert record.status == ("SUBMITTED" if operation == "review" else "DRAFT")
    assert record.grade is None
    assert record.submitted_at is None
    assert record.content == "Original work"
    assert db_session.scalar(select(func.count()).select_from(SubmissionReview)) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(Submission))
        == expected_count
    )


def test_concurrent_reviews_cannot_both_finalize_submission(test_engine):
    suffix = uuid4().hex
    with Session(test_engine) as setup:
        student = User(
            email=f"student-{suffix}@example.com",
            full_name="Student",
            hashed_password="unused",
        )
        admin = User(
            email=f"admin-{suffix}@example.com",
            full_name="Admin",
            hashed_password="unused",
            is_superuser=True,
        )
        assignment = Assignment(
            title="Concurrent review",
            description="Test",
            instructions="Test",
            difficulty="beginner",
        )
        record = Submission(user=student, assignment=assignment, status="SUBMITTED")
        setup.add_all([admin, record])
        setup.commit()
        student_id, admin_id, assignment_id, submission_id = (
            student.id,
            admin.id,
            assignment.id,
            record.id,
        )
    barrier = Barrier(2, timeout=10)

    def review(grade):
        with Session(test_engine) as session:
            session.execute(text("SET LOCAL lock_timeout = '10s'"))
            actor = session.get(User, admin_id)
            loaded = session.get(Submission, submission_id)
            barrier.wait()
            try:
                crud.create_review_and_transition(
                    session,
                    db_obj=loaded,
                    actor=actor,
                    obj_in=SubmissionReviewCreate(
                        feedback_text=f"Grade {grade}",
                        status_transition="APPROVED",
                        grade=grade,
                    ),
                )
                return "saved"
            except SubmissionStateError:
                return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(review, (90, 95)))
        assert sorted(results) == ["conflict", "saved"]
        with Session(test_engine) as session:
            loaded = session.get(Submission, submission_id)
            assert loaded.status == "APPROVED"
            assert len(loaded.reviews) == 1
            assert loaded.grade == loaded.reviews[0].score
    finally:
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(Assignment).where(Assignment.id == assignment_id))
            cleanup.execute(delete(User).where(User.id.in_([student_id, admin_id])))
            cleanup.commit()
