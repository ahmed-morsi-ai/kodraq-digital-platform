import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text


def test_quiz_foundation_migration_round_trip(test_engine):
    database = f"kodraq_quiz_migration_{uuid4().hex}"
    admin = create_engine(
        test_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    engine = create_engine(test_engine.url.set(database=database))

    def migrate(operation, revision):
        environment = dict(
            os.environ,
            DEBUG="false",
            DATABASE_URL=engine.url.render_as_string(hide_password=False),
        )
        result = subprocess.run(
            [sys.executable, "-m", "alembic", operation, revision],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        print(
            f"alembic {operation} {revision}\n{result.stdout}{result.stderr}Exit code: {result.returncode}"
        )
        assert result.returncode == 0

    try:
        migrate("upgrade", "e7b252600001")
        with engine.begin() as connection:
            question_id = connection.scalar(
                text(
                    "INSERT INTO questions (text, question_type, points) VALUES ('Existing question', 'TRUE_FALSE', 2) RETURNING id"
                )
            )
            quiz_id = connection.scalar(
                text(
                    "INSERT INTO quizzes (title, passing_score, is_active) VALUES ('Existing quiz', 70, true) RETURNING id"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO question_options (question_id, text, is_correct) VALUES (:id, 'True', true)"
                ),
                {"id": question_id},
            )
            connection.execute(
                text(
                    "INSERT INTO quiz_questions (quiz_id, question_id, ordering) VALUES (:quiz, :question, 2)"
                ),
                {"quiz": quiz_id, "question": question_id},
            )
        for iteration in range(2):
            migrate("upgrade", "f15300000001")
            inspector = inspect(engine)
            for table in ("quizzes", "questions"):
                assert "module_id" in {
                    column["name"] for column in inspector.get_columns(table)
                }
                module_fk = next(
                    fk
                    for fk in inspector.get_foreign_keys(table)
                    if fk["constrained_columns"] == ["module_id"]
                )
                assert module_fk["options"]["ondelete"] == "SET NULL"
            with engine.connect() as connection:
                assert (
                    connection.scalar(
                        text("SELECT text FROM questions WHERE id=:id"),
                        {"id": question_id},
                    )
                    == "Existing question"
                )
                assert (
                    connection.scalar(
                        text("SELECT ordering FROM quiz_questions WHERE quiz_id=:id"),
                        {"id": quiz_id},
                    )
                    == 2
                )
            if iteration == 0:
                migrate("downgrade", "e7b252600001")
                assert "module_id" not in {
                    column["name"]
                    for column in inspect(engine).get_columns("questions")
                }
        with engine.begin() as connection:
            defaults = connection.execute(
                text(
                    "INSERT INTO questions (text, question_type) VALUES ('Defaults', 'TRUE_FALSE') RETURNING difficulty, points"
                )
            ).one()
            assert defaults == (1, 1)
            assert (
                connection.scalar(
                    text(
                        "INSERT INTO quizzes (title, passing_score) VALUES ('Defaults quiz', 100) RETURNING is_active"
                    )
                )
                is True
            )
            assert (
                connection.scalar(
                    text(
                        "INSERT INTO question_options (question_id, text) VALUES (:id, 'False') RETURNING is_correct"
                    ),
                    {"id": question_id},
                )
                is False
            )
            connection.execute(
                text("DELETE FROM questions WHERE id=:id"), {"id": question_id}
            )
            assert (
                connection.scalar(
                    text("SELECT COUNT(*) FROM question_options WHERE question_id=:id"),
                    {"id": question_id},
                )
                == 0
            )
            assert (
                connection.scalar(
                    text("SELECT COUNT(*) FROM quiz_questions WHERE question_id=:id"),
                    {"id": question_id},
                )
                == 0
            )
        print(
            "Quiz foundation migration preserved data, restored defaults, and verified FK deletion behavior."
        )
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()
