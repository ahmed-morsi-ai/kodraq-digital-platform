from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.submission import (
    Submission,
    SubmissionFile,
    SubmissionReview,
    SubmissionStatus,
)
from app.models.user import User

PREVIOUS_REVISION = "8e2435463795"
REVISION = "d4a8511554d8"
BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
def migration_database(test_engine):
    # A fresh database keeps migration rollback away from all application/test data.
    database = f"kodraq_submission_migration_{uuid4().hex}"
    admin = create_engine(
        test_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    engine = create_engine(test_engine.url.set(database=database))
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()


def _migrate(engine, operation, revision):
    environment = dict(os.environ)
    environment["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
    environment["DEBUG"] = "false"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", operation, revision],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"\nalembic {operation} {revision}")
    print(result.stdout + result.stderr, end="")
    print(f"Exit code: {result.returncode}")
    assert result.returncode == 0


def test_submission_migration_round_trip_preserves_existing_data(migration_database):
    engine = migration_database
    _migrate(engine, "upgrade", PREVIOUS_REVISION)
    with Session(engine) as session:
        student = User(
            email="migration@example.com",
            full_name="Migration Student",
            hashed_password="test",
        )
        reviewer = User(
            email="reviewer@example.com",
            full_name="Migration Reviewer",
            hashed_password="test",
        )
        assignment = Assignment(
            title="Migration assignment",
            description="Description",
            instructions="Instructions",
            difficulty="beginner",
        )
        session.add_all([student, reviewer, assignment])
        session.flush()
        student_id, reviewer_id, assignment_id = student.id, reviewer.id, assignment.id
        submission_id = session.scalar(
            text(
                "INSERT INTO submissions (assignment_id, user_id, github_url) "
                "VALUES (:assignment, :student, 'https://github.com/student/work') RETURNING id"
            ),
            {"assignment": assignment_id, "student": student_id},
        )
        file_id, review_id = uuid4(), uuid4()
        session.execute(
            text(
                "INSERT INTO submission_files (id, submission_id, file_name, file_path, file_size, content_type) "
                "VALUES (:id, :submission, 'work.pdf', 'submissions/work.pdf', 512, 'application/pdf')"
            ),
            {"id": file_id, "submission": submission_id},
        )
        session.execute(
            text(
                "INSERT INTO submission_reviews (id, submission_id, reviewer_id, feedback, score, resulting_status) "
                "VALUES (:id, :submission, :reviewer, 'Original feedback', 70, 'CHANGES_REQUIRED')"
            ),
            {"id": review_id, "submission": submission_id, "reviewer": reviewer_id},
        )
        session.commit()

    _migrate(engine, "upgrade", REVISION)
    with Session(engine) as session:
        submission = session.get(Submission, submission_id)
        assert submission.status is SubmissionStatus.DRAFT
        assert submission.grade is submission.submitted_at is None
        assert submission.github_url == "https://github.com/student/work"
        file = session.get(SubmissionFile, file_id)
        assert (file.file_url, file.file_type, file.file_size) == (
            "submissions/work.pdf",
            "application/pdf",
            512,
        )
        review = session.get(SubmissionReview, review_id)
        assert (review.feedback_text, review.score, review.reviewer_id) == (
            "Original feedback",
            70,
            reviewer_id,
        )
        assert review.status_transition is SubmissionStatus.CHANGES_REQUIRED
        submission.grade = 85
        submission.submitted_at = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
        unknown_size_file = SubmissionFile(
            submission=submission,
            file_url="https://files.example.com/new.pdf",
            file_name="new.pdf",
            file_type="application/pdf",
        )
        session.add(unknown_size_file)
        session.commit()
        unknown_size_id = unknown_size_file.id
        session.refresh(submission)
        assert submission.grade == 85
        assert submission.submitted_at.tzinfo is not None
        for table, field in (
            ("submissions", "status"),
            ("submission_reviews", "status_transition"),
        ):
            with pytest.raises(IntegrityError):
                with session.begin_nested():
                    session.execute(text(f"UPDATE {table} SET {field} = 'INVALID'"))

    _migrate(engine, "downgrade", PREVIOUS_REVISION)
    inspector = inspect(engine)
    assert {
        column["name"] for column in inspector.get_columns("submissions")
    }.isdisjoint({"grade", "submitted_at"})
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT file_path FROM submission_files WHERE id = :id"),
                {"id": file_id},
            )
            == "submissions/work.pdf"
        )
        assert (
            connection.scalar(
                text("SELECT feedback FROM submission_reviews WHERE id = :id"),
                {"id": review_id},
            )
            == "Original feedback"
        )
        assert (
            connection.scalar(
                text("SELECT file_size FROM submission_files WHERE id = :id"),
                {"id": unknown_size_id},
            )
            == 0
        )

    _migrate(engine, "upgrade", REVISION)
    inspector = inspect(engine)
    assert "ix_submission_reviews_status_transition" in {
        index["name"] for index in inspector.get_indexes("submission_reviews")
    }
    for table in ("submissions", "submission_files", "submission_reviews"):
        for foreign_key in inspector.get_foreign_keys(table):
            expected = (
                "SET NULL"
                if foreign_key["constrained_columns"] == ["reviewer_id"]
                else "CASCADE"
            )
            assert foreign_key["options"]["ondelete"] == expected
    with Session(engine) as session:
        assert (
            session.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
        )
        assert session.get(SubmissionFile, file_id).file_size == 512
        assert (
            session.get(SubmissionFile, unknown_size_id).file_url
            == "https://files.example.com/new.pdf"
        )
        review = session.get(SubmissionReview, review_id)
        assert review.feedback_text == "Original feedback"
        assert review.status_transition is SubmissionStatus.CHANGES_REQUIRED
        session.execute(text("DELETE FROM users WHERE id = :id"), {"id": reviewer_id})
        session.expire_all()
        assert review.reviewer_id is None
        session.execute(
            text("DELETE FROM submissions WHERE id = :id"), {"id": submission_id}
        )
        session.expire_all()
        assert session.get(SubmissionFile, file_id) is None
        assert session.get(SubmissionFile, unknown_size_id) is None
        assert session.get(SubmissionReview, review_id) is None
    print(
        "Migration data preservation, enum constraints, defaults, and deletion checks passed."
    )


def test_submission_attempt_migration_round_trip(migration_database):
    engine = migration_database
    _migrate(engine, "upgrade", REVISION)
    submitted_at = datetime.now(UTC)
    with Session(engine) as session:
        user = User(
            email="history@example.com",
            hashed_password="test",
            full_name="History Student",
        )
        assignment = Assignment(
            title="History",
            description="History",
            instructions="Submit",
            difficulty="beginner",
        )
        submission = Submission(
            user=user,
            assignment=assignment,
            status="CHANGES_REQUIRED",
            submitted_at=submitted_at,
        )
        session.add(submission)
        session.commit()
        submission_id = submission.id
    history_revision = "e7b252600001"
    for iteration in range(2):
        _migrate(engine, "upgrade", history_revision)
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT submission_id, submitted_at FROM submission_attempts")
            ).all()
            assert rows == [(submission_id, submitted_at)]
        assert (
            inspect(engine).get_foreign_keys("submission_attempts")[0]["options"][
                "ondelete"
            ]
            == "CASCADE"
        )
        if iteration == 0:
            _migrate(engine, "downgrade", REVISION)
            assert "submission_attempts" not in inspect(engine).get_table_names()
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM submissions WHERE id=:id"), {"id": submission_id}
        )
        assert connection.scalar(text("SELECT COUNT(*) FROM submission_attempts")) == 0
    print(
        "Submission history backfill, upgrade/downgrade/re-upgrade, and cascade checks passed."
    )
