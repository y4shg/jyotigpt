"""Rooms endpoints: /api/v1/rooms (REST) + the /ws realtime socket."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import rooms as domain
from jyoti_api.realtime.rooms import rooms_websocket

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    is_public: bool = False


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MemberAdd(BaseModel):
    """Add a member by user id, or by email (resolved server-side)."""

    user_id: str | None = None
    email: str | None = Field(default=None, max_length=320)


class RoleUpdate(BaseModel):
    role: str


@router.websocket("/ws")
async def ws(websocket: WebSocket, token: str | None = None) -> None:
    """Live room events. Auth via ``?token=``, the session cookie, or ``?key=``."""
    await rooms_websocket(websocket, token=token)


@router.get("")
def list_rooms(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return domain.list_rooms(session, user.id)


@router.post("", status_code=201)
def create_room(body: RoomCreate, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    room = domain.create_room(session, user.id, body.name, body.description, body.is_public)
    return domain.to_room_dto(session, room, user.id)


@router.get("/{room_id}")
def get_room(room_id: str, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    return domain.get_room(session, user.id, room_id)


@router.patch("/{room_id}")
def update_room(
    room_id: str, body: RoomUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    room = domain.update_room(
        session, user.id, room_id, body.name, body.description, body.is_public
    )
    return domain.to_room_dto(session, room, user.id)


@router.delete("/{room_id}")
def delete_room(room_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    domain.delete_room(session, user.id, room_id)
    return {"ok": True}


# ------------------------------------------------------------------ membership


@router.post("/{room_id}/join")
def join_room(room_id: str, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    return domain.join_room(session, user.id, room_id)


@router.post("/{room_id}/leave")
def leave_room(room_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    domain.leave_room(session, user.id, room_id)
    return {"ok": True}


@router.get("/{room_id}/members")
def list_members(room_id: str, user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return domain.list_members(session, user.id, room_id)


@router.post("/{room_id}/members", status_code=201)
def add_member(
    room_id: str, body: MemberAdd, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return domain.add_member(session, user.id, room_id, body.user_id, email=body.email)


@router.delete("/{room_id}/members/{target_id}")
def remove_member(
    room_id: str, target_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    domain.remove_member(session, user.id, room_id, target_id)
    return {"ok": True}


@router.patch("/{room_id}/members/{target_id}")
def set_role(
    room_id: str, target_id: str, body: RoleUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return domain.set_member_role(session, user.id, room_id, target_id, body.role)


# ------------------------------------------------------------------ messages


@router.get("/{room_id}/messages")
def list_messages(
    room_id: str,
    user: CurrentUser,
    session: SessionDep,
    before_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    return domain.list_messages(session, user.id, room_id, before_id=before_id, limit=limit)


@router.post("/{room_id}/messages", status_code=201)
def create_message(
    room_id: str, body: MessageCreate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    message = domain.create_message(session, user.id, room_id, body.content)
    return domain.to_message_dto(session, message)


@router.delete("/{room_id}/messages/{message_id}")
def delete_message(
    room_id: str, message_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    domain.delete_message(session, user.id, room_id, message_id)
    return {"ok": True}
