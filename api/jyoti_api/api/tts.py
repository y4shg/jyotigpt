"""Text-to-speech: provider TTS (OpenAI-compatible /audio/speech).

The browser Web Speech API synthesizes speech client-side, so these routes
only serve provider-based engines. The engine is chosen by ``AUDIO_TTS_ENGINE``
(``openai``); ``browser`` means the client speaks without calling the API.
Responses are audio/octet-stream so any TTS provider (OpenAI mp3, etc.) can
be returned verbatim.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser
from jyoti_api.config import get_settings
from jyoti_api.errors import BadGatewayError

router = APIRouter(prefix="/api/v1/tts", tags=["tts"])

MAX_TEXT_CHARS = 4000


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    voice: str = ""  # empty -> config default
    speed: float = Field(default=1.0, ge=0.25, le=4.0)


async def _tts_openai(
    *, api_key: str, base_url: str, model: str, voice: str, text: str, speed: float
) -> bytes:
    body = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "speed": speed,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, read=120.0)) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/audio/speech",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise BadGatewayError(f"TTS request failed: {exc}") from exc
    return response.content


@router.post("/speech")
async def synthesize(
    body: TTSRequest, user: CurrentUser
) -> Response:
    """Synthesize speech for ``text``; requires AUDIO_TTS_ENGINE=openai."""
    settings = get_settings()
    if settings.audio_tts_engine != "openai":
        raise BadGatewayError("Provider TTS is not enabled (set AUDIO_TTS_ENGINE=openai).")
    api_key = settings.audio_tts_openai_api_key or settings.openai_api_key
    if not api_key:
        raise BadGatewayError("OpenAI is not configured (OPENAI_API_KEY is empty).")
    voice = body.voice or settings.audio_tts_openai_voice or "alloy"
    audio = await _tts_openai(
        api_key=api_key,
        base_url=settings.audio_tts_openai_base_url or settings.openai_api_base_url,
        model=settings.audio_tts_openai_model or "tts-1",
        voice=voice,
        text=body.text,
        speed=body.speed,
    )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store", "Content-Disposition": 'inline; filename="speech.mp3"'},
    )
