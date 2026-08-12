"""Plugin endpoints: /api/v1/plugins/*

The functions workspace maps onto plugins. ``kind`` selects the behavior:
``prompt`` plugins shape the system prompt, ``tool`` plugins are Python
sources run in the server-side sandbox via POST /plugins/{id}/run.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import plugins
from jyoti_api.errors import NotFoundError
from jyoti_api.services import sandbox

router = APIRouter(prefix="/api/v1", tags=["plugins"])


class PluginWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = "prompt"  # prompt | tool
    description: str = ""
    source: str = ""
    prompt: str = ""
    is_active: bool = True
    meta: dict[str, Any] = {}


class PluginPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: str | None = None
    description: str | None = None
    source: str | None = None
    prompt: str | None = None
    is_active: bool | None = None
    meta: dict[str, Any] | None = None


class PluginRun(BaseModel):
    """Arguments for a sandboxed tool plugin invocation."""

    arguments: dict[str, Any] = {}


class PluginImport(BaseModel):
    plugins: list[dict[str, Any]]


@router.get("/plugins")
def list_plugins(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return plugins.list_plugins(session, user.id)


@router.post("/plugins", status_code=201)
def create_plugin(
    body: PluginWrite, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    plugin = plugins.create_plugin(
        session,
        user.id,
        name=body.name,
        kind=body.kind,
        description=body.description,
        source=body.source,
        prompt=body.prompt,
        is_active=body.is_active,
        meta=body.meta,
    )
    return plugins.to_plugin_dto(plugin)


@router.patch("/plugins/{plugin_id}")
def update_plugin(
    plugin_id: str, body: PluginPatch, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    plugin = plugins.update_plugin(
        session,
        user.id,
        plugin_id,
        name=body.name,
        kind=body.kind,
        description=body.description,
        source=body.source,
        prompt=body.prompt,
        is_active=body.is_active,
        meta=body.meta,
    )
    return plugins.to_plugin_dto(plugin)


@router.delete("/plugins/{plugin_id}")
def delete_plugin(plugin_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    plugins.delete_plugin(session, user.id, plugin_id)
    return {"ok": True}


@router.post("/plugins/{plugin_id}/run")
def run_plugin(
    plugin_id: str, body: PluginRun, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    """Execute a tool plugin in the server-side sandbox."""
    from jyoti_api.domain import plugins as plugin_domain

    plugin = session.get(plugin_domain.Plugin, plugin_id)
    if not plugin or plugin.user_id != user.id:
        raise NotFoundError("Plugin not found.")
    if plugin.kind != "tool":
        return {"error": "Only tool plugins can be run directly."}
    result = sandbox.run_python_tool(plugin.source, body.arguments)
    return {
        "id": plugin.id,
        "name": plugin.name,
        "result": result,
    }


# -------------------------------------------------------------- export/import


@router.get("/plugins/export")
def export_plugins(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    """Download all plugins as a JSON document (backup / migration)."""
    return plugins.export_plugins(session, user.id)


@router.post("/plugins/import", status_code=201)
def import_plugins(
    body: PluginImport, user: CurrentUser, session: SessionDep
) -> list[dict[str, Any]]:
    return plugins.import_plugins(session, user.id, body.plugins)
