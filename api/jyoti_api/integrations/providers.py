"""Model providers: upstream discovery (Ollama / OpenAI-compatible) and streaming.

Each ``stream_*`` async generator yields text deltas as they arrive and raises
``ProviderError`` on transport/auth failures. Consumers drive the stream to
completion (or stop early on client disconnect); providers never persist
anything themselves.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from jyoti_api.config import Settings


class ProviderError(Exception):
    """Raised when an upstream model provider cannot be reached or answers badly."""


async def _discovery_timeout() -> float:
    return 5.0


# ------------------------------------------------------------------ discovery


async def list_ollama_models(settings: Settings) -> list[dict[str, Any]]:
    """List local Ollama models; an unreachable daemon yields an empty list."""
    try:
        async with httpx.AsyncClient(timeout=await _discovery_timeout()) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
    except httpx.HTTPError:
        return []
    result = []
    for model in models:
        details = model.get("details", {})
        result.append(
            {
                "id": model.get("name", ""),
                "name": model.get("name", ""),
                "provider": "ollama",
                "owned_by": "ollama",
                "ollama": {
                    "size": model.get("size"),
                    "parameter_size": details.get("parameter_size", ""),
                    "quantization_level": details.get("quantization_level", ""),
                    "family": details.get("family", ""),
                    "modified_at": model.get("modified_at"),
                },
                "info": {
                    "meta": {
                        "profile_image_url": "",
                        "description": model.get("description", ""),
                    }
                },
            }
        )
    return result


async def list_openai_models(settings: Settings) -> list[dict[str, Any]]:
    """List OpenAI-compatible models; requires an API key (or a local server)."""
    if not settings.openai_api_key:
        return []
    allowed = {m.strip() for m in settings.openai_api_models.split(",") if m.strip()}
    try:
        async with httpx.AsyncClient(timeout=await _discovery_timeout()) as client:
            response = await client.get(
                f"{settings.openai_api_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            )
        response.raise_for_status()
        models = response.json().get("data", [])
    except httpx.HTTPError:
        return []
    result = []
    for model in models:
        model_id = model.get("id", "")
        if allowed and model_id not in allowed:
            continue
        result.append(
            {
                "id": model_id,
                "name": model.get("name") or model_id,
                "provider": "openai",
                "owned_by": "openai",
                "info": {
                    "meta": {
                        "profile_image_url": "",
                        "description": model.get("description", ""),
                    }
                },
            }
        )
    return result


# ------------------------------------------------------------------- streaming


async def stream_chat(
    settings: Settings,
    *,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    params: dict[str, Any] | None,
) -> AsyncIterator[str]:
    """Stream assistant text deltas for ``messages`` from the chosen provider."""
    params = params or {}
    if provider == "openai":
        if not settings.openai_api_key:
            raise ProviderError("OpenAI is not configured (OPENAI_API_KEY is empty).")
        async for delta in _stream_openai(settings, model, messages, params):
            yield delta
    else:
        async for delta in _stream_ollama(settings, model, messages, params):
            yield delta


async def _stream_ollama(
    settings: Settings,
    model: str,
    messages: list[dict[str, str]],
    params: dict[str, Any],
) -> AsyncIterator[str]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {},
    }
    ollama_options = {
        "temperature": params.get("temperature"),
        "top_p": params.get("top_p"),
        "top_k": params.get("top_k"),
        "seed": params.get("seed"),
        "num_predict": params.get("max_tokens") or params.get("num_predict"),
    }
    body["options"] = {k: v for k, v in ollama_options.items() if v is not None}
    if settings.ollama_num_predict != -1 and "num_predict" not in body["options"]:
        body["options"]["num_predict"] = settings.ollama_num_predict
    if settings.ollama_keep_alive:
        body["keep_alive"] = settings.ollama_keep_alive

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.openai_request_timeout, read=None)
        ) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        payload = json_loads(line)
                    except ValueError:
                        continue
                    if payload.get("done"):
                        return
                    yield payload.get("message", {}).get("content", "")
    except httpx.HTTPError as exc:
        raise ProviderError(f"Ollama request failed: {exc}") from exc


async def _stream_openai(
    settings: Settings,
    model: str,
    messages: list[dict[str, str]],
    params: dict[str, Any],
) -> AsyncIterator[str]:
    body: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    for key in ("temperature", "top_p", "max_tokens", "seed", "stop", "presence_penalty", "frequency_penalty"):
        if params.get(key) is not None:
            body[key] = params[key]
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    if "openai.com" not in settings.openai_api_base_url:
        headers["api-key"] = settings.openai_api_key
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.openai_request_timeout, read=None)
        ) as client:
            async with client.stream(
                "POST",
                f"{settings.openai_api_base_url.rstrip('/')}/chat/completions",
                json=body,
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        return
                    try:
                        chunk = json_loads(data)
                    except ValueError:
                        continue
                    choices = chunk.get("choices") or []
                    delta = choices[0].get("delta", {}) if choices else {}
                    text = delta.get("content", "") or delta.get("reasoning_content", "")
                    if text:
                        yield text
    except httpx.HTTPError as exc:
        raise ProviderError(f"OpenAI request failed: {exc}") from exc


def json_loads(line: str) -> Any:
    import json

    return json.loads(line)
