"""Model aggregation and access control.

Combines base models from the enabled backends (Ollama, OpenAI, function
plugins), overlays custom/preset models, adds arena-evaluation models, and
resolves action menus. Also enforces per-model access control.
"""

import logging
import sys
import time

from fastapi import Request

from jyotigpt.config import DEFAULT_ARENA_MODEL
from jyotigpt.env import GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS
from jyotigpt.functions import get_function_models
from jyotigpt.models.functions import Functions
from jyotigpt.models.models import Models
from jyotigpt.models.users import UserModel
from jyotigpt.routers import ollama, openai
from jyotigpt.utils.access_control import has_access
from jyotigpt.utils.plugin import load_function_module_by_id

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def get_all_base_models(request: Request, user: UserModel = None):
    """Return the raw model list from enabled backends plus function models."""
    function_models = []
    openai_models = []
    ollama_models = []

    if request.app.state.config.ENABLE_OPENAI_API:
        openai_models = await openai.get_all_models(request, user=user)
        openai_models = openai_models["data"]

    if request.app.state.config.ENABLE_OLLAMA_API:
        ollama_models = await ollama.get_all_models(request, user=user)
        ollama_models = [
            {
                "id": model["model"],
                "name": model["name"],
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ollama",
                "ollama": model,
                "tags": model.get("tags", []),
            }
            for model in ollama_models["models"]
        ]

    function_models = await get_function_models(request)
    return function_models + openai_models + ollama_models


def _build_arena_model(arena_config: dict) -> dict:
    """Shape a single arena model entry."""
    return {
        "id": arena_config["id"],
        "name": arena_config["name"],
        "info": {"meta": arena_config["meta"]},
        "object": "model",
        "created": int(time.time()),
        "owned_by": "arena",
        "arena": True,
    }


async def get_all_models(request, user: UserModel = None):
    """Return the fully-assembled model catalog for ``user``.

    Appends arena models when enabled, merges custom/preset models over
    their base models (adding new entries for derived models), and resolves
    each model's action list from its action ids.
    """
    models = await get_all_base_models(request, user=user)

    if len(models) == 0:
        return []

    if request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS:
        arena_models = []
        if len(request.app.state.config.EVALUATION_ARENA_MODELS) > 0:
            arena_models = [
                _build_arena_model(model)
                for model in request.app.state.config.EVALUATION_ARENA_MODELS
            ]
        else:
            arena_models = [_build_arena_model(DEFAULT_ARENA_MODEL)]
        models = models + arena_models

    global_action_ids = [
        function.id for function in Functions.get_global_action_functions()
    ]
    enabled_action_ids = [
        function.id
        for function in Functions.get_functions_by_type("action", active_only=True)
    ]

    custom_models = Models.get_all_models()
    for custom_model in custom_models:
        if custom_model.base_model_id is None:
            for model in models:
                base_id_matches = (
                    custom_model.id == model["id"]
                    or model.get("owned_by") == "ollama"
                    and custom_model.id == model["id"].split(":")[0]
                )
                if base_id_matches:
                    if custom_model.is_active:
                        model["name"] = custom_model.name
                        model["info"] = custom_model.model_dump()

                        action_ids = []
                        if "info" in model and "meta" in model["info"]:
                            action_ids.extend(
                                model["info"]["meta"].get("actionIds", [])
                            )

                        model["action_ids"] = action_ids
                    else:
                        models.remove(model)

        elif custom_model.is_active and (
            custom_model.id not in [model["id"] for model in models]
        ):
            owned_by = "openai"
            pipe = None
            action_ids = []

            for model in models:
                if (
                    custom_model.base_model_id == model["id"]
                    or custom_model.base_model_id == model["id"].split(":")[0]
                ):
                    owned_by = model.get("owned_by", "unknown owner")
                    if "pipe" in model:
                        pipe = model["pipe"]
                    break

            if custom_model.meta:
                meta = custom_model.meta.model_dump()
                if "actionIds" in meta:
                    action_ids.extend(meta["actionIds"])

            models.append(
                {
                    "id": f"{custom_model.id}",
                    "name": custom_model.name,
                    "object": "model",
                    "created": custom_model.created_at,
                    "owned_by": owned_by,
                    "info": custom_model.model_dump(),
                    "preset": True,
                    **({"pipe": pipe} if pipe is not None else {}),
                    "action_ids": action_ids,
                }
            )

    def get_action_items_from_module(function, module):
        """Map a function's actions (or the function itself) to menu items.

        When the module exposes an ``actions`` list each entry becomes an
        item keyed as ``<function id>.<action id>``; otherwise a single item
        is derived from the function's metadata.
        """
        if hasattr(module, "actions"):
            actions = module.actions
            return [
                {
                    "id": f"{function.id}.{action['id']}",
                    "name": action.get("name", f"{function.name} ({action['id']})"),
                    "description": function.meta.description,
                    "icon_url": action.get(
                        "icon_url", function.meta.manifest.get("icon_url", None)
                    ),
                }
                for action in actions
            ]
        return [
            {
                "id": function.id,
                "name": function.name,
                "description": function.meta.description,
                "icon_url": function.meta.manifest.get("icon_url", None),
            }
        ]

    def load_function_module(function_id):
        """Ensure the function's module is loaded and cached.

        Mirrors the historical behavior: the module is loaded purely for its
        side effect of caching in ``request.app.state.FUNCTIONS``; the
        action items are derived from function metadata, not the module.
        """
        if function_id not in request.app.state.FUNCTIONS:
            function_module, _, _ = load_function_module_by_id(function_id)
            request.app.state.FUNCTIONS[function_id] = function_module

    for model in models:
        action_ids = [
            action_id
            for action_id in list(set(model.pop("action_ids", []) + global_action_ids))
            if action_id in enabled_action_ids
        ]

        model["actions"] = []
        for action_id in action_ids:
            action_function = Functions.get_function_by_id(action_id)
            if action_function is None:
                raise Exception(f"Action not found: {action_id}")

            function_module = load_function_module(action_id)
            model["actions"].extend(
                get_action_items_from_module(action_function, function_module)
            )

    log.debug(f"get_all_models() returned {len(models)} models")

    request.app.state.MODELS = {model["id"]: model for model in models}
    return models


def check_model_access(user, model):
    """Raise if ``user`` may not read ``model``.

    Arena models are checked against their metadata access control; other
    models are checked against the stored custom model record.
    """
    if model.get("arena"):
        if not has_access(
            user.id,
            type="read",
            access_control=model.get("info", {})
            .get("meta", {})
            .get("access_control", {}),
        ):
            raise Exception("Model not found")
    else:
        model_info = Models.get_model_by_id(model.get("id"))
        if not model_info:
            raise Exception("Model not found")
        elif not (
            user.id == model_info.user_id
            or has_access(
                user.id, type="read", access_control=model_info.access_control
            )
        ):
            raise Exception("Model not found")
