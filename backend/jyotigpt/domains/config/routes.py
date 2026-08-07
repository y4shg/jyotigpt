"""Configuration HTTP routes.

All settings are admin-scoped except the public banner list. Import/export
round-trips through the persisted config file; the rest mutate the live
config instance on the application state.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from jyotigpt.config import BannerModel
from jyotigpt.utils.auth import get_admin_user, get_verified_user

from .service import configs

router = APIRouter()


class ImportConfigForm(BaseModel):
    config: dict


@router.post("/import", response_model=dict)
async def import_config(form_data: ImportConfigForm, user=Depends(get_admin_user)):
    return configs.import_(form_data.config)


@router.get("/export", response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return configs.export()


class DirectConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool


@router.get("/direct_connections", response_model=DirectConnectionsConfigForm)
async def get_direct_connections_config(
    request: Request, user=Depends(get_admin_user)
):
    return configs.get_direct_connections(request.app.state.config)


@router.post("/direct_connections", response_model=DirectConnectionsConfigForm)
async def set_direct_connections_config(
    request: Request,
    form_data: DirectConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    return configs.set_direct_connections(
        request.app.state.config, form_data.ENABLE_DIRECT_CONNECTIONS
    )


class ToolServerConnection(BaseModel):
    url: str
    path: str
    auth_type: Optional[str]
    key: Optional[str]
    config: Optional[dict]

    model_config = ConfigDict(extra="allow")


class ToolServersConfigForm(BaseModel):
    TOOL_SERVER_CONNECTIONS: list[ToolServerConnection]


@router.get("/tool_servers", response_model=ToolServersConfigForm)
async def get_tool_servers_config(request: Request, user=Depends(get_admin_user)):
    return configs.get_tool_servers(request.app.state.config)


@router.post("/tool_servers", response_model=ToolServersConfigForm)
async def set_tool_servers_config(
    request: Request,
    form_data: ToolServersConfigForm,
    user=Depends(get_admin_user),
):
    connections = [
        connection.model_dump() for connection in form_data.TOOL_SERVER_CONNECTIONS
    ]
    return await configs.set_tool_servers(request.app.state, connections)


@router.post("/tool_servers/verify")
async def verify_tool_servers_config(
    request: Request, form_data: ToolServerConnection, user=Depends(get_admin_user)
):
    """Verify the connection to the tool server."""
    try:
        token = None
        if form_data.auth_type == "bearer":
            token = form_data.key
        elif form_data.auth_type == "session":
            token = request.state.token.credentials

        url = f"{form_data.url}/{form_data.path}"
        return await configs.verify_connection(token, url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to the tool server: {str(e)}",
        )


class CodeInterpreterConfigForm(BaseModel):
    ENABLE_CODE_EXECUTION: bool
    CODE_EXECUTION_ENGINE: str
    CODE_EXECUTION_JUPYTER_URL: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_EXECUTION_JUPYTER_TIMEOUT: Optional[int]
    ENABLE_CODE_INTERPRETER: bool
    CODE_INTERPRETER_ENGINE: str
    CODE_INTERPRETER_PROMPT_TEMPLATE: Optional[str]
    CODE_INTERPRETER_JUPYTER_URL: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_INTERPRETER_JUPYTER_TIMEOUT: Optional[int]


@router.get("/code_execution", response_model=CodeInterpreterConfigForm)
async def get_code_execution_config(
    request: Request, user=Depends(get_admin_user)
):
    return configs.get_code_execution(request.app.state.config)


@router.post("/code_execution", response_model=CodeInterpreterConfigForm)
async def set_code_execution_config(
    request: Request,
    form_data: CodeInterpreterConfigForm,
    user=Depends(get_admin_user),
):
    return configs.set_code_execution(request.app.state.config, form_data.model_dump())


class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: Optional[str]
    MODEL_ORDER_LIST: Optional[list[str]]


@router.get("/models", response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    return configs.get_models(request.app.state.config)


@router.post("/models", response_model=ModelsConfigForm)
async def set_models_config(
    request: Request,
    form_data: ModelsConfigForm,
    user=Depends(get_admin_user),
):
    return configs.set_models(request.app.state.config, form_data.model_dump())


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post("/suggestions", response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_admin_user),
):
    return configs.set_suggestions(
        request.app.state.config, form_data.model_dump()["suggestions"]
    )


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post("/banners", response_model=list[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    return configs.set_banners(request.app.state.config, form_data.model_dump()["banners"])


@router.get("/banners", response_model=list[BannerModel])
async def get_banners(request: Request, user=Depends(get_verified_user)):
    return configs.get_banners(request.app.state.config)
