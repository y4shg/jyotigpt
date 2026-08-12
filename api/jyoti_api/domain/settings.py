"""Persisted app settings (admin-managed, layered over env defaults)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.persistence.schema import AppSetting

_DEFAULT_GROUPS: dict[str, dict[str, Any]] = {
    "app": {
        "name": "JyotiGPT",
        "logo_url": "",
    },
    "interface": {
        "default_model": "",
        "default_prompt": "",
    },
    "features": {
        "image_generation": False,
        "image_prompt_generation": False,
        "web_search": False,
        "audio_enabled": True,
    },
    "flows": {
        "url": "",
        "api_key": "",
        "enabled": False,
    },
    "images": {
        "engine": "openai",
        "openai_api_key": "",
        "openai_base_url": "",
        "openai_model": "dall-e-3",
        "automatic1111_base_url": "",
        "comfyui_base_url": "",
        "comfyui_workflow": "",
        "comfyui_api_key": "",
    },
    "audio": {
        "tts_engine": "",
        "stt_engine": "",
    },
    "evaluations": {
        "enable_evaluations": False,
        "model": "",
    },
}


def get_group(session: Session, group: str) -> dict[str, Any]:
    row = session.get(AppSetting, group)
    return dict(row.value) if row else {}


def set_value(session: Session, key: str, value: dict[str, Any]) -> None:
    row = session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        session.add(AppSetting(key=key, value=value))
    session.commit()


def get_all(require_session: str | None = None) -> dict[str, Any]:
    """Return all setting groups merged over defaults.

    `require_session` is accepted for signature symmetry; persistence is
    global, not per-user.
    """
    from jyoti_api.persistence.database import SessionLocal

    merged: dict[str, Any] = {}
    with SessionLocal() as session:
        rows = session.scalars(select(AppSetting)).all()
        for row in rows:
            merged[row.key] = row.value
    for group, defaults in _DEFAULT_GROUPS.items():
        merged.setdefault(group, defaults)
    return merged
