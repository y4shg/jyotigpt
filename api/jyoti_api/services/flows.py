"""Flows (the pipeline/plugin-server integration).

A flow server exposes custom pipelines that can pre-process chat traffic
(inlet) and post-process responses (outlet). Configuration lives in the
``settings`` table under the ``flows`` key and is admin-managed. Hooks are
fail-open: an unreachable flow server never blocks chat, the original
payload is passed through.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx
from sqlalchemy.orm import Session

from jyoti_api.config import Settings
from jyoti_api.errors import ValidationError
from jyoti_api.integrations.providers import ProviderError
from jyoti_api.persistence.schema import AppSetting

FLOWS_KEY = "flows"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "url": "",
    "api_key": "",
    "inlet_enabled": True,
    "outlet_enabled": True,
    "pipelines": [],
}


def get_flows_config(session: Session) -> dict[str, Any]:
    row = session.get(AppSetting, FLOWS_KEY)
    config = dict(DEFAULT_CONFIG)
    if row and isinstance(row.value, dict):
        config.update({k: v for k, v in row.value.items() if k in DEFAULT_CONFIG})
    return config


def save_flows_config(session: Session, config: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, default in DEFAULT_CONFIG.items():
        if key not in config:
            clean[key] = default
            continue
        value = config[key]
        if key == "url":
            value = (str(value) or "").strip().rstrip("/")
        elif key == "api_key":
            value = str(value or "").strip()
        elif key == "enabled" or key.endswith("_enabled"):
            value = bool(value)
        elif key == "pipelines":
            value = value if isinstance(value, list) else []
        clean[key] = value
    if clean["enabled"] and not clean["url"]:
        raise ValidationError("A flow server URL is required when flows are enabled.")
    row = session.get(AppSetting, FLOWS_KEY)
    if row is None:
        row = AppSetting(key=FLOWS_KEY, value=clean)
        session.add(row)
    else:
        row.value = clean
        session.add(row)
    session.commit()
    return get_flows_config(session)


def flows_enabled(session: Session) -> bool:
    return bool(get_flows_config(session).get("enabled"))


async def _request(
    session: Session, settings: Settings, method: str, path: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    config = get_flows_config(session)
    if not config.get("enabled") or not config.get("url"):
        return None
    url = f"{config['url']}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    if config.get("api_key"):
        headers["Authorization"] = f"Bearer {config['api_key']}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(method, url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"result": data}
    except (httpx.HTTPError, ValueError):
        return None


async def list_pipelines(session: Session, settings: Settings) -> list[dict[str, Any]]:
    """Fetch the pipelines served by the configured flow server."""
    config = get_flows_config(session)
    if not config.get("enabled") or not config.get("url"):
        return []
    result = await _request(session, settings, "GET", "pipelines", {})
    if not result:
        return []
    pipelines = result.get("pipelines")
    if not isinstance(pipelines, list):
        return []
    return [p for p in pipelines if isinstance(p, dict)]


async def run_inlet(
    session: Session,
    settings: Settings,
    *,
    pipeline: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Pre-chat filter. Returns the (possibly modified) payload, or the
    original when the server is unreachable or flows are off."""
    config = get_flows_config(session)
    if not config.get("enabled") or not config.get("inlet_enabled"):
        return payload
    body = {"pipeline": pipeline, "payload": payload}
    result = await _request(session, settings, "POST", "pipeline/inlet", body)
    if result and isinstance(result.get("payload"), dict):
        return result["payload"]
    return payload


async def stream_flow(
    session: Session,
    settings: Settings,
    *,
    pipeline: str,
    messages: list[dict[str, str]],
    model: str,
) -> AsyncIterator[str]:
    """Stream a chat response from a flow-server pipeline (chat-shape reply).

    The flow server answers ``POST /pipeline/{id}`` with the completion in
    chat shape (``{"message": {"content": ...}}``) — the same contract the
    pipelines ecosystem uses — plus optional ``model``/``usage`` fields. The
    full text is yielded as one delta; empty or malformed replies raise a
    ProviderError so the caller can persist the error.
    """
    config = get_flows_config(session)
    if not config.get("enabled") or not config.get("url"):
        raise ProviderError("Flows are not configured.")
    url = f"{config['url']}/pipeline/{pipeline}"
    headers = {"Content-Type": "application/json"}
    if config.get("api_key"):
        headers["Authorization"] = f"Bearer {config['api_key']}"
    body: dict[str, Any] = {"messages": messages, "model": model, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise ProviderError(f"Flow request failed: {exc}") from exc
    text = ""
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, dict):
            text = message.get("content", "")
        else:
            text = payload.get("content") or payload.get("response") or ""
    if not text:
        raise ProviderError("Flow server returned no response text.")
    yield text


async def run_outlet(
    session: Session,
    settings: Settings,
    *,
    pipeline: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Post-chat filter. Returns the modified payload or the original."""
    config = get_flows_config(session)
    if not config.get("enabled") or not config.get("outlet_enabled"):
        return payload
    body = {"pipeline": pipeline, "payload": payload}
    result = await _request(session, settings, "POST", "pipeline/outlet", body)
    if result and isinstance(result.get("payload"), dict):
        return result["payload"]
    return payload
