"""Task-generation HTTP surface.

One completion endpoint per background task: title, tags, image prompt,
search/retrieval queries, autocompletion, emoji, and moa. Each builds a
non-streaming task payload from its template + config, then delegates to
``run_task_completion`` for the pipeline filter + completion call.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from jyotigpt.config import (
    DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE,
)
from jyotigpt.constants import TASKS
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.utils.auth import get_admin_user, get_verified_user
from jyotigpt.utils.task import (
    autocomplete_generation_template,
    emoji_generation_template,
    image_prompt_generation_template,
    moa_response_generation_template,
    query_generation_template,
    tags_generation_template,
    title_generation_template,
)

from jyotigpt.domains.tasks.service import (
    resolve_models,
    resolve_task_model,
    run_task_completion,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


def _task_payload(request, model_id, content, task, form_data, *, chat_id=True):
    """Base non-streaming task payload with the task metadata block."""
    metadata = {
        **(request.state.metadata if hasattr(request.state, "metadata") else {}),
        "task": str(task),
        "task_body": form_data,
    }
    if chat_id:
        metadata["chat_id"] = form_data.get("chat_id", None)

    return {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "metadata": metadata,
    }


@router.get("/config")
async def get_task_config(request: Request, user=Depends(get_verified_user)):
    return {
        "TASK_MODEL": request.app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": request.app.state.config.TASK_MODEL_EXTERNAL,
        "TITLE_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE": request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_AUTOCOMPLETE_GENERATION": request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION,
        "AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH": request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
        "TAGS_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_TAGS_GENERATION": request.app.state.config.ENABLE_TAGS_GENERATION,
        "ENABLE_TITLE_GENERATION": request.app.state.config.ENABLE_TITLE_GENERATION,
        "ENABLE_SEARCH_QUERY_GENERATION": request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION,
        "ENABLE_RETRIEVAL_QUERY_GENERATION": request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION,
        "QUERY_GENERATION_PROMPT_TEMPLATE": request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


class TaskConfigForm(BaseModel):
    TASK_MODEL: Optional[str]
    TASK_MODEL_EXTERNAL: Optional[str]
    ENABLE_TITLE_GENERATION: bool
    TITLE_GENERATION_PROMPT_TEMPLATE: str
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_AUTOCOMPLETE_GENERATION: bool
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: int
    TAGS_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_TAGS_GENERATION: bool
    ENABLE_SEARCH_QUERY_GENERATION: bool
    ENABLE_RETRIEVAL_QUERY_GENERATION: bool
    QUERY_GENERATION_PROMPT_TEMPLATE: str
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: str


@router.post("/config/update")
async def update_task_config(
    request: Request, form_data: TaskConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.TASK_MODEL = form_data.TASK_MODEL
    request.app.state.config.TASK_MODEL_EXTERNAL = form_data.TASK_MODEL_EXTERNAL
    request.app.state.config.ENABLE_TITLE_GENERATION = form_data.ENABLE_TITLE_GENERATION
    request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = (
        form_data.TITLE_GENERATION_PROMPT_TEMPLATE
    )
    request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = (
        form_data.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
    )
    request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION = (
        form_data.ENABLE_AUTOCOMPLETE_GENERATION
    )
    request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = (
        form_data.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
    )
    request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = (
        form_data.TAGS_GENERATION_PROMPT_TEMPLATE
    )
    request.app.state.config.ENABLE_TAGS_GENERATION = form_data.ENABLE_TAGS_GENERATION
    request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION = (
        form_data.ENABLE_SEARCH_QUERY_GENERATION
    )
    request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION = (
        form_data.ENABLE_RETRIEVAL_QUERY_GENERATION
    )
    request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = (
        form_data.QUERY_GENERATION_PROMPT_TEMPLATE
    )
    request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
        form_data.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
    )

    return {
        "TASK_MODEL": request.app.state.config.TASK_MODEL,
        "TASK_MODEL_EXTERNAL": request.app.state.config.TASK_MODEL_EXTERNAL,
        "ENABLE_TITLE_GENERATION": request.app.state.config.ENABLE_TITLE_GENERATION,
        "TITLE_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        "IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE": request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_AUTOCOMPLETE_GENERATION": request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION,
        "AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH": request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
        "TAGS_GENERATION_PROMPT_TEMPLATE": request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        "ENABLE_TAGS_GENERATION": request.app.state.config.ENABLE_TAGS_GENERATION,
        "ENABLE_TITLE_GENERATION": request.app.state.config.ENABLE_TITLE_GENERATION,
        "ENABLE_SEARCH_QUERY_GENERATION": request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION,
        "ENABLE_RETRIEVAL_QUERY_GENERATION": request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION,
        "QUERY_GENERATION_PROMPT_TEMPLATE": request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE": request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    }


@router.post("/title/completions")
async def generate_title(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if not request.app.state.config.ENABLE_TITLE_GENERATION:
        return JSONResponse(
            status_code=200,
            content={"detail": "Title generation is disabled"},
        )

    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    task_model_id = resolve_task_model(model_id, request, models)

    log.debug(
        f"generating chat title using model {task_model_id} for user {user.email}"
    )

    template = (
        request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE
        or DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE
    )

    messages = form_data["messages"]

    # Remove reasoning details from the messages
    for message in messages:
        message["content"] = re.sub(
            r"<details\s+type=\"reasoning\"[^>]*>.*?<\/details>",
            "",
            message["content"],
            flags=re.S,
        ).strip()

    content = title_generation_template(
        template,
        messages,
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = _task_payload(
        request, task_model_id, content, TASKS.TITLE_GENERATION, form_data
    )
    if models[task_model_id].get("owned_by") == "ollama":
        payload["max_tokens"] = 1000
    else:
        payload["max_completion_tokens"] = 1000

    return await run_task_completion(
        request,
        payload,
        user,
        models,
        error_status=400,
        error_detail="An internal error has occurred.",
    )


@router.post("/tags/completions")
async def generate_chat_tags(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if not request.app.state.config.ENABLE_TAGS_GENERATION:
        return JSONResponse(
            status_code=200,
            content={"detail": "Tags generation is disabled"},
        )

    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    task_model_id = resolve_task_model(model_id, request, models)

    log.debug(
        f"generating chat tags using model {task_model_id} for user {user.email}"
    )

    template = (
        request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE
        or DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE
    )

    content = tags_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    payload = _task_payload(
        request, task_model_id, content, TASKS.TAGS_GENERATION, form_data
    )

    return await run_task_completion(
        request,
        payload,
        user,
        models,
        error_status=500,
        error_detail="An internal error has occurred.",
    )


@router.post("/image_prompt/completions")
async def generate_image_prompt(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    task_model_id = resolve_task_model(model_id, request, models)

    log.debug(
        f"generating image prompt using model {task_model_id} for user {user.email}"
    )

    template = (
        request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
        or DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
    )

    content = image_prompt_generation_template(
        template,
        form_data["messages"],
        user={
            "name": user.name,
        },
    )

    payload = _task_payload(
        request, task_model_id, content, TASKS.IMAGE_PROMPT_GENERATION, form_data
    )

    return await run_task_completion(
        request,
        payload,
        user,
        models,
        error_status=400,
        error_detail="An internal error has occurred.",
    )


@router.post("/queries/completions")
async def generate_queries(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    type = form_data.get("type")
    if type == "web_search":
        if not request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION:
            raise HTTPException(
                status_code=400, detail="Search query generation is disabled"
            )
    elif type == "retrieval":
        if not request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION:
            raise HTTPException(
                status_code=400, detail="Query generation is disabled"
            )

    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    task_model_id = resolve_task_model(model_id, request, models)

    log.debug(
        f"generating {type} queries using model {task_model_id} for user {user.email}"
    )

    template = (
        request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE.strip()
        or DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE
    )

    content = query_generation_template(
        template, form_data["messages"], {"name": user.name}
    )

    payload = _task_payload(
        request, task_model_id, content, TASKS.QUERY_GENERATION, form_data
    )

    return await run_task_completion(
        request, payload, user, models, error_status=400, error_detail=None
    )


@router.post("/auto/completions")
async def generate_autocompletion(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if not request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION:
        raise HTTPException(
            status_code=400, detail="Autocompletion generation is disabled"
        )

    type = form_data.get("type")
    prompt = form_data.get("prompt")
    messages = form_data.get("messages")

    max_length = request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
    if max_length > 0 and len(prompt) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input prompt exceeds maximum length of {max_length}",
        )

    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    task_model_id = resolve_task_model(model_id, request, models)

    log.debug(
        f"generating autocompletion using model {task_model_id} for user {user.email}"
    )

    template = (
        request.app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE.strip()
        or DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE
    )

    content = autocomplete_generation_template(
        template, prompt, messages, type, {"name": user.name}
    )

    payload = _task_payload(
        request, task_model_id, content, TASKS.AUTOCOMPLETE_GENERATION, form_data
    )

    return await run_task_completion(
        request,
        payload,
        user,
        models,
        error_status=500,
        error_detail="An internal error has occurred.",
    )


@router.post("/emoji/completions")
async def generate_emoji(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    task_model_id = resolve_task_model(model_id, request, models)

    log.debug(f"generating emoji using model {task_model_id} for user {user.email}")

    content = emoji_generation_template(
        DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE,
        form_data["prompt"],
        {
            "name": user.name,
            "location": user.info.get("location") if user.info else None,
        },
    )

    payload = _task_payload(
        request,
        task_model_id,
        content,
        TASKS.EMOJI_GENERATION,
        form_data,
        chat_id=False,
    )
    payload["chat_id"] = form_data.get("chat_id", None)
    del payload["stream"]
    if models[task_model_id].get("owned_by") == "ollama":
        payload["max_tokens"] = 4
    else:
        payload["max_completion_tokens"] = 4

    return await run_task_completion(
        request, payload, user, models, error_status=400, error_detail=None
    )


@router.post("/moa/completions")
async def generate_moa_response(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    models = resolve_models(request)
    model_id = form_data["model"]
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    content = moa_response_generation_template(
        DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE,
        form_data["prompt"],
        form_data["responses"],
    )

    payload = _task_payload(
        request, model_id, content, TASKS.MOA_RESPONSE_GENERATION, form_data
    )
    payload["stream"] = form_data.get("stream", False)

    return await run_task_completion(
        request, payload, user, models, error_status=400, error_detail=None
    )
