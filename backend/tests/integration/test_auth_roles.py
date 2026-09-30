from __future__ import annotations

import pytest


@pytest.mark.parametrize("role", ["student", "client"])
def test_registration_persists_role_and_returns_it_from_me(client, role):
    payload = {
        "email": f"{role}@roles.local",
        "full_name": f"{role.title()} Account",
        "password": "SecurePassword123!",
        "role": role,
    }

    registration = client.post("/api/v1/users", json=payload)
    assert registration.status_code == 201
    assert registration.json()["role_name"] == role
    assert registration.json()["is_superuser"] is False

    login = client.post(
        "/api/v1/login/access-token",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    profile = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["role_name"] == role


def test_public_registration_cannot_assign_privileged_role_or_flags(client):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "untrusted@roles.local",
            "full_name": "Untrusted Account",
            "password": "SecurePassword123!",
            "role": "instructor",
            "role_id": 1,
            "is_superuser": True,
        },
    )
    assert response.status_code == 422