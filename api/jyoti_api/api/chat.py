"""Chat completions: /api/v1/chat/completions (SSE).

The completions endpoint streams model output as Server-Sent Events. When a
``conversation_id`` is given the exchange is persisted: an assistant message
row is created up front (so the client has a stable id to reference) and
filled in when the stream finishes. If the client disconnects early the
partial reply is saved so the conversation stays consistent.

Custom model presets (``ModelRecord``) are resolved server-side: their system
prompt, attached collections (RAG context), and prompt plugins are applied
here, and the flow-server inlet/outlet hooks wrap the exchange when a
pipeline is selected.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.domain import conversations, models
from jyoti_api.integrations.providers import ProviderError, stream_chat
from jyoti_api.persistence.schema import Conversation
from jyoti_api.retrieval.search import search_collections, to_context
from jyoti_api.services import flows

logger = logging.getLogger("jyoti_api")
router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    model: str
    provider: str = "ollama"  # ollama | openai | flow
    conversation_id: str | None = None
    messages: list[dict[str, str]] = []  # used only for stateless (playground) streams
    params: dict[str, Any] = {}
    pipeline: str | None = None  # flow pipeline id (provider == "flow")


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _last_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return message["content"]
    return ""


async def _build_context(
    session: SessionDep,
    user: CurrentUser,
    *,
    provider: str,
    model: str,
    history: list[dict[str, str]],
    body_params: dict[str, Any],
) -> list[dict[str, str]]:
    """Apply custom-model params, RAG context, and prompt plugins to history."""
    settings = get_settings()
    record_params = models.resolve_record_params(session, provider, model)
    params = {**record_params, **body_params}

    context: list[dict[str, str]] = list(history)
    system_parts: list[str] = []
    if params.get("system"):
        system_parts.append(params["system"])

    # RAG: search the model's attached collections with the latest user line.
    collection_ids = params.get("collection_ids") or []
    if settings.enable_rag and collection_ids:
        try:
            results = await search_collections(
                session,
                settings,
                user_id=user.id,
                collection_ids=[str(c) for c in collection_ids],
                query=_last_user_message(context),
            )
            block = to_context(results)
            if block:
                system_parts.append(
                    "Use the following retrieved context when it is relevant "
                    "to the question:\n" + block
                )
        except Exception:  # pragma: no cover - retrieval must never block chat
            logger.debug("RAG context failed", exc_info=True)

    # Prompt plugins: append each enabled plugin's prompt text.
    plugin_ids = params.get("plugin_ids") or []
    if plugin_ids:
        from jyoti_api.persistence.schema import Plugin

        rows = session.query(Plugin).filter(
            Plugin.id.in_([str(p) for p in plugin_ids]),
            Plugin.user_id == user.id,
            Plugin.kind == "prompt",
            Plugin.is_active.is_(True),
        ).all()
        for plugin in rows:
            if plugin.prompt.strip():
                system_parts.append(plugin.prompt)

    if system_parts:
        system = {"role": "system", "content": "\n\n".join(p for p in system_parts if p)}
        context = [system, *[m for m in context if m["role"] != "system"]]
    return context


# ---------------------------------------------------------------------- chat


@router.post("/chat/completions")
async def chat_completions(
    body: ChatRequest, request: Request, user: CurrentUser, session: SessionDep
) -> StreamingResponse:
    settings = get_settings()
    conversation: Conversation | None = None
    if body.conversation_id:
        conversation = conversations.get_conversation(session, user.id, body.conversation_id)
        history = conversations.list_messages(session, user.id, body.conversation_id)
        history_messages: list[dict[str, str]] = [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if m["role"] in ("user", "assistant") and m["content"]
        ]
    else:
        history_messages = body.messages

    async def event_stream() -> AsyncIterator[str]:
        # Assistant message row: created up front when we are persisting.
        message_id = None
        if conversation is not None:
            row = conversations.add_message(
                session,
                user.id,
                conversation.id,
                role="assistant",
                content="",
                model=body.model,
                provider=body.provider,
            )
            message_id = row.id
            conversations.update_message(session, user.id, message_id, done=False)
            yield _sse("start", {"message_id": message_id})
        else:
            yield _sse("start", {"message_id": None})

        persisted = False
        try:
            context = await _build_context(
                session,
                user,
                provider=body.provider,
                model=body.model,
                history=history_messages,
                body_params=body.params,
            )

            # Flow inlet hook: the pipeline may rewrite the request payload.
            if body.pipeline:
                inlet = await flows.run_inlet(
                    session,
                    settings,
                    pipeline=body.pipeline,
                    payload={
                        "model": body.model,
                        "messages": context,
                        "params": body.params,
                    },
                )
                if isinstance(inlet.get("messages"), list):
                    context = inlet["messages"]

            content_parts: list[str] = []
            if body.provider == "flow" and body.pipeline:
                async for delta in flows.stream_flow(
                    session, settings, pipeline=body.pipeline, messages=context, model=body.model
                ):
                    if await request.is_disconnected():
                        break
                    content_parts.append(delta)
                    yield _sse("delta", {"content": delta})
            else:
                provider = "openai" if body.provider == "openai" else "ollama"
                async for delta in stream_chat(
                    settings,
                    provider=provider,
                    model=body.model,
                    messages=context,
                    params=body.params,
                ):
                    if await request.is_disconnected():
                        break
                    content_parts.append(delta)
                    yield _sse("delta", {"content": delta})

            full = "".join(content_parts)

            # Flow outlet hook: the pipeline may rewrite the response.
            if body.pipeline:
                outlet = await flows.run_outlet(
                    session,
                    settings,
                    pipeline=body.pipeline,
                    payload={"model": body.model, "messages": context, "response": full},
                )
                if isinstance(outlet.get("response"), str):
                    full = outlet["response"]

            if conversation is not None and message_id is not None:
                if await request.is_disconnected():
                    # client went away mid-stream: keep the partial reply
                    conversations.update_message(session, user.id, message_id, content=full, done=False)
                else:
                    conversations.update_message(session, user.id, message_id, content=full, done=True)
            persisted = True
            yield _sse("done", {"message_id": message_id, "content": full})
        except ProviderError as exc:
            if conversation is not None and message_id is not None:
                conversations.update_message(
                    session, user.id, message_id, content="", done=True, error=str(exc)
                )
            persisted = True
            yield _sse("error", {"message": str(exc)})
        finally:
            # Cancelled before a clean finish: save whatever streamed so far.
            if conversation is not None and message_id is not None and not persisted:
                try:
                    conversations.update_message(
                        session, user.id, message_id, content="".join(content_parts), done=False
                    )
                except Exception:  # pragma: no cover - defensive
                    logger.debug("could not persist partial reply", exc_info=True)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
