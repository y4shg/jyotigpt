"""Tests for the auth endpoints and session flow."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import signup


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_signup_creates_pending_user(client: TestClient) -> None:
    body = signup(client)
    assert body["user"]["role"] == "pending"
    assert body["user"]["email"] == "user@example.com"
    assert "token" in body


def test_signup_duplicate_email_rejected(client: TestClient) -> None:
    signup(client)
    r = client.post(
        "/api/v1/auth/signup",
        json={"name": "Other", "email": "user@example.com", "password": "secret123"},
    )
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"]


def test_session_endpoint(client: TestClient) -> None:
    signup(client)
    r = client.get("/api/v1/auth/session")
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "user@example.com"


def test_signin_wrong_password(client: TestClient) -> None:
    signup(client)
    r = client.post(
        "/api/v1/auth/signin",
        json={"email": "user@example.com", "password": "wrong-pass"},
    )
    assert r.status_code == 401


def test_signout_invalidates_session(client: TestClient) -> None:
    signup(client)
    r = client.post("/api/v1/auth/signout")
    assert r.status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 401


def test_protected_route_requires_auth(client: TestClient) -> None:
    # /api/v1/config is public by design (the sign-in page reads enable_signup /
    # enable_ldap before authenticating); everything under /auth is protected.
    assert client.get("/api/v1/config").status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 401


def test_deactivated_user_cannot_signin(client: TestClient, admin_headers: dict[str, str]) -> None:
    signup(client, email="deact@example.com")
    r = client.get("/api/v1/users", headers=admin_headers)
    target = next(u for u in r.json() if u["email"] == "deact@example.com")
    r = client.patch(f"/api/v1/users/{target['id']}", json={"status": "deactivated"}, headers=admin_headers)
    assert r.status_code == 200
    r = client.post(
        "/api/v1/auth/signin", json={"email": "deact@example.com", "password": "secret123"}
    )
    assert r.status_code == 401
