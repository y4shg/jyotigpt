"""Tests for Phase 8: provider STT/TTS + web search endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from jyoti_api.config import get_settings
from tests.conftest import signup


def _user_headers(client: TestClient) -> dict[str, str]:
    body = signup(client)
    return {"Authorization": f"Bearer {body['token']}"}


# --------------------------------------------------------------------- STT


def test_stt_rejected_when_engine_off(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "audio_stt_engine", "")
    r = client.post(
        "/api/v1/stt/transcriptions",
        headers=_user_headers(client),
        files={"file": ("audio.webm", b"\x1a\x45\xdf\xa3" * 10, "audio/webm")},
    )
    assert r.status_code == 502
    assert "not enabled" in r.json()["detail"]


def test_stt_openai_happy_path(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "audio_stt_engine", "openai")
    monkeypatch.setattr(settings, "audio_stt_openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "audio_stt_openai_base_url", "https://api.openai.com/v1")

    import httpx

    class FakeResponse:
        def __init__(self, text: str = ""):
            self._text = text

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"text": self._text}

    async def fake_post(self, *args, **kwargs):  # noqa: ANN001
        return FakeResponse("hello world")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    r = client.post(
        "/api/v1/stt/transcriptions",
        headers=_user_headers(client),
        files={"file": ("audio.webm", b"\x00" * 1024, "audio/webm")},
    )
    assert r.status_code == 200
    assert r.json()["text"] == "hello world"


# --------------------------------------------------------------------- TTS


def test_tts_rejected_when_engine_off(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "audio_tts_engine", "")
    r = client.post(
        "/api/v1/tts/speech",
        headers=_user_headers(client),
        json={"text": "hello"},
    )
    assert r.status_code == 502
    assert "not enabled" in r.json()["detail"]


def test_tts_openai_happy_path(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "audio_tts_engine", "openai")
    monkeypatch.setattr(settings, "audio_tts_openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "audio_tts_openai_base_url", "https://api.openai.com/v1")

    import httpx

    class FakeResponse:
        content = b"\xff\xf3\x00ID3" * 100  # fake mp3 bytes

        def raise_for_status(self) -> None:
            return None

    async def fake_post(self, *args, **kwargs):  # noqa: ANN001
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    r = client.post(
        "/api/v1/tts/speech",
        headers=_user_headers(client),
        json={"text": "hello world", "speed": 1.2},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content.startswith(b"\xff\xf3\x00ID3")


def test_tts_empty_text_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/v1/tts/speech",
        headers=_user_headers(client),
        json={"text": ""},
    )
    assert r.status_code == 422


# ------------------------------------------------------------------ search


def test_web_search_disabled(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_web_search", False)
    r = client.get("/api/v1/search/web?q=hello", headers=_user_headers(client))
    assert r.status_code == 502
    assert "disabled" in r.json()["detail"]


def test_web_search_missing_searxng(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_web_search", True)
    monkeypatch.setattr(settings, "searxng_query_url", "")
    r = client.get("/api/v1/search/web?q=hello", headers=_user_headers(client))
    assert r.status_code == 502
    assert "SEARXNG_QUERY_URL" in r.json()["detail"]


def test_web_search_happy_path(client: TestClient, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_web_search", True)
    monkeypatch.setattr(settings, "searxng_query_url", "https://search.example/json")
    monkeypatch.setattr(settings, "web_search_result_count", 5)

    import httpx

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/a",
                        "title": "Result A",
                        "content": "A description",
                    },
                    {"url": "https://example.com/b", "title": "Result B"},
                    {"url": "", "title": "No URL"},  # dropped
                ]
            }

    async def fake_get(self, *args, **kwargs):  # noqa: ANN001
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    r = client.get("/api/v1/search/web?q=hello", headers=_user_headers(client))
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "hello"
    assert len(data["results"]) == 2
    assert data["results"][0]["title"] == "Result A"
    assert data["results"][0]["url"] == "https://example.com/a"
