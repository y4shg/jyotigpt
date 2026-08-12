"""Shared test fixtures: a fresh app + client per test with isolated data."""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ["DATA_DIR"] = os.path.join(
    tempfile.gettempdir(), f"jyoti_tests_{uuid.uuid4().hex[:8]}"
)
os.environ["JYOTIGPT_JWT_SECRET_KEY"] = uuid.uuid4().hex + uuid.uuid4().hex


@pytest.fixture(autouse=True)
def _clean_database():
    """Drop and recreate all tables before each test for full isolation."""
    from jyoti_api.persistence import schema  # noqa: F401
    from jyoti_api.persistence.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client() -> Iterator[TestClient]:
    from jyoti_api.app import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/signin", json={"email": "admin@jyoti.local", "password": "admin"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def signup(client: TestClient, email: str = "user@example.com", name: str = "User") -> dict:
    r = client.post(
        "/api/v1/auth/signup",
        json={"name": name, "email": email, "password": "secret123"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def user_headers(client: TestClient) -> dict[str, str]:
    body = signup(client)
    return {"Authorization": f"Bearer {body['token']}"}
