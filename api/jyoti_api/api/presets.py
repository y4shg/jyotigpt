"""Preset endpoints: /api/v1/presets/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import presets

router = APIRouter(prefix="/api/v1", tags=["presets"])


class PresetWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_command: bool = False
    meta: dict[str, Any] = {}


class PresetPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    is_command: bool | None = None
    meta: dict[str, Any] | None = None


@router.get("/presets")
def list_presets(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return presets.list_presets(session, user.id)


@router.post("/presets", status_code=201)
def create_preset(
    body: PresetWrite, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    preset = presets.create_preset(
        session,
        user.id,
        name=body.name,
        content=body.content,
        is_command=body.is_command,
        meta=body.meta,
    )
    return presets.to_preset_dto(preset)


@router.patch("/presets/{preset_id}")
def update_preset(
    preset_id: str, body: PresetPatch, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    preset = presets.update_preset(
        session,
        user.id,
        preset_id,
        name=body.name,
        content=body.content,
        is_command=body.is_command,
        meta=body.meta,
    )
    return presets.to_preset_dto(preset)


@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    presets.delete_preset(session, user.id, preset_id)
    return {"ok": True}
