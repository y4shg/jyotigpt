"""Application configuration endpoints: /api/v1/config/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from jyoti_api.api.deps import AdminUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.domain import settings as settings_domain
from jyoti_api.errors import ValidationError

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("")
def public_config() -> dict[str, Any]:
    """Public feature surface the frontend needs before/after sign-in."""
    env = get_settings()
    stored = settings_domain.get_all()
    merged = {**stored.get("app", {}), "features": _feature_flags(env, stored)}
    return {
        "app": {
            "name": env.app_name,
            "env": env.app_env,
        },
        "features": merged.get("features"),
        "auth": {
            "enable_signup": env.enable_signup,
            "default_user_role": env.default_user_role,
            "enable_ldap": env.enable_ldap,
            "enable_api_keys": env.enable_api_keys,
        },
        "audio": {
            "stt_engine": env.audio_stt_engine,
            "tts_engine": env.audio_tts_engine,
        },
        "interface": merged.get("interface", {}),
        "image_generation": {
            "enabled": _image_enabled(env, stored),
        },
    }


@router.get("/settings")
def get_app_settings(user: AdminUser, session: SessionDep) -> dict[str, Any]:
    return settings_domain.get_all(require_session=user.id)


class SettingsPatch(BaseModel):
    key: str
    value: dict[str, Any]


@router.post("/settings")
def set_app_setting(body: SettingsPatch, user: AdminUser, session: SessionDep) -> dict[str, bool]:
    if not body.key or body.value is None:
        raise ValidationError("key and value are required.")
    settings_domain.set_value(session, body.key, body.value)
    return {"ok": True}


def _feature_flags(env, stored: dict[str, Any]) -> dict[str, Any]:
    features = stored.get("features", {})
    return {
        "image_generation": _image_enabled(env, stored),
        "image_prompt_generation": env.enable_image_prompt_generation,
        "web_search": env.enable_web_search,
        "rag": env.enable_rag,
        "rooms": env.enable_rooms,
        "markdown": env.enable_markdown,
        "signup": env.enable_signup,
    }


def _image_enabled(env, stored: dict[str, Any]) -> bool:
    if env.enable_image_generation:
        return True
    perms = env.user_permissions_features_image_generation
    if not perms:
        return False
    features = stored.get("features", {})
    return bool(features.get("image_generation"))
