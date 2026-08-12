"""User preferences + memory + profile: /api/v1/users/me/*, /api/v1/memory, /api/v1/about"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from jyoti_api import __version__
from jyoti_api.api.deps import SESSION_COOKIE, CurrentUser, SessionDep
from jyoti_api.config import get_settings as get_env_settings
from jyoti_api.domain import preferences
from jyoti_api.domain import security
from jyoti_api.domain.accounts import to_public

router = APIRouter(prefix="/api/v1", tags=["preferences"])


class SettingsPatch(BaseModel):
    settings: dict[str, Any]


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MemoryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class AvatarUpdate(BaseModel):
    image_data: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=200)


# ------------------------------------------------------------- user settings


@router.get("/users/me/settings")
def get_settings(user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    return preferences.get_user_settings(session, user.id)


@router.post("/users/me/settings")
def update_settings(
    body: SettingsPatch, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return preferences.update_user_settings(session, user.id, body.settings)


# --------------------------------------------------------------------- memory


@router.get("/memory")
def list_memory(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return preferences.list_memory(session, user.id)


@router.post("/memory", status_code=201)
def create_memory(
    body: MemoryCreate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return preferences.add_memory(session, user.id, body.content)


@router.patch("/memory/{entry_id}")
def edit_memory(
    entry_id: str, body: MemoryUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return preferences.update_memory(session, user.id, entry_id, body.content)


@router.delete("/memory/{entry_id}")
def remove_memory(
    entry_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    preferences.delete_memory(session, user.id, entry_id)
    return {"ok": True}


# ------------------------------------------------------------------- profile


@router.post("/users/me/avatar")
def update_avatar(
    body: AvatarUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return preferences.set_avatar(session, user, body.image_data)


@router.post("/users/me/password")
def change_password(
    body: PasswordChange,
    user: CurrentUser,
    session: SessionDep,
    request: Request,
) -> dict[str, bool]:
    jti = _session_jti(request)
    preferences.change_password(
        session, user, body.current_password, body.new_password, current_jti=jti
    )
    return {"ok": True}


def _session_jti(request: Request) -> str | None:
    """Extract the jti of the session cookie that authenticated this request."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    try:
        payload = security.decode_token(cookie)
        return payload.get("jti")
    except Exception:
        return None


# --------------------------------------------------------------------- about


@router.get("/about")
def about() -> dict[str, Any]:
    env = get_env_settings()
    return {
        "version": __version__,
        "app_name": env.app_name,
        "environment": env.app_env,
        "created_by": "JyotiGPT project",
        "models": _ollama_version(),
    }


def _ollama_version() -> str:
    """Best-effort Ollama version probe; empty when unreachable."""
    try:
        import httpx

        env = get_env_settings()
        base = env.ollama_base_url.rstrip("/")
        response = httpx.get(f"{base}/api/version", timeout=3)
        if response.status_code == 200:
            return str(response.json().get("version", ""))
    except Exception:
        pass
    return ""
