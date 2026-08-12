"""Speech-to-text: provider STT (OpenAI Whisper) via /api/v1/stt/*.

The browser Web Speech API does its transcription entirely in the browser, so
the STT endpoints only exist for provider-based engines (OpenAI-compatible
``/audio/transcriptions``). The engine is chosen by ``AUDIO_STT_ENGINE``;
``browser`` means the client does the work and never calls these routes.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, UploadFile

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.errors import BadGatewayError

router = APIRouter(prefix="/api/v1/stt", tags=["stt"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Whisper's 25 MB request cap


async def _stt_openai(
    *, api_key: str, base_url: str, model: str, audio: bytes, lang: str | None
) -> str:
    """Transcribe ``audio`` via an OpenAI-compatible /audio/transcriptions."""
    files = {"file": ("audio.webm", audio, "audio/webm")}
    data: dict[str, str] = {"model": model}
    if lang:
        data["language"] = lang
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, read=120.0)) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise BadGatewayError(f"STT request failed: {exc}") from exc
    text = payload.get("text", "") if isinstance(payload, dict) else ""
    return text.strip()


@router.post("/transcriptions")
async def transcribe(
    file: UploadFile,
    user: CurrentUser,
    session: SessionDep,  # noqa: ARG001 — reserved for auth-scoped STT
    lang: str | None = None,
) -> dict[str, Any]:
    """Transcribe an uploaded audio file; requires AUDIO_STT_ENGINE=openai."""
    settings = get_settings()
    if settings.audio_stt_engine != "openai":
        raise BadGatewayError(
            "Provider STT is not enabled (set AUDIO_STT_ENGINE=openai)."
        )
    api_key = settings.audio_stt_openai_api_key or settings.openai_api_key
    if not api_key:
        raise BadGatewayError("OpenAI is not configured (OPENAI_API_KEY is empty).")
    audio = await file.read()
    if not audio:
        raise BadGatewayError("Empty audio upload.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise BadGatewayError("Audio file exceeds the 25 MB limit.")
    text = await _stt_openai(
        api_key=api_key,
        base_url=settings.audio_stt_openai_base_url or settings.openai_api_base_url,
        model=settings.audio_stt_openai_model or "whisper-1",
        audio=audio,
        lang=lang,
    )
    return {"text": text, "engine": "openai"}
