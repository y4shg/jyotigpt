"""Capabilities (OpenAPI tool servers): persistence + serialization.

A capability wraps an OpenAPI spec that describes a set of callable
operations (tools). The spec is stored as-is so the chat layer can map
operations onto provider tool-call schemas later; today capabilities can be
managed and enabled/disabled, and the spec is validated for basic shape on
write.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Capability


def to_capability_dto(capability: Capability) -> dict[str, Any]:
    return {
        "id": capability.id,
        "user_id": capability.user_id,
        "name": capability.name,
        "description": capability.description,
        "spec": capability.spec or {},
        "is_active": capability.is_active,
        "created_at": capability.created_at.isoformat() if capability.created_at else None,
        "updated_at": capability.updated_at.isoformat() if capability.updated_at else None,
    }


def _parse_spec(raw: dict[str, Any] | str | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ValidationError("Capability spec must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValidationError("Capability spec must be a JSON object.")
    return parsed


def list_capabilities(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Capability).where(Capability.user_id == user_id).order_by(Capability.created_at)
    ).all()
    return [to_capability_dto(c) for c in rows]


def create_capability(
    session: Session,
    user_id: str,
    *,
    name: str,
    description: str = "",
    spec: dict[str, Any] | str | None = None,
    is_active: bool = True,
) -> Capability:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Capability name is required.")
    capability = Capability(
        user_id=user_id,
        name=name[:200],
        description=(description or ""),
        spec=_parse_spec(spec),
        is_active=is_active,
    )
    session.add(capability)
    session.commit()
    session.refresh(capability)
    return capability


def _owned(session: Session, user_id: str, capability_id: str) -> Capability:
    capability = session.get(Capability, capability_id)
    if not capability or capability.user_id != user_id:
        raise NotFoundError("Capability not found.")
    return capability


def update_capability(
    session: Session,
    user_id: str,
    capability_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    spec: dict[str, Any] | str | None = None,
    is_active: bool | None = None,
) -> Capability:
    capability = _owned(session, user_id, capability_id)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("Capability name is required.")
        capability.name = name[:200]
    if description is not None:
        capability.description = description
    if spec is not None:
        capability.spec = _parse_spec(spec)
    if is_active is not None:
        capability.is_active = is_active
    session.add(capability)
    session.commit()
    session.refresh(capability)
    return capability


def delete_capability(session: Session, user_id: str, capability_id: str) -> None:
    capability = _owned(session, user_id, capability_id)
    session.delete(capability)
    session.commit()
