"""Image generation: OpenAI-compatible, AUTOMATIC1111, and ComfyUI engines.

Generated images are saved under ``DATA_DIR/images`` as PNG and served back
through the API (``/api/v1/images/{id}.png``) so the browser gets a stable,
local URL regardless of engine. Engine choice is admin-configured via
environment (``ENABLE_IMAGE_GENERATION`` + the engine base URLs).
"""

from __future__ import annotations

import base64
import uuid
from typing import Any

import httpx

from jyoti_api.config import Settings
from jyoti_api.errors import ApiError

_IMAGE_DIR = "images"


def _image_path(settings: Settings, image_id: str) -> str:
    path = settings.data_dir / _IMAGE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return str(path / f"{image_id}.png")


def _save_png(settings: Settings, raw: bytes) -> str:
    image_id = uuid.uuid4().hex
    path = _image_path(settings, image_id)
    with open(path, "wb") as handle:
        handle.write(raw)
    return image_id


def _decode_b64(data: str) -> bytes:
    try:
        return base64.b64decode(data)
    except (ValueError, base64.binascii.Error) as exc:
        raise ApiError("Engine returned malformed image data.") from exc


async def _download(settings: Settings, url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url)
    response.raise_for_status()
    return response.content


async def _generate_openai(settings: Settings, prompt: str, size: str) -> bytes:
    base = (settings.image_generation_openai_base_url or "https://api.openai.com/v1").rstrip("/")
    key = settings.image_generation_openai_api_key
    if not key:
        raise ApiError("OpenAI image API key is not configured.")
    body: dict[str, Any] = {
        "prompt": prompt,
        "model": settings.image_generation_openai_model,
        "n": 1,
        "size": size,
    }
    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{base}/images/generations", json=body, headers=headers)
        response.raise_for_status()
        data = response.json()["data"][0]
    except httpx.HTTPError as exc:
        raise ApiError(f"Image generation failed: {exc}") from exc
    if data.get("b64_json"):
        return _decode_b64(data["b64_json"])
    if data.get("url"):
        return await _download(settings, data["url"])
    raise ApiError("Image engine returned no image data.")


async def _generate_automatic1111(settings: Settings, prompt: str) -> bytes:
    base = settings.automatic1111_base_url.rstrip("/")
    if not base:
        raise ApiError("AUTOMATIC1111 is not configured.")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{base}/sdapi/v1/txt2img", json={"prompt": prompt, "steps": 28}
            )
        response.raise_for_status()
        images = response.json().get("images") or []
    except httpx.HTTPError as exc:
        raise ApiError(f"AUTOMATIC1111 request failed: {exc}") from exc
    if not images:
        raise ApiError("AUTOMATIC1111 returned no images.")
    return _decode_b64(images[0])


async def _generate_comfyui(settings: Settings, prompt: str) -> bytes:
    base = settings.comfyui_base_url.rstrip("/")
    workflow = settings.comfyui_workflow
    if not base or not workflow:
        raise ApiError("ComfyUI is not configured (URL and workflow required).")
    client_id = uuid.uuid4().hex
    try:
        resolved = workflow.replace("{{prompt}}", prompt)
        import json as _json

        payload = _json.loads(resolved) if resolved.strip().startswith(("{", "[")) else {
            "prompt": resolved
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base}/prompt",
                json={"prompt": payload, "client_id": client_id},
                headers={"Authorization": f"Bearer {settings.comfyui_api_key}"} if settings.comfyui_api_key else {},
            )
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            raise ApiError("ComfyUI did not accept the workflow.")
        for _ in range(120):  # poll history until the run finishes
            history_response = await client.get(f"{base}/history/{prompt_id}")
            history_response.raise_for_status()
            history = history_response.json()
            entry = (history.get(prompt_id) or {}).get("outputs") if isinstance(history, dict) else None
            if entry:
                for node in entry.values():
                    for image in node.get("images", []):
                        image_response = await client.get(
                            f"{base}/view", params={"filename": image["filename"], "subfolder": image.get("subfolder", "")}
                        )
                        image_response.raise_for_status()
                        return image_response.content
                break
            import asyncio

            await asyncio.sleep(1)
        raise ApiError("ComfyUI run did not produce an image in time.")
    except httpx.HTTPError as exc:
        raise ApiError(f"ComfyUI request failed: {exc}") from exc


async def generate_image(settings: Settings, prompt: str, size: str = "1024x1024") -> str:
    """Generate an image, persist it, and return the served image id."""
    engine = settings.image_generation_engine
    if engine == "automatic1111":
        raw = await _generate_automatic1111(settings, prompt)
    elif engine == "comfyui":
        raw = await _generate_comfyui(settings, prompt)
    else:
        raw = await _generate_openai(settings, prompt, size)
    return _save_png(settings, raw)


def image_url(image_id: str) -> str:
    return f"/api/v1/images/{image_id}.png"


def image_path(settings: Settings, image_id: str) -> str:
    return _image_path(settings, image_id)
