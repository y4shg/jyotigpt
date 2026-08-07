"""Task-generation service: model resolution + completion runner.

The task endpoints (title, tags, image prompt, queries, autocompletion,
emoji, moa) all share the same shape: resolve the target model, run the
payload through the pipeline inlet filters, then hand it to the chat
completion machinery. That shared machinery lives here; the per-task
template rendering and payload shape stay in ``routes.py``.
"""

import logging

from fastapi.responses import JSONResponse

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.utils.chat import generate_chat_completion
from jyotigpt.utils.task import get_task_model_id

from jyotigpt.domains.pipelines.service import process_pipeline_inlet_filter

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


def resolve_models(request):
    """Model map for the request: the direct-request override or the registry."""
    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        return {
            request.state.model["id"]: request.state.model,
        }
    return request.app.state.MODELS


def resolve_task_model(model_id, request, models):
    """The configured task model, falling back to the chat model itself."""
    return get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )


async def run_task_completion(
    request,
    payload,
    user,
    models,
    *,
    error_status: int,
    error_detail: str,
):
    """Inlet-filter the task payload, then run a chat completion.

    Pipeline failures propagate unchanged; chat-completion failures are
    turned into a JSON error response using the task's own status code
    and detail.
    """
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error("Exception occurred", exc_info=True)
        return JSONResponse(
            status_code=error_status,
            content={
                "detail": error_detail if error_detail is not None else str(e)
            },
        )
