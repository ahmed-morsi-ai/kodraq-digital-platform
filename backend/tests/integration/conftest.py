import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def migration_database(test_engine):
    name = f"kodraq_project_migration_{uuid4().hex}"
    admin = create_engine(
        test_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(test_engine.url.set(database=name))

    def migrate(operation, revision, *, succeeds=True):
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
        if succeeds:
            print(
                f"alembic {operation} {revision}\n{result.stdout}{result.stderr}Exit code: {result.returncode}"
            )
            assert result.returncode == 0
        else:
            assert result.returncode != 0
        return result

    try:
        yield engine, migrate
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()
