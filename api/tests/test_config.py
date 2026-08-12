"""Tests for the config/settings endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import signup


def test_public_config_shape(client: TestClient) -> None:
    signup(client)
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    data = r.json()
    assert data["app"]["name"] == "JyotiGPT"
    assert data["auth"]["enable_signup"] is True
    assert "image_generation" in data["features"]


def test_settings_require_admin(client: TestClient) -> None:
    signup(client)
    assert client.get("/api/v1/config/settings").status_code == 403


def test_admin_set_and_get_settings(client: TestClient, admin_headers: dict[str, str]) -> None:
    r = client.get("/api/v1/config/settings", headers=admin_headers)
    assert r.status_code == 200
    assert "features" in r.json()

    r = client.post(
        "/api/v1/config/settings",
        json={"key": "features", "value": {"image_generation": True}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    r = client.get("/api/v1/config/settings", headers=admin_headers)
    assert r.json()["features"]["image_generation"] is True
