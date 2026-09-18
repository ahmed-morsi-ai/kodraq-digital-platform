from __future__ import annotations

from fastapi import status


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


def test_user_registration_and_duplicates(client):
    user_payload = {
        "email": "testuser@kodraq.com",
        "password": "SecurePassword123!",
        "full_name": "Test User",
    }
    # 1. Successful registration
    response = client.post("/api/v1/users", json=user_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == user_payload["email"]
    assert "id" in data

    # 2. Duplicate email registration rejection
    response_dup = client.post("/api/v1/users", json=user_payload)
    assert response_dup.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response_dup.json()["detail"].lower()


def test_login_access_token(client):
    user_payload = {
        "email": "loginuser@kodraq.com",
        "password": "LoginPassword123!",
        "full_name": "Login User",
    }
    client.post("/api/v1/users", json=user_payload)

    # 1. Successful login
    form_data = {
        "username": user_payload["email"],
        "password": user_payload["password"],
    }
    response = client.post("/api/v1/login/access-token", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. Invalid password login failure
    invalid_form = {
        "username": user_payload["email"],
        "password": "WrongPassword",
    }
    response_fail = client.post("/api/v1/login/access-token", data=invalid_form)
    assert response_fail.status_code == status.HTTP_400_BAD_REQUEST


def test_user_me_endpoints(client):
    user_payload = {
        "email": "meuser@kodraq.com",
        "password": "MePassword123!",
        "full_name": "Me User",
    }
    client.post("/api/v1/users", json=user_payload)

    # Obtain token
    login_res = client.post(
        "/api/v1/login/access-token",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get /users/me
    me_res = client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == status.HTTP_200_OK
    assert me_res.json()["email"] == user_payload["email"]

    # 2. Put /users/me (update profile)
    update_res = client.put(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "Updated Full Name"},
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["full_name"] == "Updated Full Name"


def test_superuser_listing_permissions(client):
    # Create regular user
    reg_payload = {
        "email": "regular@kodraq.com",
        "password": "Password123!",
        "full_name": "Regular User",
    }
    client.post("/api/v1/users", json=reg_payload)
    reg_login = client.post(
        "/api/v1/login/access-token",
        data={"username": reg_payload["email"], "password": reg_payload["password"]},
    )
    reg_headers = {"Authorization": f"Bearer {reg_login.json()['access_token']}"}

    # Regular user trying to list users -> forbidden
    forbidden_res = client.get("/api/v1/users", headers=reg_headers)
    assert forbidden_res.status_code == status.HTTP_403_FORBIDDEN
