"""Conversations + messages endpoints: /api/v1/conversations/*, /api/v1/messages/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import conversations
from jyoti_api.persistence.schema import User

router = APIRouter(prefix="/api/v1", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str = "New Chat"
    folder_id: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    folder_id: str | None = None
    archived: bool | None = None
    pinned: bool | None = None


class MessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = ""
    model: str = ""
    provider: str = ""


class MessageUpdate(BaseModel):
    content: str | None = None
    done: bool | None = None
    error: str | None = None


# -------------------------------------------------------------- conversations


@router.get("/conversations")
def list_conversations(
    user: CurrentUser,
    session: SessionDep,
    search: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    archived: bool = Query(default=False),
) -> dict[str, Any]:
    if archived:
        rows = conversations.list_archived(session, user.id)
    else:
        rows = conversations.list_conversations(session, user.id, search=search, page=page)
    return {"page": page, "conversations": rows}


@router.post("/conversations", status_code=201)
def create_conversation(
    body: ConversationCreate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    conversation = conversations.create_conversation(session, user.id, body.title, body.folder_id)
    return conversations.to_conversation_dto(session, conversation)


class ConversationImport(BaseModel):
    conversations: list[dict[str, Any]]


@router.get("/conversations/export")
def export_conversations(
    user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    rows = conversations.export_conversations(session, user.id)
    return {"conversations": rows, "count": len(rows)}


@router.post("/conversations/import", status_code=201)
def import_conversations(
    body: ConversationImport, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    count = conversations.import_conversations(session, user.id, body.conversations)
    return {"count": count}


@router.post("/conversations/actions/archive-all")
def archive_all(user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    count = conversations.archive_all_conversations(session, user.id)
    return {"count": count}


@router.post("/conversations/actions/delete-all")
def delete_all(user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    count = conversations.delete_all_conversations(session, user.id)
    return {"count": count}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    conversation = conversations.get_conversation(session, user.id, conversation_id)
    payload = conversations.to_conversation_dto(session, conversation)
    payload["messages"] = conversations.list_messages(session, user.id, conversation_id)
    return payload


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: str, body: ConversationUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    conversation = conversations.update_conversation(
        session,
        user.id,
        conversation_id,
        title=body.title,
        folder_id=body.folder_id,
        archived=body.archived,
        pinned=body.pinned,
    )
    return conversations.to_conversation_dto(session, conversation)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    conversations.delete_conversation(session, user.id, conversation_id)
    return {"ok": True}


# ------------------------------------------------------------------- messages


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str, user: CurrentUser, session: SessionDep
) -> list[dict[str, Any]]:
    return conversations.list_messages(session, user.id, conversation_id)


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def add_message(
    conversation_id: str, body: MessageCreate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    message = conversations.add_message(
        session,
        user.id,
        conversation_id,
        role=body.role,
        content=body.content,
        model=body.model,
        provider=body.provider,
    )
    return conversations.to_message_dto(message)


@router.patch("/messages/{message_id}")
def update_message(
    message_id: str, body: MessageUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    message = conversations.update_message(
        session,
        user.id,
        message_id,
        content=body.content,
        done=body.done,
        error=body.error,
    )
    return conversations.to_message_dto(message)


@router.delete("/messages/{message_id}")
def delete_message(message_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    conversations.delete_message(session, user.id, message_id)
    return {"ok": True}
