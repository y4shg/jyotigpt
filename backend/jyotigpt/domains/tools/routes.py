"""Tool HTTP routes.

Local tools are user-authored Python toolkits; the catalogue also lists
remote tool servers discovered over OpenAPI (loaded lazily once per server
lifetime and cached on the application state). Admins and the owning user
manage a tool's code; valves (per-tool and per-user) are the Pydantic config
models the tool module exposes. The valve-update endpoint is intentionally
more permissive in its ownership check (400 instead of 401) to match the
historical surface.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.tools import (
    ToolForm,
    ToolModel,
    ToolResponse,
    ToolUserResponse,
)
from jyotigpt.utils.access_control import has_access, has_permission
from jyotigpt.utils.auth import get_admin_user, get_verified_user

from .service import tools

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


@router.get("/", response_model=list[ToolUserResponse])
async def get_tools(request: Request, user=Depends(get_verified_user)):
    return await tools.list_tools(request.app.state, user)


@router.get("/list", response_model=list[ToolUserResponse])
async def get_tool_list(user=Depends(get_verified_user)):
    if user.role == "admin":
        return tools.list_all()
    return tools.list_for_write(user.id)


@router.get("/export", response_model=list[ToolModel])
async def export_tools(user=Depends(get_admin_user)):
    return tools.list_all()


@router.post("/create", response_model=Optional[ToolResponse])
async def create_new_tools(
    request: Request,
    form_data: ToolForm,
    user=Depends(get_verified_user),
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.tools", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters and underscores are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    if tools.get(form_data.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )

    try:
        tool = tools.create(form_data, user.id, request.app.state.TOOLS)
        if tool:
            return tool
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error creating tools"),
        )
    except Exception as e:
        log.exception(f"Failed to load the tool by id {form_data.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


@router.get("/id/{id}", response_model=Optional[ToolModel])
async def get_tools_by_id(id: str, user=Depends(get_verified_user)):
    tool = tools.get(id)

    if tool:
        if (
            user.role == "admin"
            or tool.user_id == user.id
            or has_access(user.id, "read", tool.access_control)
        ):
            return tool
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/id/{id}/update", response_model=Optional[ToolModel])
async def update_tools_by_id(
    request: Request,
    id: str,
    form_data: ToolForm,
    user=Depends(get_verified_user),
):
    tool = tools.get(id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only the owning user, a group with write access, or an admin may edit.
    if (
        tool.user_id != user.id
        and not has_access(user.id, "write", tool.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        updated = tools.update(id, form_data, request.app.state.TOOLS)
        if updated:
            return updated
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error updating tools"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_tools_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    tool = tools.get(id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tool.user_id != user.id
        and not has_access(user.id, "write", tool.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    return tools.delete(id, request.app.state.TOOLS)


@router.get("/id/{id}/valves", response_model=Optional[dict])
async def get_tools_valves_by_id(id: str, user=Depends(get_verified_user)):
    tool = tools.get(id)
    if tool:
        try:
            return tools.get_valves(id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(str(e)),
            )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


@router.get("/id/{id}/valves/spec", response_model=Optional[dict])
async def get_tools_valves_spec_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    tool = tools.get(id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    module = tools.module_for(id, request.app.state.TOOLS)
    return tools.valves_schema(module)


@router.post("/id/{id}/valves/update", response_model=Optional[dict])
async def update_tools_valves_by_id(
    request: Request, id: str, form_data: dict, user=Depends(get_verified_user)
):
    tool = tools.get(id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tool.user_id != user.id
        and not has_access(user.id, "write", tool.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    module = tools.module_for(id, request.app.state.TOOLS)
    if not hasattr(module, "Valves"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        return tools.update_valves(id, module, form_data)
    except Exception as e:
        log.exception(f"Failed to update tool valves by id {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


@router.get("/id/{id}/valves/user", response_model=Optional[dict])
async def get_tools_user_valves_by_id(id: str, user=Depends(get_verified_user)):
    tool = tools.get(id)
    if tool:
        try:
            return tools.get_user_valves(id, user.id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(str(e)),
            )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


@router.get("/id/{id}/valves/user/spec", response_model=Optional[dict])
async def get_tools_user_valves_spec_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    tool = tools.get(id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    module = tools.module_for(id, request.app.state.TOOLS)
    return tools.user_valves_schema(module)


@router.post("/id/{id}/valves/user/update", response_model=Optional[dict])
async def update_tools_user_valves_by_id(
    request: Request, id: str, form_data: dict, user=Depends(get_verified_user)
):
    tool = tools.get(id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    module = tools.module_for(id, request.app.state.TOOLS)
    if not hasattr(module, "UserValves"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        return tools.update_user_valves(id, user.id, module, form_data)
    except Exception as e:
        log.exception(f"Failed to update user valves by id {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )
