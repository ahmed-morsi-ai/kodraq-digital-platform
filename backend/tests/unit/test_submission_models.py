from __future__ import annotations

from sqlalchemy import delete, select

from app.models.assignment import Assignment
from app.models.submission import (
    Submission,
    SubmissionFile,
    SubmissionReview,
    SubmissionStatus,
)
from app.models.user import User


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
        file_path="submissions/1/solution.pdf",
        file_size=4096,
        content_type="application/pdf",
    )
    review = SubmissionReview(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        feedback="Looks good",
        score=90,
        resulting_status=SubmissionStatus.APPROVED.value,
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
        file_path="submissions/cascade.pdf",
        file_size=128,
        content_type="application/pdf",
    )
    review = SubmissionReview(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        feedback="Needs revision",
        score=60,
        resulting_status=SubmissionStatus.CHANGES_REQUIRED.value,
    )
    db_session.add_all([submission_file, review])
    db_session.commit()

    file_id = submission_file.id
    review_id = review.id

    db_session.execute(
        delete(Submission).where(Submission.id == submission.id)
    )
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
        feedback="Reviewer feedback",
        resulting_status=SubmissionStatus.REJECTED.value,
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
        file_path="submissions/archive.zip",
        file_size=2048,
        content_type="application/zip",
    )
    db_session.add(file)
    db_session.commit()

    persisted = db_session.execute(
        select(SubmissionFile).where(SubmissionFile.id == file.id)
    ).scalar_one()

    assert persisted.file_name == "archive.zip"
    assert persisted.file_path == "submissions/archive.zip"
    assert persisted.file_size == 2048
    assert persisted.content_type == "application/zip"
