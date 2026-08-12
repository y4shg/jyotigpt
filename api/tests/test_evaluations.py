"""Tests for evaluations: config gating + feedback CRUD/ownership."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import signup


def _user_headers(client: TestClient, email: str = "user@example.com") -> dict[str, str]:
    body = signup(client, email=email)
    return {"Authorization": f"Bearer {body['token']}"}


# ---------------------------------------------------------------- config


def test_config_defaults_and_readable_by_any_user(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    r = client.get("/api/v1/evaluations/config", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == {"enable_evaluations": False, "model": ""}

    r = client.get("/api/v1/evaluations/config", headers=_user_headers(client))
    assert r.status_code == 200


def test_config_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/evaluations/config").status_code == 401


def test_config_write_is_admin_only(client: TestClient) -> None:
    r = client.post(
        "/api/v1/evaluations/config",
        json={"enable_evaluations": True, "model": "eval-model"},
        headers=_user_headers(client),
    )
    assert r.status_code == 403


def test_config_write_persists(client: TestClient, admin_headers: dict[str, str]) -> None:
    r = client.post(
        "/api/v1/evaluations/config",
        json={"enable_evaluations": True, "model": "eval-model"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    r = client.get("/api/v1/evaluations/config", headers=admin_headers)
    assert r.json() == {"enable_evaluations": True, "model": "eval-model"}


# ---------------------------------------------------------------- feedback


def test_feedback_create_and_versioning(client: TestClient) -> None:
    headers = _user_headers(client)
    r = client.post(
        "/api/v1/evaluations/feedback",
        json={
            "type": "rating",
            "data": {"rating": 5, "model_id": "m", "comment": "great"},
            "meta": {"chat_id": "c1", "message_id": "m1"},
        },
        headers=headers,
    )
    assert r.status_code == 201
    fb = r.json()
    assert fb["version"] == 0 and fb["data"]["rating"] == 5

    r = client.post(
        f"/api/v1/evaluations/feedback/{fb['id']}",
        json={"data": {"rating": 3}},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 1
    assert r.json()["data"]["rating"] == 3


def test_feedback_ownership_isolation(client: TestClient) -> None:
    a = _user_headers(client, "a@example.com")
    b = _user_headers(client, "b@example.com")
    r = client.post(
        "/api/v1/evaluations/feedback",
        json={"type": "rating", "data": {"rating": 1}, "meta": {}},
        headers=a,
    )
    fb_id = r.json()["id"]

    assert client.get(f"/api/v1/evaluations/feedback/{fb_id}", headers=b).status_code == 404
    assert client.delete(f"/api/v1/evaluations/feedback/{fb_id}", headers=b).status_code == 404

    assert client.get("/api/v1/evaluations/feedbacks/user", headers=a).status_code == 200
    assert len(client.get("/api/v1/evaluations/feedbacks/user", headers=a).json()) == 1
    assert client.get("/api/v1/evaluations/feedbacks/user", headers=b).json() == []


def test_user_cannot_access_all_feedbacks(client: TestClient) -> None:
    headers = _user_headers(client)
    assert client.get("/api/v1/evaluations/feedbacks/all", headers=headers).status_code == 403
    assert client.delete("/api/v1/evaluations/feedbacks/all", headers=headers).status_code == 403


def test_admin_lists_and_clears_all(client: TestClient, admin_headers: dict[str, str]) -> None:
    for email in ("a@example.com", "b@example.com"):
        headers = _user_headers(client, email)
        client.post(
            "/api/v1/evaluations/feedback",
            json={"type": "rating", "data": {"rating": 4}, "meta": {}},
            headers=headers,
        )

    r = client.get("/api/v1/evaluations/feedbacks/all", headers=admin_headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert {"id", "user_id", "version", "type", "data", "meta"} <= set(rows[0])
    assert rows[0]["user"]["email"] in ("a@example.com", "b@example.com")

    assert client.get("/api/v1/evaluations/feedbacks/all/export", headers=admin_headers).status_code == 200

    assert client.delete("/api/v1/evaluations/feedbacks/all", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/evaluations/feedbacks/all", headers=admin_headers).json() == []


def test_user_deletes_own_feedbacks(client: TestClient) -> None:
    headers = _user_headers(client)
    client.post(
        "/api/v1/evaluations/feedback",
        json={"type": "rating", "data": {"rating": 2}, "meta": {}},
        headers=headers,
    )
    assert client.delete("/api/v1/evaluations/feedbacks", headers=headers).status_code == 200
    assert client.get("/api/v1/evaluations/feedbacks/user", headers=headers).json() == []
