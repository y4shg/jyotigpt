"""Web search via SearXNG: GET /api/v1/search/web.

Requires ``ENABLE_WEB_SEARCH=1`` and a configured SearXNG instance
(``SEARXNG_QUERY_URL``). The SearXNG JSON output format is enabled with the
``format=json`` query parameter; if the instance requires it, ``SEARXNG_SECRET``
is passed as the ``authentication`` header. Results are normalized to the
Open WebUI-compatible shape the frontend expects: ``{id,title,content,url}``.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Query

from jyoti_api.api.deps import CurrentUser
from jyoti_api.config import get_settings
from jyoti_api.errors import BadGatewayError, ValidationError

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def _normalize(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in results:
        url = item.get("url") or item.get("href")
        title = item.get("title") or ""
        content = item.get("content") or ""
        if not url:
            continue
        out.append(
            {
                "id": url,
                "title": title,
                "content": content,
                "url": url,
                "author": item.get("author", ""),
                "score": item.get("score"),
            }
        )
    return out


@router.get("/web")
async def web_search(
    user: CurrentUser,
    q: str = Query(min_length=1, max_length=500),
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.enable_web_search:
        raise BadGatewayError("Web search is disabled (set ENABLE_WEB_SEARCH=1).")
    if not settings.searxng_query_url:
        raise BadGatewayError("SearXNG is not configured (SEARXNG_QUERY_URL is empty).")
    if not q.strip():
        raise ValidationError("Search query is required.")

    params = {"q": q.strip(), "format": "json"}
    if settings.web_search_result_count > 0:
        params["n"] = str(settings.web_search_result_count)
    headers = {}
    if settings.searxng_secret:
        headers["authentication"] = settings.searxng_secret

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(
                settings.searxng_query_url, params=params, headers=headers
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise BadGatewayError(f"Search request failed: {exc}") from exc

    results = payload.get("results") or [] if isinstance(payload, dict) else []
    return {"results": _normalize(results), "query": q.strip()}
