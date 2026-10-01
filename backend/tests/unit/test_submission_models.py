from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.models.assignment import Assignment
from app.models.submission import (
    Submission,
    SubmissionFile,
    SubmissionReview,
    SubmissionStatus,
)
from app.models.user import User
from app.schemas.submission_file import SubmissionFileResponse


def _create_user(
    db_session,
    *,
    email: str,
    full_name: str,
) -> User:
    user = User(
        email=email,
        hashed_password="test-hash",
        full_name=full_name,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_assignment(db_session) -> Assignment:
    assignment = Assignment(
        title="Submission Test Assignment",
        description="Test assignment",
        instructions="Submit the work",
        difficulty="beginner",
        ordering=0,
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(assignment)
    db_session.flush()
    return assignment


def test_submission_file_and_review_models(db_session):
    student = _create_user(
        db_session,
        email="student-submission-model@example.com",
        full_name="Submission Student",
    )
    reviewer = _create_user(
        db_session,
        email="reviewer-submission-model@example.com",
        full_name="Submission Reviewer",
    )
    assignment = _create_assignment(db_session)

    submission = Submission(
        assignment_id=assignment.id,
        user_id=student.id,
        status=SubmissionStatus.SUBMITTED.value,
        content="Submission content",
    )
    db_session.add(submission)
    db_session.flush()

    submission_file = SubmissionFile(
        submission_id=submission.id,
        file_name="solution.pdf",
        file_url="submissions/1/solution.pdf",
        file_size=4096,
        file_type="application/pdf",
    )
    review = SubmissionReview(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        feedback_text="Looks good",
        score=90,
        status_transition=SubmissionStatus.APPROVED.value,
    )
    submission.files.append(submission_file)
    submission.reviews.append(review)
    db_session.commit()

    assert submission_file.id is not None
    assert review.id is not None
    assert submission_file.submission_id == submission.id
    assert review.submission_id == submission.id
    assert review.reviewer_id == reviewer.id

    loaded_submission = db_session.get(Submission, submission.id)
    assert loaded_submission is not None
    assert len(loaded_submission.files) == 1
    assert len(loaded_submission.reviews) == 1


def test_submission_delete_cascades_files_and_reviews(db_session):
    student = _create_user(
        db_session,
        email="student-cascade@example.com",
        full_name="Cascade Student",
    )
    reviewer = _create_user(
        db_session,
        email="reviewer-cascade@example.com",
        full_name="Cascade Reviewer",
    )
    assignment = _create_assignment(db_session)

    submission = Submission(
        assignment_id=assignment.id,
        user_id=student.id,
        status=SubmissionStatus.SUBMITTED.value,
    )
    db_session.add(submission)
    db_session.flush()

    submission_file = SubmissionFile(
        submission_id=submission.id,
        file_name="cascade.pdf",
        file_url="submissions/cascade.pdf",
        file_size=128,
        file_type="application/pdf",
    )
    review = SubmissionReview(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        feedback_text="Needs revision",
        score=60,
        status_transition=SubmissionStatus.CHANGES_REQUIRED.value,
    )
    db_session.add_all([submission_file, review])
    db_session.commit()

    file_id = submission_file.id
    review_id = review.id

    db_session.execute(delete(Submission).where(Submission.id == submission.id))
    db_session.commit()

    assert db_session.get(SubmissionFile, file_id) is None
    assert db_session.get(SubmissionReview, review_id) is None
    assert db_session.get(Submission, submission.id) is None


def test_submission_review_reviewer_set_null_on_user_delete(db_session):
    student = _create_user(
        db_session,
        email="student-reviewer-null@example.com",
        full_name="Review Student",
    )
    reviewer = _create_user(
        db_session,
        email="reviewer-null@example.com",
        full_name="Review Reviewer",
    )
    assignment = _create_assignment(db_session)

    submission = Submission(
        assignment_id=assignment.id,
        user_id=student.id,
        status=SubmissionStatus.SUBMITTED.value,
    )
    db_session.add(submission)
    db_session.flush()

    review = SubmissionReview(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        feedback_text="Reviewer feedback",
        status_transition=SubmissionStatus.REJECTED.value,
    )
    db_session.add(review)
    db_session.commit()

    review_id = review.id

    db_session.execute(delete(User).where(User.id == reviewer.id))
    db_session.commit()

    persisted_review = db_session.get(SubmissionReview, review_id)
    assert persisted_review is not None
    assert persisted_review.reviewer_id is None


def test_submission_file_metadata_persists(db_session):
    student = _create_user(
        db_session,
        email="student-file@example.com",
        full_name="File Student",
    )
    assignment = _create_assignment(db_session)

    submission = Submission(
        assignment_id=assignment.id,
        user_id=student.id,
        status=SubmissionStatus.DRAFT.value,
    )
    db_session.add(submission)
    db_session.flush()

    file = SubmissionFile(
        submission_id=submission.id,
        file_name="archive.zip",
        file_url="submissions/archive.zip",
        file_size=2048,
        file_type="application/zip",
    )
    db_session.add(file)
    db_session.commit()

    persisted = db_session.execute(
        select(SubmissionFile).where(SubmissionFile.id == file.id)
    ).scalar_one()

    assert persisted.file_name == "archive.zip"
    assert persisted.file_url == "submissions/archive.zip"
    assert persisted.file_size == 2048
    assert persisted.file_type == "application/zip"


@pytest.fixture
def submission_graph(db_session):
    student = _create_user(
        db_session, email="model-student@example.com", full_name="Student"
    )
    reviewer = _create_user(
        db_session, email="model-reviewer@example.com", full_name="Reviewer"
    )
    submission = Submission(assignment=_create_assignment(db_session), user=student)
    submission.files.append(
        SubmissionFile(
            file_url="https://files.example.com/solution.pdf",
            file_name="solution.pdf",
            file_type="application/pdf",
        )
    )
    submission.reviews.append(
        SubmissionReview(
            reviewer=reviewer,
            feedback_text="Please add tests.",
            status_transition=SubmissionStatus.CHANGES_REQUIRED,
        )
    )
    db_session.add(submission)
    db_session.flush()
    return submission


def test_submission_enum_has_exact_roadmap_states():
    assert [(state.name, state.value) for state in SubmissionStatus] == [
        (value, value)
        for value in (
            "DRAFT",
            "SUBMITTED",
            "UNDER_REVIEW",
            "CHANGES_REQUIRED",
            "APPROVED",
            "REJECTED",
        )
    ]


def test_submission_defaults_and_bidirectional_relationships(
    db_session, submission_graph
):
    submission_id = submission_graph.id
    db_session.expire_all()
    submission = db_session.get(Submission, submission_id)
    assert submission.status is SubmissionStatus.DRAFT
    assert submission.grade is None
    assert submission.github_url is None
    assert submission.submitted_at is None
    assert submission in submission.assignment.submissions
    assert submission in submission.user.submissions
    file = submission.files[0]
    review = submission.reviews[0]
    assert file.submission is submission
    assert review.submission is submission
    assert review in review.reviewer.submission_reviews
    assert review.status_transition is SubmissionStatus.CHANGES_REQUIRED
    assert file.file_url == "https://files.example.com/solution.pdf"
    assert file.file_name == "solution.pdf"
    assert file.file_type == "application/pdf"
    assert review.feedback_text == "Please add tests."
    for record in (submission, file, review):
        assert record.created_at.tzinfo is not None
    assert submission.updated_at.tzinfo is not None
    assert submission.updated_at >= submission.created_at


def test_submission_nullable_file_size_response(submission_graph):
    file = submission_graph.files[0]
    response = SubmissionFileResponse.model_validate(file)
    assert file.file_size is None
    assert response.file_size_bytes is None
    assert response.file_url == file.file_url
    assert response.file_type == file.file_type


def test_submission_grade_github_and_submission_time_persist(
    db_session, submission_graph
):
    submitted_at = datetime(2026, 9, 25, 12, 30, tzinfo=UTC)
    submission_graph.grade = 91
    submission_graph.github_url = "https://github.com/student/solution"
    submission_graph.submitted_at = submitted_at
    submission_graph.status = SubmissionStatus.APPROVED
    db_session.flush()
    db_session.refresh(submission_graph)
    assert submission_graph.grade == 91
    assert submission_graph.github_url == "https://github.com/student/solution"
    assert submission_graph.submitted_at == submitted_at
    assert submission_graph.submitted_at.tzinfo is not None
    submission_graph.grade = None
    submission_graph.github_url = None
    submission_graph.submitted_at = None
    db_session.flush()
    db_session.refresh(submission_graph)
    assert submission_graph.grade is None
    assert submission_graph.github_url is None
    assert submission_graph.submitted_at is None


def test_submission_updated_at_changes_on_edit(db_session, submission_graph):
    earlier = datetime(2000, 1, 1, tzinfo=UTC)
    submission_graph.updated_at = earlier
    db_session.flush()
    submission_graph.grade = 80
    db_session.flush()
    db_session.refresh(submission_graph)
    assert submission_graph.updated_at > earlier


@pytest.mark.parametrize("state", list(SubmissionStatus))
def test_submission_states_round_trip_as_enum(db_session, submission_graph, state):
    submission_graph.status = state.value
    submission_graph.reviews[0].status_transition = state.value
    db_session.flush()
    db_session.expire_all()
    assert submission_graph.status is state
    assert submission_graph.reviews[0].status_transition is state


@pytest.mark.parametrize("invalid", ["draft", "PENDING", "APPROVE", "", None, 1])
def test_submission_enum_rejects_invalid_values(invalid):
    with pytest.raises(ValueError):
        SubmissionStatus(invalid)
    with pytest.raises(ValueError):
        Submission(status=invalid)
    with pytest.raises(ValueError):
        SubmissionReview(status_transition=invalid)


@pytest.mark.parametrize("target", ["submission", "review"])
def test_submission_enum_rejects_invalid_assignment(submission_graph, target):
    record = submission_graph if target == "submission" else submission_graph.reviews[0]
    attribute = "status" if target == "submission" else "status_transition"
    with pytest.raises(ValueError):
        setattr(record, attribute, "INVALID")


@pytest.mark.parametrize(
    "model,field",
    [
        (Submission, "status"),
        (SubmissionReview, "status_transition"),
    ],
)
def test_submission_enum_rejects_invalid_core_writes(
    db_session, submission_graph, model, field
):
    with pytest.raises(StatementError):
        with db_session.begin_nested():
            db_session.execute(model.__table__.update().values({field: "INVALID"}))


@pytest.mark.parametrize(
    "table,field",
    [
        ("submissions", "status"),
        ("submission_reviews", "status_transition"),
    ],
)
@pytest.mark.parametrize("value", ["INVALID", "draft", None])
def test_submission_database_rejects_invalid_states(
    db_session, submission_graph, table, field, value
):
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(f"UPDATE {table} SET {field} = :value"), {"value": value}
            )


def test_submission_database_draft_default(db_session, submission_graph):
    row = db_session.execute(
        text(
            "INSERT INTO submissions (assignment_id, user_id) VALUES (:assignment, :student) "
            "RETURNING status, grade, submitted_at, created_at, updated_at"
        ),
        {
            "assignment": submission_graph.assignment_id,
            "student": submission_graph.user_id,
        },
    ).one()
    assert row.status == "DRAFT"
    assert row.grade is None
    assert row.submitted_at is None
    assert row.created_at.tzinfo is not None
    assert row.updated_at.tzinfo is not None


@pytest.mark.parametrize(
    "target,field",
    [
        ("submission", "assignment_id"),
        ("submission", "user_id"),
        ("file", "submission_id"),
        ("file", "file_url"),
        ("file", "file_name"),
        ("file", "file_type"),
        ("review", "submission_id"),
        ("review", "feedback_text"),
    ],
)
def test_submission_required_fields(db_session, submission_graph, target, field):
    record = {
        "submission": submission_graph,
        "file": submission_graph.files[0],
        "review": submission_graph.reviews[0],
    }[target]
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            setattr(record, field, None)
            db_session.flush()


@pytest.mark.parametrize(
    "target,field",
    [
        ("submission", "assignment_id"),
        ("submission", "user_id"),
        ("file", "submission_id"),
        ("review", "submission_id"),
        ("review", "reviewer_id"),
    ],
)
def test_submission_rejects_missing_foreign_keys(
    db_session, submission_graph, target, field
):
    record = {
        "submission": submission_graph,
        "file": submission_graph.files[0],
        "review": submission_graph.reviews[0],
    }[target]
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            setattr(record, field, -1)
            db_session.flush()


@pytest.mark.parametrize("target", ["assignment", "student", "submission"])
@pytest.mark.parametrize("through_orm", [True, False])
def test_submission_parent_deletion_cascades(
    db_session, submission_graph, target, through_orm
):
    submission = submission_graph
    student_id, assignment_id = submission.user_id, submission.assignment_id
    reviewer_id = submission.reviews[0].reviewer_id
    ids = (submission.id, submission.files[0].id, submission.reviews[0].id)
    record = {
        "assignment": submission.assignment,
        "student": submission.user,
        "submission": submission,
    }[target]
    if through_orm:
        db_session.delete(record)
        db_session.flush()
    else:
        db_session.execute(delete(type(record)).where(type(record).id == record.id))
    db_session.expire_all()
    for model, record_id in zip(
        (Submission, SubmissionFile, SubmissionReview), ids, strict=True
    ):
        assert db_session.get(model, record_id) is None
    assert db_session.get(User, reviewer_id) is not None
    if target != "student":
        assert db_session.get(User, student_id) is not None
    if target != "assignment":
        assert db_session.get(Assignment, assignment_id) is not None


def test_submission_reviewer_orm_deletion_preserves_review(
    db_session, submission_graph
):
    review = submission_graph.reviews[0]
    db_session.delete(review.reviewer)
    db_session.flush()
    db_session.expire_all()
    assert review.reviewer_id is None
    assert review.reviewer is None
    assert review.feedback_text == "Please add tests."
    assert review.submission is submission_graph


@pytest.mark.parametrize(
    "collection,model", [("files", SubmissionFile), ("reviews", SubmissionReview)]
)
def test_submission_children_delete_orphan(
    db_session, submission_graph, collection, model
):
    records = getattr(submission_graph, collection)
    record_id = records[0].id
    records.clear()
    db_session.flush()
    assert db_session.get(model, record_id) is None
    assert db_session.get(Submission, submission_graph.id) is submission_graph


def test_submission_file_api_aliases_share_canonical_columns(
    db_session, submission_graph
):
    file = submission_graph.files[0]
    file.file_url = "submissions/changed.zip"
    file.file_type = "application/zip"
    db_session.flush()
    db_session.expire_all()
    assert file.file_url == "submissions/changed.zip"
    assert file.file_type == "application/zip"
    assert "file_path" not in SubmissionFile.__table__.columns
    assert "content_type" not in SubmissionFile.__table__.columns
    assert "feedback" not in SubmissionReview.__table__.columns
    assert "resulting_status" not in SubmissionReview.__table__.columns
