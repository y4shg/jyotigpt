"""Realtime room hub: live presence and message fan-out over WebSockets.

A single connection may subscribe to several rooms at once. The wire protocol
is JSON messages:

    client → server::
        {"op": "join",    "room_id": "..."}
        {"op": "leave",   "room_id": "..."}
        {"op": "message", "room_id": "...", "content": "..."}
        {"op": "typing",  "room_id": "...", "typing": true}

    server → client::
        {"type": "presence", "room_id", "action": "joined"|"left", "user": {...}}
        {"type": "members",  "room_id", "users": [...]}          # on join
        {"type": "message",  "room_id", "message": {...}}        # broadcast
        {"type": "typing",   "room_id", "user": {...}, "typing": true}
        {"type": "error",    "message": "..."}

Authentication happens before the connection is accepted (JWT via ``?token=``
query, the session cookie, or an API key); membership is re-checked on every
``join`` so a leaving member stops receiving events.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from jyoti_api.domain.accounts import to_public
from jyoti_api.domain.rooms import create_message, to_message_dto, _get_room, _is_member
from jyoti_api.persistence.database import SessionLocal
from jyoti_api.persistence.schema import User

logger = logging.getLogger("jyoti_api.realtime")


class RoomHub:
    """Per-room connection registry with a small lock around mutations."""

    def __init__(self) -> None:
        self._rooms: dict[str, dict[WebSocket, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket, room_id: str, user: User) -> None:
        async with self._lock:
            self._rooms.setdefault(room_id, {})[websocket] = {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
            }

    async def unsubscribe(self, websocket: WebSocket, room_id: str) -> None:
        async with self._lock:
            members = self._rooms.get(room_id)
            if members:
                members.pop(websocket, None)
                if not members:
                    self._rooms.pop(room_id, None)

    async def room_users(self, room_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            members = self._rooms.get(room_id, {})
            seen: dict[str, dict[str, Any]] = {}
            for info in members.values():
                seen.setdefault(info["user_id"], info)
            return list(seen.values())

    async def broadcast(self, room_id: str, payload: dict[str, Any], exclude: WebSocket | None = None) -> None:
        async with self._lock:
            targets = list(self._rooms.get(room_id, {}).keys())
        for target in targets:
            if target is exclude:
                continue
            try:
                await target.send_json(payload)
            except Exception:  # noqa: BLE001 — a dead socket must not break the loop
                await self.unsubscribe(target, room_id)


hub = RoomHub()


async def _authenticate(websocket: WebSocket) -> User | None:
    """Resolve the user from a query token, the session cookie, or an API key."""
    from jyoti_api.api.deps import _user_from_token
    from jyoti_api.domain.security import _hash_api_key
    from jyoti_api.persistence.schema import ApiKey, Session as DbSession

    token = websocket.query_params.get("token")
    if token:
        with SessionLocal() as session:
            user = _user_from_token(session, token)
            if user:
                return user

    cookie = websocket.cookies.get("jyoti_session")
    if cookie:
        with SessionLocal() as session:
            user = _user_from_token(session, cookie)
            if user:
                return user

    key = websocket.query_params.get("key")
    if key:
        with SessionLocal() as session:
            key_hash = _hash_api_key(key)
            record = session.scalars(
                select(ApiKey).where(ApiKey.key_hash == key_hash)
            ).first()
            if record:
                user = session.get(User, record.user_id)
                if user and user.status != "deactivated":
                    return user
    return None


async def rooms_websocket(
    websocket: WebSocket, token: str | None = Query(default=None)
) -> None:
    user = await _authenticate(websocket)
    if not user:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    subscribed: set[str] = set()

    async def announce(room_id: str, action: str, exclude: WebSocket | None = None) -> None:
        await hub.broadcast(
            room_id,
            {"type": "presence", "room_id": room_id, "action": action, "user": to_public(user)},
            exclude=exclude,
        )

    try:
        while True:
            data = await websocket.receive_json()
            op = data.get("op")
            room_id = str(data.get("room_id", ""))
            if op == "join" and room_id:
                with SessionLocal() as session:
                    room = _get_room(session, room_id)
                    if not _is_member(session, user.id, room):
                        await websocket.send_json(
                            {"type": "error", "message": "You are not a member of this room."}
                        )
                        continue
                if room_id not in subscribed:
                    subscribed.add(room_id)
                    await hub.subscribe(websocket, room_id, user)
                    await announce(room_id, "joined", exclude=websocket)
                users = await hub.room_users(room_id)
                await websocket.send_json({"type": "members", "room_id": room_id, "users": users})

            elif op == "leave" and room_id:
                if room_id in subscribed:
                    subscribed.discard(room_id)
                    await hub.unsubscribe(websocket, room_id)
                    await announce(room_id, "left")

            elif op == "message" and room_id:
                if room_id not in subscribed:
                    await websocket.send_json(
                        {"type": "error", "message": "Join the room before sending messages."}
                    )
                    continue
                content = str(data.get("content", ""))
                with SessionLocal() as session:
                    message = create_message(session, user.id, room_id, content)
                    payload = {"type": "message", "room_id": room_id, "message": to_message_dto(session, message)}
                await hub.broadcast(payload["room_id"], payload)

            elif op == "typing" and room_id:
                await hub.broadcast(
                    room_id,
                    {
                        "type": "typing",
                        "room_id": room_id,
                        "user": to_public(user),
                        "typing": bool(data.get("typing", False)),
                    },
                    exclude=websocket,
                )
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("rooms ws error: %s", exc)
    finally:
        for room_id in list(subscribed):
            await hub.unsubscribe(websocket, room_id)
            await announce(room_id, "left")
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
