"""Chat completion orchestration.

Routes incoming chat requests to the right backend (socket relay, arena,
function pipelines, Ollama or OpenAI-compatible APIs) and runs the post-
completion filter chain.
"""

import asyncio
import inspect
import json
import logging
import random
import sys
import uuid
from typing import Any, Optional

from fastapi import Request
from starlette.responses import StreamingResponse

from jyotigpt.env import BYPASS_MODEL_ACCESS_CONTROL, GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS
from jyotigpt.functions import generate_function_chat_completion
from jyotigpt.models.functions import Functions
from jyotigpt.models.users import UserModel
from jyotigpt.routers.ollama import (
    generate_chat_completion as generate_ollama_chat_completion,
)
from jyotigpt.routers.openai import (
    generate_chat_completion as generate_openai_chat_completion,
)
from jyotigpt.routers.pipelines import (
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)
from jyotigpt.socket.main import get_event_call, get_event_emitter, sio
from jyotigpt.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)
from jyotigpt.utils.models import check_model_access, get_all_models
from jyotigpt.utils.payload import convert_payload_openai_to_ollama
from jyotigpt.utils.plugin import load_function_module_by_id
from jyotigpt.utils.response import (
    convert_response_ollama_to_openai,
    convert_streaming_response_ollama_to_openai,
)

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# Model entries marked as "arena" route to a random member model.
_ARENA_OWNER = "arena"


def _extract_metadata(form_data: dict) -> dict:
    """Pop and return the metadata block carried on a chat payload."""
    return form_data.pop("metadata", {})


def _build_socket_channel(user_id: str, session_id: str, request_id: str) -> str:
    return f"{user_id}:{session_id}:{request_id}"


def _resolve_model_table(
    request: Request, user: Any
) -> tuple[dict, bool]:
    """Return (model_map, is_direct) for the current request context."""
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        return {request.state.model["id"]: request.state.model}, True
    return request.app.state.MODELS, False


def _require_model(model_id: str, model_map: dict) -> dict:
    if model_id not in model_map:
        raise Exception("Model not found")
    return model_map[model_id]


class _SocketRelay:
    """Streams a chat completion through a private socketio channel."""

    def __init__(self, channel: str, event_caller: Any, session_id: Optional[str]):
        self.channel = channel
        self.event_caller = event_caller
        self.session_id = session_id
        self._queue: asyncio.Queue = asyncio.Queue()

    async def _listen(self, _sid: str, data: Any) -> None:
        """Socket callback: enqueue every incoming frame."""
        await self._queue.put(data)

    async def _frames(self):
        """Yield SSE frames until the completion signals done."""
        try:
            while True:
                frame = await self._queue.get()
                if isinstance(frame, dict):
                    if frame.get("done"):
                        break
                    yield f"data: {json.dumps(frame)}\n\n"
                elif isinstance(frame, str):
                    yield frame
        except Exception as exc:  # keep the stream alive on transient errors
            log.debug(f"frame loop aborted: {exc}")

    async def _cleanup(self) -> None:
        try:
            del sio.handlers["/"][self.channel]
        except Exception:
            pass

    async def run(self, form_data: dict, model: dict) -> Any:
        sio.on(self.channel, self._listen)
        result = await self.event_caller(
            {
                "type": "request:chat:completion",
                "data": {
                    "form_data": form_data,
                    "model": model,
                    "channel": self.channel,
                    "session_id": self.session_id,
                },
            }
        )
        log.info(f"relay result: {result}")
        if not result.get("status", False):
            raise Exception(str(result))
        if not form_data.get("stream"):
            return result
        return StreamingResponse(
            self._frames(), media_type="text/event-stream", background=self._cleanup
        )


async def generate_direct_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    models: dict,
):
    """Completion that bypasses the HTTP layer and streams over socketio."""
    log.info("generate_direct_chat_completion")

    metadata = _extract_metadata(form_data)
    user_id = metadata.get("user_id")
    session_id = metadata.get("session_id")
    request_id = str(uuid.uuid4())

    channel = _build_socket_channel(user_id, session_id, request_id)
    relay = _SocketRelay(channel, get_event_call(metadata), session_id)
    return await relay.run(form_data, models[form_data["model"]])


def _merge_request_metadata(request: Request, form_data: dict) -> None:
    if not hasattr(request.state, "metadata"):
        return
    if "metadata" not in form_data:
        form_data["metadata"] = request.state.metadata
    else:
        form_data["metadata"] = {
            **form_data["metadata"],
            **request.state.metadata,
        }


def _authorize_model_access(user: Any, model: dict, bypass: bool) -> None:
    if bypass or user.role != "user":
        return
    check_model_access(user, model)


def _draw_arena_model(model_map: dict, arena_model: dict, form_data: dict) -> str:
    """Pick a concrete model for an arena entry and record it on the payload."""
    meta = arena_model.get("info", {}).get("meta", {})
    pool = meta.get("model_ids")
    if pool and meta.get("filter_mode") == "exclude":
        pool = [
            m["id"]
            for m in model_map.values()
            if m.get("owned_by") != _ARENA_OWNER and m["id"] not in pool
        ]

    if not isinstance(pool, list) or not pool:
        pool = [
            m["id"]
            for m in model_map.values()
            if m.get("owned_by") != _ARENA_OWNER
        ]
    return random.choice(pool)


def _wrap_arena_stream(response: StreamingResponse, chosen: str) -> StreamingResponse:
    async def annotate(stream):
        yield f"data: {json.dumps({'selected_model_id': chosen})}\n\n"
        async for chunk in stream:
            yield chunk

    return StreamingResponse(
        annotate(response.body_iterator),
        media_type="text/event-stream",
        background=response.background,
    )


async def _dispatch_to_provider(
    request: Request,
    form_data: dict,
    model: dict,
    model_map: dict,
    user: Any,
    bypass_filter: bool,
):
    """Send the payload to the backend that owns the model."""
    if model.get("pipe"):
        return await generate_function_chat_completion(
            request, form_data, user=user, models=model_map
        )

    if model.get("owned_by") == "ollama":
        ollama_payload = convert_payload_openai_to_ollama(form_data)
        response = await generate_ollama_chat_completion(
            request=request,
            form_data=ollama_payload,
            user=user,
            bypass_filter=bypass_filter,
        )
        if ollama_payload.get("stream"):
            response.headers["content-type"] = "text/event-stream"
            return StreamingResponse(
                convert_streaming_response_ollama_to_openai(response),
                headers=dict(response.headers),
                background=response.background,
            )
        return convert_response_ollama_to_openai(response)

    return await generate_openai_chat_completion(
        request=request,
        form_data=form_data,
        user=user,
        bypass_filter=bypass_filter,
    )


async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    bypass_filter: bool = False,
):
    """Route a chat payload to its provider, applying access + arena logic."""
    log.debug(f"generate_chat_completion: {form_data}")
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    _merge_request_metadata(request, form_data)
    model_map, is_direct = _resolve_model_table(request, user)
    model = _require_model(form_data["model"], model_map)

    if is_direct:
        return await generate_direct_chat_completion(
            request, form_data, user=user, models=model_map
        )

    _authorize_model_access(user, model, bypass_filter)

    if model.get("owned_by") == _ARENA_OWNER:
        chosen = _draw_arena_model(model_map, model, form_data)
        form_data["model"] = chosen
        if form_data.get("stream"):
            response = await generate_chat_completion(
                request, form_data, user, bypass_filter=True
            )
            return _wrap_arena_stream(response, chosen)
        return {
            **(
                await generate_chat_completion(
                    request, form_data, user, bypass_filter=True
                )
            ),
            "selected_model_id": chosen,
        }

    return await _dispatch_to_provider(
        request, form_data, model, model_map, user, bypass_filter
    )


chat_completion = generate_chat_completion


def _completion_metadata(data: dict, user: Any) -> dict:
    return {
        "chat_id": data["chat_id"],
        "message_id": data["id"],
        "session_id": data["session_id"],
        "user_id": user.id,
    }


def _user_context(user: Any) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


def _build_extra_params(
    request: Request, data: dict, user: Any, model: dict
) -> dict:
    meta = _completion_metadata(data, user)
    return {
        "__event_emitter__": get_event_emitter(meta),
        "__event_call__": get_event_call(meta),
        "__user__": _user_context(user),
        "__metadata__": meta,
        "__request__": request,
        "__model__": model,
    }


async def chat_completed(request: Request, form_data: dict, user: Any):
    """Run outlet filters over a finished completion."""
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    model_map, _ = _resolve_model_table(request, user)
    model = _require_model(form_data["model"], model_map)

    try:
        data = await process_pipeline_outlet_filter(request, form_data, user, model_map)
    except Exception as exc:
        return Exception(f"Error: {exc}")

    extra_params = _build_extra_params(request, data, user, model)

    try:
        filter_functions = [
            Functions.get_function_by_id(filter_id)
            for filter_id in get_sorted_filter_ids(model)
        ]
        result, _ = await process_filter_functions(
            request=request,
            filter_functions=filter_functions,
            filter_type="outlet",
            form_data=data,
            extra_params=extra_params,
        )
        return result
    except Exception as exc:
        return Exception(f"Error: {exc}")


def _load_action_module(action_id: str, request: Request):
    """Return a cached function module for the given action id."""
    if action_id in request.app.state.FUNCTIONS:
        return request.app.state.FUNCTIONS[action_id]
    module, _, _ = load_function_module_by_id(action_id)
    request.app.state.FUNCTIONS[action_id] = module
    return module


def _apply_action_valves(module: Any, action_id: str) -> None:
    if not (hasattr(module, "valves") and hasattr(module, "Valves")):
        return
    valves = Functions.get_function_valves_by_id(action_id)
    module.valves = module.Valves(**(valves if valves else {}))


def _compose_action_kwargs(
    module: Any,
    action: Any,
    action_id: str,
    sub_action_id: Optional[str],
    data: dict,
    model: dict,
    request: Request,
    user: Any,
) -> dict:
    """Build the keyword arguments for an action call based on its signature."""
    signature = inspect.signature(action)
    kwargs: dict = {"body": data}

    extras = {
        "__model__": model,
        "__id__": sub_action_id if sub_action_id is not None else action_id,
        "__event_emitter__": get_event_emitter(_completion_metadata(data, user)),
        "__event_call__": get_event_call(_completion_metadata(data, user)),
        "__request__": request,
    }
    for key, value in extras.items():
        if key in signature.parameters:
            kwargs[key] = value

    if "__user__" in signature.parameters:
        context = _user_context(user)
        try:
            if hasattr(module, "UserValves"):
                context["valves"] = module.UserValves(
                    **Functions.get_user_valves_by_id_and_user_id(action_id, user.id)
                )
        except Exception as exc:
            log.exception(f"Failed to get user values: {exc}")
        kwargs["__user__"] = context

    return kwargs


async def chat_action(request: Request, action_id: str, form_data: dict, user: Any):
    """Invoke a registered function module's action handler."""
    if "." in action_id:
        action_id, sub_action_id = action_id.split(".")
    else:
        sub_action_id = None

    action = Functions.get_function_by_id(action_id)
    if not action:
        raise Exception(f"Action not found: {action_id}")

    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    model_map, _ = _resolve_model_table(request, user)
    model = _require_model(form_data["model"], model_map)

    module = _load_action_module(action_id, request)
    _apply_action_valves(module, action_id)

    if not hasattr(module, "action"):
        return form_data

    try:
        handler = module.action
        kwargs = _compose_action_kwargs(
            module, handler, action_id, sub_action_id, form_data, model, request, user
        )
        if inspect.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)
    except Exception as exc:
        return Exception(f"Error: {exc}")
