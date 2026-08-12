"""Flow endpoints: /api/v1/flows/* (admin-managed pipeline server config)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from jyoti_api.api.deps import AdminUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.services import flows

router = APIRouter(prefix="/api/v1", tags=["flows"])


class FlowConfig(BaseModel):
    enabled: bool = False
    url: str = ""
    api_key: str = ""
    inlet_enabled: bool = True
    outlet_enabled: bool = True


@router.get("/flows/config")
def get_config(admin: AdminUser, session: SessionDep) -> dict[str, Any]:
    return flows.get_flows_config(session)


@router.put("/flows/config")
def put_config(body: FlowConfig, admin: AdminUser, session: SessionDep) -> dict[str, Any]:
    return flows.save_flows_config(
        session,
        {
            "enabled": body.enabled,
            "url": body.url,
            "api_key": body.api_key,
            "inlet_enabled": body.inlet_enabled,
            "outlet_enabled": body.outlet_enabled,
        },
    )


@router.get("/flows/pipelines")
async def list_pipelines(admin: AdminUser, session: SessionDep) -> dict[str, Any]:
    """Pipelines served by the configured flow server (for the model catalog)."""
    settings = get_settings()
    pipelines = await flows.list_pipelines(session, settings)
    return {"pipelines": pipelines}
