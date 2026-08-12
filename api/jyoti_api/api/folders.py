"""Folders + share endpoints: /api/v1/folders/*, /api/v1/share/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.domain import conversations, folders

router = APIRouter(prefix="/api/v1", tags=["folders"])


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None


class FolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


# ------------------------------------------------------------------ folders


@router.get("/folders")
def list_folders(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return folders.list_folders(session, user.id)


@router.post("/folders", status_code=201)
def create_folder(body: FolderCreate, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    folder = folders.create_folder(session, user.id, body.name, body.parent_id)
    return folders.to_folder_dto(session, folder)


@router.patch("/folders/{folder_id}")
def update_folder(
    folder_id: str, body: FolderUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    folder = folders.rename_folder(session, user.id, folder_id, body.name)
    return folders.to_folder_dto(session, folder)


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    folders.delete_folder(session, user.id, folder_id)
    return {"ok": True}


# -------------------------------------------------------------------- share


@router.post("/conversations/{conversation_id}/share")
def share_conversation(
    conversation_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    conversation = conversations.create_share(session, user.id, conversation_id)
    settings = get_settings()
    url = f"{settings.webui_url.rstrip('/')}/s/{conversation.share_id}"
    return {"share_id": conversation.share_id, "url": url}


@router.delete("/conversations/{conversation_id}/share")
def unshare_conversation(
    conversation_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    conversations.clear_share(session, user.id, conversation_id)
    return {"ok": True}


@router.get("/share/{share_id}")
def get_shared_conversation(share_id: str, session: SessionDep) -> dict[str, Any]:
    """Public share link — deliberately outside the auth dependency."""
    return conversations.get_public_share(session, share_id)
