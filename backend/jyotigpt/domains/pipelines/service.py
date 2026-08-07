"""Pipelines middleware: inlet/outlet filter fan-out + admin proxy helper.

The two ``process_pipeline_*_filter`` coroutines drive the model-filter
chain used by the chat/task/middleware layers: every registered "filter"
pipeline targeting the requested model is asked to rewrite the payload
before (inlet) and after (outlet) the provider call. The admin endpoints
all share one small synchronous provider proxy, ``pipelines_proxy``.
"""

import logging
from typing import Optional

import aiohttp
import requests
from fastapi import HTTPException, Request

from jyotigpt.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def get_sorted_filters(model_id, models):
    """Filter pipelines registered for ``model_id``, lowest priority first."""
    filters = [
        model
        for model in models.values()
        if "pipeline" in model
        and model["pipeline"].get("type") == "filter"
        and (
            model["pipeline"].get("pipelines") == ["*"]
            or model_id in model["pipeline"].get("pipelines", [])
        )
    ]
    return sorted(filters, key=lambda model: model["pipeline"]["priority"])


def _user_summary(user):
    """Compact user dict forwarded to the pipeline provider."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


def _provider_config(request, url_idx):
    """(base_url, api_key) for the provider index."""
    return (
        request.app.state.config.OPENAI_API_BASE_URLS[url_idx],
        request.app.state.config.OPENAI_API_KEYS[url_idx],
    )


async def process_pipeline_inlet_filter(request, payload, user, models):
    """Let every matching filter pipeline rewrite the payload upstream."""
    user = _user_summary(user)
    model_id = payload["model"]
    sorted_filters = get_sorted_filters(model_id, models)
    model = models[model_id]

    # The model itself may be a pipeline: it filters after the chain
    if "pipeline" in model:
        sorted_filters.append(model)

    async with aiohttp.ClientSession() as session:
        for filter in sorted_filters:
            url_idx = filter.get("urlIdx")
            if url_idx is None:
                continue

            url, key = _provider_config(request, url_idx)
            if not key:
                continue

            headers = {"Authorization": f"Bearer {key}"}
            request_data = {
                "user": user,
                "body": payload,
            }

            try:
                async with session.post(
                    f"{url}/{filter['id']}/filter/inlet",
                    headers=headers,
                    json=request_data,
                ) as response:
                    payload = await response.json()
                    response.raise_for_status()
            except aiohttp.ClientResponseError:
                res = (
                    await response.json()
                    if response.content_type == "application/json"
                    else {}
                )
                if "detail" in res:
                    raise Exception(response.status, res["detail"])
            except Exception as e:
                log.exception(f"Connection error: {e}")

    return payload


async def process_pipeline_outlet_filter(request, payload, user, models):
    """Let every matching filter pipeline rewrite the payload downstream."""
    user = _user_summary(user)
    model_id = payload["model"]
    sorted_filters = get_sorted_filters(model_id, models)
    model = models[model_id]

    # The model itself is a pipeline: it filters before the chain
    if "pipeline" in model:
        sorted_filters = [model] + sorted_filters

    async with aiohttp.ClientSession() as session:
        for filter in sorted_filters:
            url_idx = filter.get("urlIdx")
            if url_idx is None:
                continue

            url, key = _provider_config(request, url_idx)
            if not key:
                continue

            headers = {"Authorization": f"Bearer {key}"}
            request_data = {
                "user": user,
                "body": payload,
            }

            try:
                async with session.post(
                    f"{url}/{filter['id']}/filter/outlet",
                    headers=headers,
                    json=request_data,
                ) as response:
                    payload = await response.json()
                    response.raise_for_status()
            except aiohttp.ClientResponseError:
                try:
                    res = (
                        await response.json()
                        if "application/json" in response.content_type
                        else {}
                    )
                    if "detail" in res:
                        raise Exception(response.status, res)
                except Exception:
                    pass
            except Exception as e:
                log.exception(f"Connection error: {e}")

    return payload


def pipelines_proxy(
    request: Request,
    url_idx: int,
    method: str,
    path: str,
    *,
    json_body=None,
    files=None,
):
    """Synchronous provider call for the admin endpoints.

    Re-raises provider errors as HTTPExceptions, keeping the provider's
    ``detail`` when the response body carries one and defaulting to
    "Pipeline not found".
    """
    r = None
    try:
        url, key = _provider_config(request, url_idx)

        r = requests.request(
            method,
            f"{url}/{path}",
            headers={"Authorization": f"Bearer {key}"},
            json=json_body,
            files=files,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.exception(f"Connection error: {e}")

        detail = None
        if r is not None:
            try:
                res = r.json()
                if "detail" in res:
                    detail = res["detail"]
            except Exception:
                pass

        raise HTTPException(
            status_code=r.status_code if r is not None else 404,
            detail=detail if detail else "Pipeline not found",
        )
