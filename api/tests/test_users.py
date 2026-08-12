"""Tests for user management and API keys."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import signup


def test_admin_lists_users(client: TestClient, admin_headers: dict[str, str]) -> None:
    signup(client)
    r = client.get("/api/v1/users", headers=admin_headers)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert "user@example.com" in emails and "admin@jyoti.local" in emails


def test_non_admin_cannot_list_users(client: TestClient) -> None:
    body = signup(client)
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.get("/api/v1/users", headers=headers).status_code == 403


def test_admin_approves_pending_user(client: TestClient, admin_headers: dict[str, str]) -> None:
    signup(client)
    r = client.get("/api/v1/users", headers=admin_headers)
    target = next(u for u in r.json() if u["email"] == "user@example.com")
    assert target["role"] == "pending"
    r = client.patch(f"/api/v1/users/{target['id']}", json={"role": "user"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "user"


def test_admin_creates_user(client: TestClient, admin_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/v1/users",
        json={"name": "New", "email": "new@example.com", "password": "secret123", "role": "user"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "user"


def test_update_own_profile(client: TestClient) -> None:
    signup(client)
    r = client.patch("/api/v1/users/me", json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


def test_api_key_lifecycle(client: TestClient) -> None:
    signup(client)
    r = client.post("/api/v1/users/api-keys", json={"name": "ci"})
    assert r.status_code == 200
    key = r.json()["key"]
    assert key.startswith("jyoti-")

    # key works for auth on a protected endpoint
    r = client.get("/api/v1/auth/session", headers={"Authorization": f"Key {key}"})
    assert r.status_code == 200

    r = client.get("/api/v1/users/api-keys")
    assert len(r.json()) == 1
    key_id = r.json()[0]["id"]

    r = client.delete(f"/api/v1/users/api-keys/{key_id}")
    assert r.status_code == 200

    r = client.get("/api/v1/auth/session", headers={"Authorization": f"Key {key}"})
    assert r.status_code == 401
