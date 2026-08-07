"""Ollama transport + model-aggregation service.

This module owns everything the ``/api/v1/ollama`` router needs that is not
request/response shaping: HTTP transport (streaming and buffered), per-instance
API-key lookup, fan-out aggregation of model lists across the configured base
URLs, model access filtering, URL resolution for chat/generate endpoints, and
the download/upload stream generators used by the model-transfer routes.
"""

import asyncio
import hashlib
import json
import logging
import os
import random
from typing import Optional, Union
from urllib.parse import urlparse

import aiohttp
import requests
from aiocache import cached
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    SRC_LOG_LEVELS,
)
from jyotigpt.models.models import Models
from jyotigpt.models.users import UserModel
from jyotigpt.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OLLAMA"])


def request_headers(key: Optional[str] = None, user: UserModel = None) -> dict:
    """Common request headers: auth bearer plus forwarded user info."""
    return {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {key}"} if key else {}),
        **(
            {
                "X-JyotiGPT-User-Name": user.name,
                "X-JyotiGPT-User-Id": user.id,
                "X-JyotiGPT-User-Email": user.email,
                "X-JyotiGPT-User-Role": user.role,
            }
            if ENABLE_FORWARD_USER_INFO_HEADERS and user
            else {}
        ),
    }


def get_api_key(idx, url, configs) -> Optional[str]:
    """API key for an instance, resolved by index or legacy base URL."""
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return configs.get(str(idx), configs.get(base_url, {})).get("key", None)


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


async def send_get_request(url, key=None, user: UserModel = None):
    """Buffered GET of a JSON endpoint; ``None`` when the instance is down."""
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url,
                headers=request_headers(key, user),
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        log.error(f"Connection error: {e}")
        return None


async def send_post_request(
    url: str,
    payload: Union[str, bytes],
    stream: bool = True,
    key: Optional[str] = None,
    content_type: Optional[str] = None,
    user: UserModel = None,
):
    """Stream or buffer a POST body to an Ollama instance.

    Streaming responses are relayed as-is (with the connection teardown
    scheduled as a background task); buffered responses return the parsed
    JSON. Failures become HTTP exceptions with the instance's error body
    when one was returned.
    """
    r = None
    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.post(
            url,
            data=payload,
            headers=request_headers(key, user),
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        r.raise_for_status()

        if stream:
            response_headers = dict(r.headers)

            if content_type:
                response_headers["Content-Type"] = content_type

            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=response_headers,
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )

        res = await r.json()
        await cleanup_response(r, session)
        return res

    except Exception as e:
        detail = None

        if r is not None:
            try:
                res = await r.json()
                if "error" in res:
                    detail = f"Ollama: {res.get('error', 'Unknown error')}"
            except Exception:
                detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "JyotiGPT: Server Connection Error",
        )


def http_error(r, e) -> HTTPException:
    """Build the shared requests-based error response for an Ollama call."""
    detail = None
    if r is not None:
        try:
            res = r.json()
            if "error" in res:
                detail = f"Ollama: {res['error']}"
        except Exception:
            detail = f"Ollama: {e}"

    return HTTPException(
        status_code=r.status_code if r else 500,
        detail=detail if detail else "JyotiGPT: Server Connection Error",
    )


@cached(ttl=1)
async def get_all_models(request, user: UserModel = None):
    """Aggregate model lists across every enabled Ollama instance.

    Applies per-instance ``model_ids``/``prefix_id``/``tags`` config and
    merges duplicates (recording which instance each model lives on), then
    caches the result in ``request.app.state.OLLAMA_MODELS``.
    """
    log.info("get_all_models()")
    if request.app.state.config.ENABLE_OLLAMA_API:
        request_tasks = []
        for idx, url in enumerate(request.app.state.config.OLLAMA_BASE_URLS):
            if (str(idx) not in request.app.state.config.OLLAMA_API_CONFIGS) and (
                url not in request.app.state.config.OLLAMA_API_CONFIGS
            ):
                request_tasks.append(send_get_request(f"{url}/api/tags", user=user))
            else:
                api_config = request.app.state.config.OLLAMA_API_CONFIGS.get(
                    str(idx),
                    request.app.state.config.OLLAMA_API_CONFIGS.get(url, {}),
                )

                enable = api_config.get("enable", True)
                key = api_config.get("key", None)

                if enable:
                    request_tasks.append(
                        send_get_request(f"{url}/api/tags", key, user=user)
                    )
                else:
                    request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

        responses = await asyncio.gather(*request_tasks)

        for idx, response in enumerate(responses):
            if response:
                url = request.app.state.config.OLLAMA_BASE_URLS[idx]
                api_config = request.app.state.config.OLLAMA_API_CONFIGS.get(
                    str(idx),
                    request.app.state.config.OLLAMA_API_CONFIGS.get(url, {}),
                )

                prefix_id = api_config.get("prefix_id", None)
                tags = api_config.get("tags", [])
                model_ids = api_config.get("model_ids", [])

                if len(model_ids) != 0 and "models" in response:
                    response["models"] = list(
                        filter(
                            lambda model: model["model"] in model_ids,
                            response["models"],
                        )
                    )

                if prefix_id:
                    for model in response.get("models", []):
                        model["model"] = f"{prefix_id}.{model['model']}"

                if tags:
                    for model in response.get("models", []):
                        model["tags"] = tags

        def merge_models_lists(model_lists):
            merged_models = {}

            for idx, model_list in enumerate(model_lists):
                if model_list is not None:
                    for model in model_list:
                        id = model["model"]
                        if id not in merged_models:
                            model["urls"] = [idx]
                            merged_models[id] = model
                        else:
                            merged_models[id]["urls"].append(idx)

            return list(merged_models.values())

        models = {
            "models": merge_models_lists(
                map(
                    lambda response: response.get("models", []) if response else None,
                    responses,
                )
            )
        }

    else:
        models = {"models": []}

    request.app.state.OLLAMA_MODELS = {
        model["model"]: model for model in models["models"]
    }
    return models


async def get_filtered_models(models, user):
    """Only models the ``user`` can read, per their access-control rules."""
    filtered_models = []
    for model in models.get("models", []):
        model_info = Models.get_model_by_id(model["model"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


async def get_ollama_url(request, model: str, url_idx: Optional[int] = None):
    """Resolve the instance URL serving ``model`` (random pick among mirrors)."""
    if url_idx is None:
        models = request.app.state.OLLAMA_MODELS
        if model not in models:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model),
            )
        url_idx = random.choice(models[model].get("urls", []))
    url = request.app.state.config.OLLAMA_BASE_URLS[url_idx]
    return url, url_idx


def parse_huggingface_url(hf_url):
    """Extract the file name from a Hugging Face resolve URL."""
    try:
        parsed_url = urlparse(hf_url)
        path_components = parsed_url.path.split("/")
        return path_components[-1]
    except ValueError:
        return None


async def download_file_stream(
    ollama_url, file_url, file_path, file_name, chunk_size=1024 * 1024
):
    """Resume-download a model file, yielding SSE progress, then upload it.

    The download is written to ``file_path`` in chunks with ``Range``
    resume; once complete the file is hashed and pushed to the instance's
    blob store before a final SSE result message is emitted.
    """
    done = False

    if os.path.exists(file_path):
        current_size = os.path.getsize(file_path)
    else:
        current_size = 0

    headers = {"Range": f"bytes={current_size}-"} if current_size > 0 else {}

    timeout = aiohttp.ClientTimeout(total=600)

    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.get(
            file_url, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL
        ) as response:
            total_size = int(response.headers.get("content-length", 0)) + current_size

            with open(file_path, "ab+") as file:
                async for data in response.content.iter_chunked(chunk_size):
                    current_size += len(data)
                    file.write(data)

                    done = current_size == total_size
                    progress = round((current_size / total_size) * 100, 2)

                    yield f'data: {{"progress": {progress}, "completed": {current_size}, "total": {total_size}}}\n\n'

                if done:
                    file.seek(0)
                    hasher = hashlib.sha256()
                    while chunk := file.read(chunk_size):
                        hasher.update(chunk)
                    hashed = hasher.hexdigest()
                    file.seek(0)

                    url = f"{ollama_url}/api/blobs/sha256:{hashed}"
                    response = requests.post(url, data=file)

                    if response.ok:
                        res = {
                            "done": done,
                            "blob": f"sha256:{hashed}",
                            "name": file_name,
                        }
                        os.remove(file_path)

                        yield f"data: {json.dumps(res)}\n\n"
                    else:
                        raise Exception(
                            "Ollama: Could not create blob, Please try again."
                        )
