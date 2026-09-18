from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://kodraq_user:kodraq_secure_password@localhost:5432/kodraq_test_db",
)

ADMIN_DATABASE_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql://kodraq_user:kodraq_secure_password@localhost:5432/postgres",
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Safety guard: Ensure TEST_DATABASE_URL points strictly to kodraq_test_db
    test_url = make_url(TEST_DATABASE_URL)
    database_name = test_url.database
    if database_name != "kodraq_test_db":
        raise RuntimeError(
            "Refusing to run tests because TEST_DATABASE_URL database "
            f"name is '{database_name}', not 'kodraq_test_db'."
        )

    # Connect to administrative database to ensure kodraq_test_db exists
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'kodraq_test_db'")
        )
        exists = result.scalar()
        if not exists:
            conn.execute(text("CREATE DATABASE kodraq_test_db"))
    admin_engine.dispose()

    # Create test engine and tables
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield test_engine

    test_engine.dispose()


@pytest.fixture(scope="session")
def test_engine(setup_test_database):
    return setup_test_database


@pytest.fixture(scope="function")
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
