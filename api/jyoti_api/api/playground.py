"""Playground endpoint: ad-hoc completions for the /playground lab.

Streams the same provider path as chat, without persisting a conversation —
the lab is a scratchpad, not a chat history. Events mirror the chat SSE
shape (start / delta / done / error).
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser
from jyoti_api.config import get_settings
from jyoti_api.errors import ValidationError
from jyoti_api.integrations.providers import ProviderError, stream_chat

router = APIRouter(prefix="/api/v1/playground", tags=["playground"])


class PlaygroundRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    provider: str = Field(default="ollama", pattern="^(ollama|openai|flow)$")
    messages: list[dict[str, str]] = Field(min_length=1, max_length=200)
    params: dict[str, Any] = Field(default_factory=dict)


def _sse(event: str, data: dict[str, Any]) -> str:
    import json

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/completions")
async def playground_completions(
    body: PlaygroundRequest, request: Request, user: CurrentUser
) -> StreamingResponse:
    settings = get_settings()
    cleaned: list[dict[str, str]] = [
        {"role": m.get("role", "user"), "content": (m.get("content") or "").strip()}
        for m in body.messages
        if m.get("role") in ("system", "user", "assistant") and (m.get("content") or "").strip()
    ]
    if not cleaned:
        raise ValidationError("At least one non-empty message is required.")

    async def event_stream() -> AsyncIterator[str]:
        yield _sse("start", {})
        try:
            provider = "openai" if body.provider == "openai" else "ollama"
            async for delta in stream_chat(
                settings,
                provider=provider,
                model=body.model,
                messages=cleaned,
                params=body.params,
            ):
                if await request.is_disconnected():
                    break
                if delta:
                    yield _sse("delta", {"content": delta})
            yield _sse("done", {})
        except ProviderError as exc:
            yield _sse("error", {"message": str(exc)})
        except Exception as exc:  # noqa: BLE001 — never hang the lab on an unexpected failure
            yield _sse("error", {"message": f"Playground error: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
