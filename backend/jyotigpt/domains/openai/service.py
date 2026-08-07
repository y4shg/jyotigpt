"""OpenAI-provider transport + model-aggregation service.

Backs the ``/openai`` router: buffered GET transport, o1/o3 payload
fixups, fan-out model aggregation across the configured providers
(including config-driven ``model_ids`` and ``prefix_id`` rewrites), and
the access-control filter shared by the model-list endpoints.
"""

import asyncio
import logging
from typing import Optional

import aiohttp
from aiocache import cached

from jyotigpt.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    SRC_LOG_LEVELS,
)
from jyotigpt.models.models import Models
from jyotigpt.models.users import UserModel
from jyotigpt.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


def forward_headers(key: Optional[str] = None, user: UserModel = None) -> dict:
    """Auth bearer plus forwarded user info headers."""
    return {
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


async def send_get_request(url, key=None, user: UserModel = None):
    """Buffered GET of a JSON endpoint; ``None`` when the provider is down."""
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url,
                headers={
                    "Content-Type": "application/json",
                    **forward_headers(key, user),
                },
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        log.error(f"Connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


def openai_o1_o3_handler(payload):
    """Fix o1/o3-specific parameter expectations.

    These models reject ``max_tokens`` (use ``max_completion_tokens``) and
    do not accept a ``system`` role (use ``developer``, or ``user`` for
    the older preview builds).
    """
    if "max_tokens" in payload:
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    if payload["messages"][0]["role"] == "system":
        model_lower = payload["model"].lower()
        if model_lower.startswith("o1-mini") or model_lower.startswith("o1-preview"):
            payload["messages"][0]["role"] = "user"
        else:
            payload["messages"][0]["role"] = "developer"

    return payload


async def get_all_models_responses(request, user: UserModel) -> list:
    """Fan out ``/models`` queries across every enabled provider."""
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Keep the API key list aligned with the URL list
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        if num_keys > num_urls:
            request.app.state.config.OPENAI_API_KEYS = (
                request.app.state.config.OPENAI_API_KEYS[:num_urls]
            )
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.OPENAI_API_CONFIGS) and (
            url not in request.app.state.config.OPENAI_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.OPENAI_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),
            )

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    # Whitelisted ids only: no live query needed
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "openai",
                                "openai": {"id": model_id},
                                "urlIdx": idx,
                            }
                            for model_id in model_ids
                        ],
                    }

                    request_tasks.append(
                        asyncio.ensure_future(asyncio.sleep(0, model_list))
                    )
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),
            )

            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            if prefix_id:
                for model in (
                    response if isinstance(response, list) else response.get("data", [])
                ):
                    model["id"] = f"{prefix_id}.{model['id']}"

            if tags:
                for model in (
                    response if isinstance(response, list) else response.get("data", [])
                ):
                    model["tags"] = tags

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user):
    """Only models the ``user`` can read, per their access-control rules."""
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


@cached(ttl=1)
async def get_all_models(request, user: UserModel) -> dict[str, list]:
    """Aggregate and merge model lists across every enabled provider."""
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def merge_models_lists(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        merged_list = []

        for idx, models in enumerate(model_lists):
            if models is not None and "error" not in models:
                merged_list.extend(
                    [
                        {
                            **model,
                            "name": model.get("name", model["id"]),
                            "owned_by": "openai",
                            "openai": model,
                            "urlIdx": idx,
                        }
                        for model in models
                        if (model.get("id") or model.get("name"))
                        and (
                            "api.openai.com"
                            not in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                            or not any(
                                name in model["id"]
                                for name in [
                                    "babbage",
                                    "dall-e",
                                    "davinci",
                                    "embedding",
                                    "tts",
                                    "whisper",
                                ]
                            )
                        )
                    ]
                )

        return merged_list

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = {model["id"]: model for model in models["data"]}
    return models
