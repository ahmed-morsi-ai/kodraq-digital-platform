import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from datetime import timedelta

from sqlalchemy import create_engine, inspect, text


def test_quiz_attempt_migration_round_trip(test_engine):
    database = f"kodraq_attempt_migration_{uuid4().hex}"
    admin = create_engine(
        test_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    engine = create_engine(test_engine.url.set(database=database))

    def migrate(operation, revision):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", operation, revision],
            cwd=Path(__file__).resolve().parents[2],
            env=dict(
                os.environ,
                DEBUG="false",
                DATABASE_URL=engine.url.render_as_string(hide_password=False),
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        print(
            f"alembic {operation} {revision}\n{result.stdout}{result.stderr}Exit code: {result.returncode}"
        )
        assert result.returncode == 0

    try:
        migrate("upgrade", "f15300000001")
        with engine.begin() as connection:
            user = connection.scalar(
                text(
                    "INSERT INTO users(email, full_name, hashed_password, is_active, is_superuser) VALUES ('migration@example.com', 'Migration User', 'unused', true, false) RETURNING id"
                )
            )
            for minutes, completed in ((10, False), (None, True)):
                quiz = connection.scalar(
                    text(
                        "INSERT INTO quizzes(title, passing_score, time_limit_minutes) VALUES ('Legacy quiz', 75, :minutes) RETURNING id"
                    ),
                    {"minutes": minutes},
                )
                connection.execute(
                    text(
                        "INSERT INTO quiz_attempts(quiz_id, user_id, score, passed, is_flagged, status, completed_at) VALUES (:quiz, :user, :score, :passed, false, :status, :completed)"
                    ),
                    {
                        "quiz": quiz,
                        "user": user,
                        "score": 80 if completed else None,
                        "passed": completed,
                        "status": "COMPLETED" if completed else "IN_PROGRESS",
                        "completed": "2026-09-01T00:00:00Z" if completed else None,
                    },
                )
        for iteration in range(2):
            migrate("upgrade", "f15300000002")
            with engine.connect() as connection:
                rows = (
                    connection.execute(
                        text(
                            "SELECT passing_score, deadline_at, started_at, score, status, result_snapshot FROM quiz_attempts ORDER BY id"
                        )
                    )
                    .mappings()
                    .all()
                )
                assert [row["passing_score"] for row in rows] == [75, 75]
                assert rows[0]["deadline_at"] - rows[0]["started_at"] == timedelta(
                    minutes=10
                )
                assert rows[1]["deadline_at"] is None
                assert rows[1]["score"] == 80 and rows[1]["status"] == "COMPLETED"
                assert all(row["result_snapshot"] is None for row in rows)
            if iteration == 0:
                migrate("downgrade", "f15300000001")
                assert "deadline_at" not in {
                    column["name"]
                    for column in inspect(engine).get_columns("quiz_attempts")
                }
        print(
            "Attempt migration preserved grades and backfilled deadlines/thresholds through upgrade -> downgrade -> re-upgrade."
        )
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()
