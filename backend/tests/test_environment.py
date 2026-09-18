from __future__ import annotations

from sqlalchemy import inspect, text


def test_db_connection(db_session):
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_tables_exist(db_session):
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    assert "roles" in tables
    assert "users" in tables


def test_client_smoke(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
