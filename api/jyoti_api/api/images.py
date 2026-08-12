"""Image generation endpoints: /api/v1/images/*"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.errors import ApiError, NotFoundError
from jyoti_api.services import images as images_service

router = APIRouter(prefix="/api/v1", tags=["images"])


class ImageGenerationRequest(BaseModel):
    prompt: str = ""
    text: str = ""  # when prompt is empty, derive it from text (if enabled)
    model: str = ""
    size: str = "1024x1024"


@router.post("/images/generations")
async def generate_images(
    body: ImageGenerationRequest, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.enable_image_generation:
        raise ApiError("Image generation is disabled on this server.")
    if not settings.user_permissions_features_image_generation:
        raise ApiError("Image generation is not enabled for your role.")

    prompt = (body.prompt or "").strip()
    if not prompt and settings.enable_image_prompt_generation and (body.text or "").strip():
        prompt = await _derive_prompt(settings, body.text)

    if not prompt:
        raise ApiError("A prompt is required for image generation.")

    image_id = await images_service.generate_image(settings, prompt, body.size)
    return {
        "images": [
            {
                "url": images_service.image_url(image_id),
                "prompt": prompt,
            }
        ]
    }


async def _derive_prompt(settings: Any, text: str) -> str:
    """Ask the chat provider to turn free text into an image prompt."""
    import httpx

    template = settings.image_prompt_generation_prompt_template
    rendered = (template or "{{TEXT}}").replace("{{TEXT}}", text)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": "llama3.2",
                    "messages": [{"role": "user", "content": rendered}],
                    "stream": False,
                },
            )
        response.raise_for_status()
        return (response.json().get("message", {}).get("content", "") or "").strip()[:2000]
    except httpx.HTTPError:
        return text[:2000]


@router.get("/images/{image_id}.png")
def get_image(image_id: str) -> FileResponse:
    """Serve a generated image by id (auth-gated like every other route)."""
    settings = get_settings()
    path = Path(images_service.image_path(settings, image_id))
    if not path.exists():
        raise NotFoundError("Image not found.")
    return FileResponse(path, media_type="image/png")
