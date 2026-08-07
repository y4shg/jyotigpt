"""Pipe engine: load, enumerate and execute function "pipes".

A *pipe* is a function-type plugin that serves as a model: a module with
a callable ``pipe`` (and optionally ``pipes`` for manifolds).  This
module owns the three capabilities the rest of the application needs:

* :func:`get_function_module_by_id` — resolve (and cache) a plugin
  module, hydrating its valves from the database,
* :func:`get_function_models` — the model listing contributed by all
  active pipe plugins,
* :func:`generate_function_chat_completion` — run a pipe and shape its
  result into an OpenAI-compatible chat completion, either streamed
  (SSE) or as a single response.

The legacy ``jyotigpt.functions`` module re-exports these for backwards
compatibility.
"""

import asyncio
import inspect
import json
import logging
import sys
from typing import AsyncGenerator, Generator, Iterator

from pydantic import BaseModel
from starlette.responses import StreamingResponse

from jyotigpt.core.environment import GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS
from jyotigpt.core.events import get_event_call, get_event_emitter
from jyotigpt.models.functions import Functions
from jyotigpt.models.models import Models
from jyotigpt.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)
from jyotigpt.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)
from jyotigpt.utils.plugin import load_function_module_by_id
from jyotigpt.utils.tools import get_tools


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def get_function_module_by_id(request, pipe_id: str):
    """Return the loaded plugin module for ``pipe_id``, cached on the app.

    Valves declared by the module are hydrated from the database before
    the module is handed out.
    """
    if pipe_id not in request.app.state.FUNCTIONS:
        function_module, _, _ = load_function_module_by_id(pipe_id)
        request.app.state.FUNCTIONS[pipe_id] = function_module
    else:
        function_module = request.app.state.FUNCTIONS[pipe_id]

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(pipe_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))
    return function_module


async def get_function_models(request):
    """The OpenAI-style model list contributed by active pipe plugins."""
    pipes = Functions.get_functions_by_type("pipe", active_only=True)
    pipe_models = []

    for pipe in pipes:
        function_module = get_function_module_by_id(request, pipe.id)

        # A manifold exposes a ``pipes`` collection (list or callable).
        if hasattr(function_module, "pipes"):
            sub_pipes = []
            try:
                if callable(function_module.pipes):
                    if asyncio.iscoroutinefunction(function_module.pipes):
                        sub_pipes = await function_module.pipes()
                    else:
                        sub_pipes = function_module.pipes()
                else:
                    sub_pipes = function_module.pipes
            except Exception as e:
                log.exception(e)
                sub_pipes = []

            log.debug(
                f"get_function_models: function '{pipe.id}' is a manifold of {sub_pipes}"
            )

            for p in sub_pipes:
                sub_pipe_id = f'{pipe.id}.{p["id"]}'
                sub_pipe_name = p["name"]

                if hasattr(function_module, "name"):
                    sub_pipe_name = f"{function_module.name}{sub_pipe_name}"

                pipe_flag = {"type": pipe.type}

                pipe_models.append(
                    {
                        "id": sub_pipe_id,
                        "name": sub_pipe_name,
                        "object": "model",
                        "created": pipe.created_at,
                        "owned_by": "openai",
                        "pipe": pipe_flag,
                    }
                )
        else:
            pipe_flag = {"type": "pipe"}

            log.debug(
                f"get_function_models: function '{pipe.id}' is a single pipe {{ 'id': {pipe.id}, 'name': {pipe.name} }}"
            )

            pipe_models.append(
                {
                    "id": pipe.id,
                    "name": pipe.name,
                    "object": "model",
                    "created": pipe.created_at,
                    "owned_by": "openai",
                    "pipe": pipe_flag,
                }
            )

    return pipe_models


####################################
# Pipe execution helpers
####################################


async def _execute_pipe(pipe, params):
    """Invoke a pipe, awaiting it when it is a coroutine function."""
    if inspect.iscoroutinefunction(pipe):
        return await pipe(**params)
    else:
        return pipe(**params)


async def _get_message_content(res: str | Generator | AsyncGenerator) -> str:
    """Flatten a pipe result into plain text when it is stream-like."""
    if isinstance(res, str):
        return res
    if isinstance(res, Generator):
        return "".join(map(str, res))
    if isinstance(res, AsyncGenerator):
        return "".join([str(stream) async for stream in res])


def _process_line(form_data: dict, line):
    """Serialize one streamed line into an SSE ``data:`` frame."""
    if isinstance(line, BaseModel):
        line = line.model_dump_json()
        line = f"data: {line}"
    if isinstance(line, dict):
        line = f"data: {json.dumps(line)}"

    try:
        line = line.decode("utf-8")
    except Exception:
        pass

    if line.startswith("data:"):
        return f"{line}\n\n"
    else:
        line = openai_chat_chunk_message_template(form_data["model"], line)
        return f"data: {json.dumps(line)}\n\n"


def _get_pipe_id(form_data: dict) -> str:
    """The plugin id for a model id, stripping any manifold suffix."""
    pipe_id = form_data["model"]
    if "." in pipe_id:
        pipe_id, _ = pipe_id.split(".", 1)
    return pipe_id


def _get_function_params(function_module, form_data, user, extra_params=None):
    """Select the callable pipe params: body plus the supported extras."""
    if extra_params is None:
        extra_params = {}

    pipe_id = _get_pipe_id(form_data)

    sig = inspect.signature(function_module.pipe)
    params = {"body": form_data} | {
        k: v for k, v in extra_params.items() if k in sig.parameters
    }

    if "__user__" in params and hasattr(function_module, "UserValves"):
        user_valves = Functions.get_user_valves_by_id_and_user_id(pipe_id, user.id)
        try:
            params["__user__"]["valves"] = function_module.UserValves(**user_valves)
        except Exception as e:
            log.exception(e)
            params["__user__"]["valves"] = function_module.UserValves()

    return params


async def generate_function_chat_completion(
    request, form_data, user, models: dict = {}
):
    """Run a pipe as a chat completion (SSE when ``stream`` is set)."""
    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    metadata = form_data.pop("metadata", {})

    files = metadata.get("files", [])
    tool_ids = metadata.get("tool_ids", [])
    # Check if tool_ids is None
    if tool_ids is None:
        tool_ids = []

    __event_emitter__ = None
    __event_call__ = None
    __task__ = None
    __task_body__ = None

    if metadata:
        if all(k in metadata for k in ("session_id", "chat_id", "message_id")):
            __event_emitter__ = get_event_emitter(metadata)
            __event_call__ = get_event_call(metadata)
        __task__ = metadata.get("task", None)
        __task_body__ = metadata.get("task_body", None)

    extra_params = {
        "__event_emitter__": __event_emitter__,
        "__event_call__": __event_call__,
        "__chat_id__": metadata.get("chat_id", None),
        "__session_id__": metadata.get("session_id", None),
        "__message_id__": metadata.get("message_id", None),
        "__task__": __task__,
        "__task_body__": __task_body__,
        "__files__": files,
        "__user__": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
        "__metadata__": metadata,
        "__request__": request,
    }
    extra_params["__tools__"] = get_tools(
        request,
        tool_ids,
        user,
        {
            **extra_params,
            "__model__": models.get(form_data["model"], None),
            "__messages__": form_data["messages"],
            "__files__": files,
        },
    )

    if model_info:
        if model_info.base_model_id:
            form_data["model"] = model_info.base_model_id

        params = model_info.params.model_dump()
        form_data = apply_model_params_to_body_openai(params, form_data)
        form_data = apply_model_system_prompt_to_body(params, form_data, metadata, user)

    pipe_id = _get_pipe_id(form_data)
    function_module = get_function_module_by_id(request, pipe_id)

    pipe = function_module.pipe
    params = _get_function_params(function_module, form_data, user, extra_params)

    if form_data.get("stream", False):

        async def stream_content():
            try:
                res = await _execute_pipe(pipe, params)

                # Directly return if the response is a StreamingResponse
                if isinstance(res, StreamingResponse):
                    async for data in res.body_iterator:
                        yield data
                    return
                if isinstance(res, dict):
                    yield f"data: {json.dumps(res)}\n\n"
                    return

            except Exception as e:
                log.error(f"Error: {e}")
                yield f"data: {json.dumps({'error': {'detail':str(e)}})}\n\n"
                return

            if isinstance(res, str):
                message = openai_chat_chunk_message_template(form_data["model"], res)
                yield f"data: {json.dumps(message)}\n\n"

            if isinstance(res, Iterator):
                for line in res:
                    yield _process_line(form_data, line)

            if isinstance(res, AsyncGenerator):
                async for line in res:
                    yield _process_line(form_data, line)

            if isinstance(res, str) or isinstance(res, Generator):
                finish_message = openai_chat_chunk_message_template(
                    form_data["model"], ""
                )
                finish_message["choices"][0]["finish_reason"] = "stop"
                yield f"data: {json.dumps(finish_message)}\n\n"
                yield "data: [DONE]"

        return StreamingResponse(stream_content(), media_type="text/event-stream")
    else:
        try:
            res = await _execute_pipe(pipe, params)

        except Exception as e:
            log.error(f"Error: {e}")
            return {"error": {"detail": str(e)}}

        if isinstance(res, StreamingResponse) or isinstance(res, dict):
            return res
        if isinstance(res, BaseModel):
            return res.model_dump()

        message = await _get_message_content(res)
        return openai_chat_completion_message_template(form_data["model"], message)
