"""Image generation service.

Talks to the configured image engine (openai, gemini, comfyui,
automatic1111), saves each produced image through the file service, and
returns its content URL. Engine-specific helpers are kept here so the
router only deals with request/response shaping.
"""

import asyncio
import base64
import io
import json
import logging
import mimetypes

import requests
from fastapi import HTTPException, Request, UploadFile

from jyotigpt.config import CACHE_DIR
from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import ENABLE_FORWARD_USER_INFO_HEADERS, SRC_LOG_LEVELS
from jyotigpt.routers.files import upload_file
from jyotigpt.utils.images.comfyui import (
    ComfyUIGenerateImageForm,
    ComfyUIWorkflow,
    comfyui_generate_image,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["IMAGES"])

IMAGE_CACHE_DIR = CACHE_DIR / "image" / "generations"
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_automatic1111_api_auth(request: Request) -> str:
    """Basic auth header for Automatic1111 from the configured API key."""
    if request.app.state.config.AUTOMATIC1111_API_AUTH is None:
        return ""
    auth1111_byte_string = request.app.state.config.AUTOMATIC1111_API_AUTH.encode(
        "utf-8"
    )
    auth1111_base64_encoded_bytes = base64.b64encode(auth1111_byte_string)
    auth1111_base64_encoded_string = auth1111_base64_encoded_bytes.decode("utf-8")
    return f"Basic {auth1111_base64_encoded_string}"


def set_image_model(request: Request, model: str) -> str:
    """Persist the active image model, syncing Automatic1111 when in use."""
    log.info(f"Setting image model to {model}")
    request.app.state.config.IMAGE_GENERATION_MODEL = model
    if request.app.state.config.IMAGE_GENERATION_ENGINE in ["", "automatic1111"]:
        api_auth = get_automatic1111_api_auth(request)
        r = requests.get(
            url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
            headers={"authorization": api_auth},
        )
        options = r.json()
        if model != options["sd_model_checkpoint"]:
            options["sd_model_checkpoint"] = model
            r = requests.post(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                json=options,
                headers={"authorization": api_auth},
            )
    return request.app.state.config.IMAGE_GENERATION_MODEL


def get_image_model(request: Request) -> str:
    """Resolve the current model, applying engine-specific defaults."""
    if request.app.state.config.IMAGE_GENERATION_ENGINE == "openai":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "dall-e-2"
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "gemini":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else "imagen-3.0-generate-002"
        )
    elif request.app.state.config.IMAGE_GENERATION_ENGINE == "comfyui":
        return (
            request.app.state.config.IMAGE_GENERATION_MODEL
            if request.app.state.config.IMAGE_GENERATION_MODEL
            else ""
        )
    elif (
        request.app.state.config.IMAGE_GENERATION_ENGINE == "automatic1111"
        or request.app.state.config.IMAGE_GENERATION_ENGINE == ""
    ):
        try:
            r = requests.get(
                url=f"{request.app.state.config.AUTOMATIC1111_BASE_URL}/sdapi/v1/options",
                headers={"authorization": get_automatic1111_api_auth(request)},
            )
            options = r.json()
            return options["sd_model_checkpoint"]
        except Exception as e:
            request.app.state.config.ENABLE_IMAGE_GENERATION = False
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT(e))


def _forward_user_headers(user) -> dict:
    """Headers carrying the acting user when forwarding is enabled."""
    return {
        "X-JyotiGPT-User-Name": user.name,
        "X-JyotiGPT-User-Id": user.id,
        "X-JyotiGPT-User-Email": user.email,
        "X-JyotiGPT-User-Role": user.role,
    }


def load_b64_image_data(b64_str):
    """Decode a base64 image, sniffing its mime type from the data URI."""
    try:
        if "," in b64_str:
            header, encoded = b64_str.split(",", 1)
            mime_type = header.split(";")[0]
            img_data = base64.b64decode(encoded)
        else:
            mime_type = "image/png"
            img_data = base64.b64decode(b64_str)
        return img_data, mime_type
    except Exception as e:
        log.exception(f"Error loading image data: {e}")
        return None


def load_url_image_data(url, headers=None):
    """Download an image URL, returning (bytes, content-type)."""
    try:
        if headers:
            r = requests.get(url, headers=headers)
        else:
            r = requests.get(url)

        r.raise_for_status()
        if r.headers["content-type"].split("/")[0] == "image":
            mime_type = r.headers["content-type"]
            return r.content, mime_type
        else:
            log.error("Url does not point to an image.")
            return None

    except Exception as e:
        log.exception(f"Error saving image: {e}")
        return None


def upload_image(request, image_metadata, image_data, content_type, user) -> str:
    """Store a generated image via the file service, returning its URL."""
    image_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(image_data),
        filename=f"generated-image{image_format}",  # will be converted to a unique ID on upload_file
        headers={
            "content-type": content_type,
        },
    )
    file_item = upload_file(request, file, user, file_metadata=image_metadata)
    url = request.app.url_path_for("get_file_content_by_id", id=file_item.id)
    return url
