"""Rooms: shared real-time chat spaces with membership and message history.

A room is owned by whoever created it (role ``owner``) and has exactly one
access mode: public (anyone may join) or private (only the owner can add
members). Members post messages; the owner manages membership and the room
itself. Global admins may also delete rooms/messages for moderation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jyoti_api.domain.accounts import ROLE_ADMIN
from jyoti_api.errors import ForbiddenError, NotFoundError, ValidationError
from jyoti_api.persistence.schema import Room, RoomMember, RoomMessage, User

ROLE_OWNER = "owner"
ROLE_MEMBER = "member"


# ------------------------------------------------------------------ serialization


def to_room_dto(session: Session, room: Room, user_id: str | None = None) -> dict[str, Any]:
    member_count = session.scalar(
        select(func.count(RoomMember.user_id)).where(RoomMember.room_id == room.id)
    )
    member_role: str | None = None
    if user_id:
        row = session.get(RoomMember, (room.id, user_id))
        member_role = row.role if row else None
    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
        "created_by": room.created_by,
        "is_public": room.is_public,
        "is_member": member_role is not None,
        "role": member_role,
        "member_count": member_count or 0,
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


def to_member_dto(session: Session, member: RoomMember) -> dict[str, Any]:
    name = ""
    if member.user:
        name = member.user.name
    return {
        "user_id": member.user_id,
        "name": name,
        "role": member.role,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
    }


def to_message_dto(session: Session, message: RoomMessage) -> dict[str, Any]:
    name = ""
    if message.user:
        name = message.user.name
    return {
        "id": message.id,
        "room_id": message.room_id,
        "user_id": message.user_id,
        "name": name,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


# ------------------------------------------------------------------ rooms


def list_rooms(session: Session, user_id: str) -> list[dict[str, Any]]:
    """Rooms the user belongs to, plus public rooms (with the member flag)."""
    member_of = select(RoomMember.room_id).where(RoomMember.user_id == user_id)
    rows = session.scalars(
        select(Room)
        .where((Room.is_public.is_(True)) | (Room.id.in_(member_of)))
        .order_by(Room.created_at.desc())
    ).all()
    return [to_room_dto(session, room, user_id) for room in rows]


def create_room(
    session: Session,
    user_id: str,
    name: str,
    description: str = "",
    is_public: bool = False,
) -> Room:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Room name is required.")
    room = Room(name=name[:200], description=(description or "")[:2000], created_by=user_id, is_public=is_public)
    session.add(room)
    session.flush()
    session.add(
        RoomMember(room_id=room.id, user_id=user_id, role=ROLE_OWNER)
    )
    session.commit()
    session.refresh(room)
    return room


def _get_room(session: Session, room_id: str) -> Room:
    room = session.get(Room, room_id)
    if not room:
        raise NotFoundError("Room not found.")
    return room


def get_room(session: Session, user_id: str, room_id: str) -> dict[str, Any]:
    room = _get_room(session, room_id)
    if not _can_view(session, user_id, room):
        raise ForbiddenError("You are not a member of this room.")
    return to_room_dto(session, room, user_id)


def update_room(
    session: Session,
    user_id: str,
    room_id: str,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
) -> Room:
    room = _get_room(session, room_id)
    _require_owner(session, user_id, room)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("Room name is required.")
        room.name = name[:200]
    if description is not None:
        room.description = description[:2000]
    if is_public is not None:
        room.is_public = is_public
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def delete_room(session: Session, user_id: str, room_id: str) -> None:
    room = _get_room(session, room_id)
    _require_owner(session, user_id, room)
    session.delete(room)
    session.commit()


def _can_view(session: Session, user_id: str, room: Room) -> bool:
    if room.is_public:
        return True
    return session.get(RoomMember, (room.id, user_id)) is not None


def _is_member(session: Session, user_id: str, room: Room) -> bool:
    return session.get(RoomMember, (room.id, user_id)) is not None


def _require_owner(session: Session, user_id: str, room: Room) -> None:
    """Allow the creator, global admins, and members with the owner role."""
    if user_id == room.created_by:
        return
    user = session.get(User, user_id)
    if user and user.role == ROLE_ADMIN:
        return
    member = session.get(RoomMember, (room.id, user_id))
    if member and member.role == ROLE_OWNER:
        return
    raise ForbiddenError("Only the room owner can do that.")


def _require_member(session: Session, user_id: str, room: Room) -> None:
    if not _is_member(session, user_id, room):
        raise ForbiddenError("You are not a member of this room.")


# ------------------------------------------------------------------ membership


def join_room(session: Session, user_id: str, room_id: str) -> dict[str, Any]:
    room = _get_room(session, room_id)
    if not room.is_public:
        raise ForbiddenError("This room is private. Ask the owner to add you.")
    existing = session.get(RoomMember, (room.id, user_id))
    if not existing:
        session.add(RoomMember(room_id=room.id, user_id=user_id, role=ROLE_MEMBER))
        session.commit()
    return to_room_dto(session, room, user_id)


def leave_room(session: Session, user_id: str, room_id: str) -> None:
    room = _get_room(session, room_id)
    if user_id == room.created_by:
        raise ValidationError("The room owner cannot leave; delete the room instead.")
    member = session.get(RoomMember, (room.id, user_id))
    if member:
        session.delete(member)
        session.commit()


def add_member(
    session: Session,
    owner_id: str,
    room_id: str,
    target_id: str | None = None,
    *,
    email: str | None = None,
) -> dict[str, Any]:
    room = _get_room(session, room_id)
    _require_owner(session, owner_id, room)
    if target_id:
        target = session.get(User, target_id)
    elif email:
        target = session.scalars(
            select(User).where(func.lower(User.email) == (email or "").strip().lower())
        ).first()
    else:
        raise ValidationError("Provide a user_id or email.")
    if not target:
        raise NotFoundError("User not found.")
    existing = session.get(RoomMember, (room.id, target.id))
    if not existing:
        existing = RoomMember(room_id=room.id, user_id=target.id, role=ROLE_MEMBER)
        session.add(existing)
        session.commit()
    return to_member_dto(session, existing)


def remove_member(session: Session, owner_id: str, room_id: str, target_id: str) -> None:
    room = _get_room(session, room_id)
    _require_owner(session, owner_id, room)
    if target_id == room.created_by:
        raise ValidationError("Cannot remove the room owner.")
    member = session.get(RoomMember, (room.id, target_id))
    if not member:
        raise NotFoundError("That user is not a member.")
    session.delete(member)
    session.commit()


def set_member_role(
    session: Session, owner_id: str, room_id: str, target_id: str, role: str
) -> dict[str, Any]:
    if role not in (ROLE_OWNER, ROLE_MEMBER):
        raise ValidationError("Role must be 'owner' or 'member'.")
    room = _get_room(session, room_id)
    _require_owner(session, owner_id, room)
    member = session.get(RoomMember, (room.id, target_id))
    if not member:
        raise NotFoundError("That user is not a member.")
    if target_id == room.created_by and role != ROLE_OWNER:
        raise ValidationError("Cannot demote the room owner.")
    member.role = role
    session.add(member)
    session.commit()
    return to_member_dto(session, member)


def list_members(session: Session, user_id: str, room_id: str) -> list[dict[str, Any]]:
    room = _get_room(session, room_id)
    _require_member(session, user_id, room)
    rows = session.scalars(
        select(RoomMember)
        .where(RoomMember.room_id == room.id)
        .order_by(RoomMember.joined_at)
    ).all()
    return [to_member_dto(session, m) for m in rows]


# ------------------------------------------------------------------ messages


def list_messages(
    session: Session,
    user_id: str,
    room_id: str,
    *,
    before_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    room = _get_room(session, room_id)
    _require_member(session, user_id, room)
    limit = max(1, min(limit, 200))
    query = select(RoomMessage).where(RoomMessage.room_id == room.id)
    if before_id:
        before = session.get(RoomMessage, before_id)
        if before:
            query = query.where(RoomMessage.created_at < before.created_at)
    rows = session.scalars(
        query.order_by(RoomMessage.created_at.desc()).limit(limit)
    ).all()
    # newest-first for pagination; reverse for display (oldest → newest)
    return [to_message_dto(session, m) for m in reversed(rows)]


def create_message(session: Session, user_id: str, room_id: str, content: str) -> RoomMessage:
    content = (content or "").strip()
    if not content:
        raise ValidationError("Message cannot be empty.")
    if len(content) > 8000:
        raise ValidationError("Message is too long.")
    room = _get_room(session, room_id)
    _require_member(session, user_id, room)
    message = RoomMessage(room_id=room.id, user_id=user_id, content=content)
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def delete_message(session: Session, user_id: str, room_id: str, message_id: str) -> None:
    room = _get_room(session, room_id)
    message = session.get(RoomMessage, message_id)
    if not message or message.room_id != room.id:
        raise NotFoundError("Message not found.")
    if message.user_id != user_id:
        _require_owner(session, user_id, room)
    session.delete(message)
    session.commit()
