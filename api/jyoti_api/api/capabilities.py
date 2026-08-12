"""Capability endpoints: /api/v1/capabilities/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import capabilities

router = APIRouter(prefix="/api/v1", tags=["capabilities"])


class CapabilityWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    spec: dict[str, Any] | str | None = None
    is_active: bool = True


class CapabilityPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    spec: dict[str, Any] | str | None = None
    is_active: bool | None = None


@router.get("/capabilities")
def list_capabilities(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return capabilities.list_capabilities(session, user.id)


@router.post("/capabilities", status_code=201)
def create_capability(
    body: CapabilityWrite, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    capability = capabilities.create_capability(
        session,
        user.id,
        name=body.name,
        description=body.description,
        spec=body.spec,
        is_active=body.is_active,
    )
    return capabilities.to_capability_dto(capability)


@router.patch("/capabilities/{capability_id}")
def update_capability(
    capability_id: str, body: CapabilityPatch, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    capability = capabilities.update_capability(
        session,
        user.id,
        capability_id,
        name=body.name,
        description=body.description,
        spec=body.spec,
        is_active=body.is_active,
    )
    return capabilities.to_capability_dto(capability)


@router.delete("/capabilities/{capability_id}")
def delete_capability(
    capability_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    capabilities.delete_capability(session, user.id, capability_id)
    return {"ok": True}
