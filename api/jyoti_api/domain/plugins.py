"""Plugins (custom functions): persistence + serialization.

Two kinds live in the same table:
- ``prompt`` — a user-authored prompt that is applied to the system prompt
  when the plugin is enabled and selected for a conversation.
- ``tool`` — Python source executed in the server-side sandbox
  (``services/sandbox``). The source must define ``run_tool(context) -> dict``.

Export/import round-trip the whole plugin document so users can back up and
move their functions between instances.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Plugin

PLUGIN_KINDS = ("prompt", "tool")


def to_plugin_dto(plugin: Plugin) -> dict[str, Any]:
    return {
        "id": plugin.id,
        "user_id": plugin.user_id,
        "name": plugin.name,
        "kind": plugin.kind,
        "description": plugin.description,
        "source": plugin.source,
        "prompt": plugin.prompt,
        "is_active": plugin.is_active,
        "meta": plugin.meta or {},
        "created_at": plugin.created_at.isoformat() if plugin.created_at else None,
        "updated_at": plugin.updated_at.isoformat() if plugin.updated_at else None,
    }


def list_plugins(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Plugin).where(Plugin.user_id == user_id).order_by(Plugin.created_at)
    ).all()
    return [to_plugin_dto(p) for p in rows]


def create_plugin(
    session: Session,
    user_id: str,
    *,
    name: str,
    kind: str = "prompt",
    description: str = "",
    source: str = "",
    prompt: str = "",
    is_active: bool = True,
    meta: dict[str, Any] | None = None,
) -> Plugin:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Plugin name is required.")
    if kind not in PLUGIN_KINDS:
        raise ValidationError(f"Plugin kind must be one of {PLUGIN_KINDS}.")
    if kind == "prompt" and not (prompt or "").strip():
        raise ValidationError("Prompt plugins need prompt text.")
    if kind == "tool" and not (source or "").strip():
        raise ValidationError("Tool plugins need Python source.")
    plugin = Plugin(
        user_id=user_id,
        name=name[:200],
        kind=kind,
        description=(description or ""),
        source=source,
        prompt=prompt,
        is_active=is_active,
        meta=meta or {},
    )
    session.add(plugin)
    session.commit()
    session.refresh(plugin)
    return plugin


def _owned(session: Session, user_id: str, plugin_id: str) -> Plugin:
    plugin = session.get(Plugin, plugin_id)
    if not plugin or plugin.user_id != user_id:
        raise NotFoundError("Plugin not found.")
    return plugin


def update_plugin(
    session: Session,
    user_id: str,
    plugin_id: str,
    *,
    name: str | None = None,
    kind: str | None = None,
    description: str | None = None,
    source: str | None = None,
    prompt: str | None = None,
    is_active: bool | None = None,
    meta: dict[str, Any] | None = None,
) -> Plugin:
    plugin = _owned(session, user_id, plugin_id)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("Plugin name is required.")
        plugin.name = name[:200]
    if kind is not None:
        if kind not in PLUGIN_KINDS:
            raise ValidationError(f"Plugin kind must be one of {PLUGIN_KINDS}.")
        plugin.kind = kind
    if description is not None:
        plugin.description = description
    if source is not None:
        plugin.source = source
    if prompt is not None:
        plugin.prompt = prompt
    if is_active is not None:
        plugin.is_active = is_active
    if meta is not None:
        plugin.meta = meta
    session.add(plugin)
    session.commit()
    session.refresh(plugin)
    return plugin


def delete_plugin(session: Session, user_id: str, plugin_id: str) -> None:
    plugin = _owned(session, user_id, plugin_id)
    session.delete(plugin)
    session.commit()


def export_plugins(session: Session, user_id: str) -> list[dict[str, Any]]:
    """Full plugin documents (no per-user ids) for backup / migration."""
    rows = session.scalars(
        select(Plugin).where(Plugin.user_id == user_id).order_by(Plugin.created_at)
    ).all()
    return [
        {
            "name": p.name,
            "kind": p.kind,
            "description": p.description,
            "source": p.source,
            "prompt": p.prompt,
            "is_active": p.is_active,
            "meta": p.meta or {},
        }
        for p in rows
    ]


def import_plugins(
    session: Session, user_id: str, documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Create plugins from exported documents; duplicate names get a suffix."""
    existing = {
        p.name
        for p in session.scalars(
            select(Plugin).where(Plugin.user_id == user_id)
        ).all()
    }
    created = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        name = (str(document.get("name", "")).strip() or "Imported Plugin")[:200]
        kind = document.get("kind", "prompt")
        if kind not in PLUGIN_KINDS:
            kind = "prompt"
        if kind == "tool" and not (document.get("source") or "").strip():
            continue
        if kind == "prompt" and not (document.get("prompt") or "").strip():
            continue
        base, counter = name, 2
        while name in existing:
            name = f"{base} ({counter})"[:200]
            counter += 1
        existing.add(name)
        plugin = create_plugin(
            session,
            user_id,
            name=name,
            kind=kind,
            description=str(document.get("description", "") or ""),
            source=str(document.get("source", "") or ""),
            prompt=str(document.get("prompt", "") or ""),
            is_active=bool(document.get("is_active", True)),
            meta=document.get("meta") or {},
        )
        created.append(to_plugin_dto(plugin))
    return created
