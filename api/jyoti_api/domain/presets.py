"""Presets (prompts): persistence + serialization.

A preset is a reusable prompt a user can drop into the composer. Slash
commands are the same data with ``is_command`` set; the composer resolves
``/name`` to the preset content.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Preset


def to_preset_dto(preset: Preset) -> dict[str, Any]:
    return {
        "id": preset.id,
        "user_id": preset.user_id,
        "name": preset.name,
        "content": preset.content,
        "is_command": preset.is_command,
        "meta": preset.meta or {},
        "created_at": preset.created_at.isoformat() if preset.created_at else None,
        "updated_at": preset.updated_at.isoformat() if preset.updated_at else None,
    }


def list_presets(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Preset).where(Preset.user_id == user_id).order_by(Preset.created_at)
    ).all()
    return [to_preset_dto(p) for p in rows]


def create_preset(
    session: Session,
    user_id: str,
    *,
    name: str,
    content: str,
    is_command: bool = False,
    meta: dict[str, Any] | None = None,
) -> Preset:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Preset name is required.")
    if not (content or "").strip():
        raise ValidationError("Preset content is required.")
    if is_command and not name.startswith("/"):
        name = f"/{name}"
    preset = Preset(
        user_id=user_id,
        name=name[:200],
        content=content,
        is_command=is_command,
        meta=meta or {},
    )
    session.add(preset)
    session.commit()
    session.refresh(preset)
    return preset


def _owned(session: Session, user_id: str, preset_id: str) -> Preset:
    preset = session.get(Preset, preset_id)
    if not preset or preset.user_id != user_id:
        raise NotFoundError("Preset not found.")
    return preset


def update_preset(
    session: Session,
    user_id: str,
    preset_id: str,
    *,
    name: str | None = None,
    content: str | None = None,
    is_command: bool | None = None,
    meta: dict[str, Any] | None = None,
) -> Preset:
    preset = _owned(session, user_id, preset_id)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("Preset name is required.")
        preset.name = name[:200] if not (is_command or preset.is_command) else (
            f"/{name}" if not name.startswith("/") else name
        )[:200]
    if content is not None:
        if not content.strip():
            raise ValidationError("Preset content is required.")
        preset.content = content
    if is_command is not None:
        preset.is_command = is_command
    if meta is not None:
        preset.meta = meta
    session.add(preset)
    session.commit()
    session.refresh(preset)
    return preset


def delete_preset(session: Session, user_id: str, preset_id: str) -> None:
    preset = _owned(session, user_id, preset_id)
    session.delete(preset)
    session.commit()
