"""Conversations and their messages: persistence + serialization.

Conversations are owned by a user; messages are stored as an ordered linear
list (``seq``), which is the shape the chat UI renders. Branching regenerations
are expressed later by deleting/inserting messages rather than a tree.

Timestamps are stored as UTC datetimes and serialized as ISO-8601 strings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError
from jyoti_api.persistence.schema import Conversation, ConversationMessage, Folder

DEFAULT_TITLE = "New Chat"
_MSGS_PER_PAGE = 50
_CHATS_PER_PAGE = 50


def _bucket(ts: datetime, now: datetime) -> str:
    """Bucket a conversation into the same groups the UI renders as headings."""
    local = ts.astimezone()
    start_today = local.replace(hour=0, minute=0, second=0, microsecond=0)
    days = (start_today - now.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)).days
    if days == 0:
        return "Today"
    if days == -1:
        return "Yesterday"
    if days > -7:
        return "Previous 7 days"
    if days > -30:
        return "Previous 30 days"
    return local.strftime("%B")


def to_message_dto(message: ConversationMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "model": message.model,
        "provider": message.provider,
        "error": message.error or None,
        "done": message.meta.get("done", True) if isinstance(message.meta, dict) else True,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None,
    }


def to_conversation_dto(
    session: Session, conversation: Conversation, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    count = session.scalar(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.conversation_id == conversation.id
        )
    )
    return {
        "id": conversation.id,
        "title": conversation.title,
        "folder_id": conversation.folder_id,
        "archived": conversation.archived,
        "pinned": conversation.pinned,
        "share_id": conversation.share_id,
        "time_range": _bucket(conversation.updated_at or conversation.created_at, now),
        "message_count": count or 0,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }


def _owned(session: Session, user_id: str, conversation_id: str) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise NotFoundError("Conversation not found.")
    return conversation


# ------------------------------------------------------------------ queries


def list_conversations(
    session: Session,
    user_id: str,
    search: str = "",
    page: int = 1,
    page_size: int = _CHATS_PER_PAGE,
) -> list[dict[str, Any]]:
    """Return the user's non-archived conversations, newest first, paginated."""
    query = select(Conversation).where(
        Conversation.user_id == user_id, Conversation.archived.is_(False)
    )
    if search.strip():
        query = query.where(Conversation.title.ilike(f"%{search.strip()}%"))
    query = query.order_by(Conversation.updated_at.desc())
    rows = session.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return [to_conversation_dto(session, c) for c in rows]


def list_archived(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.archived.is_(True))
        .order_by(Conversation.updated_at.desc())
    ).all()
    return [to_conversation_dto(session, c) for c in rows]


def create_conversation(
    session: Session, user_id: str, title: str = DEFAULT_TITLE, folder_id: str | None = None
) -> Conversation:
    if folder_id:
        folder = session.get(Folder, folder_id)
        if not folder or folder.user_id != user_id:
            raise NotFoundError("Folder not found.")
    conversation = Conversation(user_id=user_id, title=title.strip() or DEFAULT_TITLE, folder_id=folder_id)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def get_conversation(session: Session, user_id: str, conversation_id: str) -> Conversation:
    return _owned(session, user_id, conversation_id)


def update_conversation(
    session: Session,
    user_id: str,
    conversation_id: str,
    *,
    title: str | None = None,
    folder_id: str | None = None,
    archived: bool | None = None,
    pinned: bool | None = None,
) -> Conversation:
    conversation = _owned(session, user_id, conversation_id)
    if title is not None:
        conversation.title = title.strip() or DEFAULT_TITLE
    if folder_id is not None:
        if folder_id:
            folder = session.get(Folder, folder_id)
            if not folder or folder.user_id != user_id:
                raise NotFoundError("Folder not found.")
        conversation.folder_id = folder_id
    if archived is not None:
        conversation.archived = archived
    if pinned is not None:
        conversation.pinned = pinned
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def delete_conversation(session: Session, user_id: str, conversation_id: str) -> None:
    conversation = _owned(session, user_id, conversation_id)
    session.delete(conversation)
    session.commit()


# -------------------------------------------------------------------- share


def create_share(session: Session, user_id: str, conversation_id: str) -> Conversation:
    """Enable the public share link for a conversation; idempotent."""
    conversation = _owned(session, user_id, conversation_id)
    if not conversation.share_id:
        import secrets

        conversation.share_id = secrets.token_hex(8)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
    return conversation


def clear_share(session: Session, user_id: str, conversation_id: str) -> None:
    conversation = _owned(session, user_id, conversation_id)
    conversation.share_id = None
    session.add(conversation)
    session.commit()


def get_public_share(session: Session, share_id: str) -> dict[str, Any]:
    """Public, read-only snapshot of a shared conversation (no ownership)."""
    conversation = session.scalars(
        select(Conversation).where(Conversation.share_id == share_id)
    ).first()
    if not conversation:
        raise NotFoundError("Shared conversation not found.")
    rows = session.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.seq)
    ).all()
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in rows
            if m.content.strip() and m.role in ("user", "assistant")
        ],
    }


# ------------------------------------------------------------------ messages


def list_messages(session: Session, user_id: str, conversation_id: str) -> list[dict[str, Any]]:
    _owned(session, user_id, conversation_id)
    rows = session.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.seq)
    ).all()
    return [to_message_dto(m) for m in rows]


def add_message(
    session: Session,
    user_id: str,
    conversation_id: str,
    *,
    role: str,
    content: str,
    model: str = "",
    provider: str = "",
) -> ConversationMessage:
    """Append a message, auto-titling the conversation from the first user turn."""
    conversation = _owned(session, user_id, conversation_id)
    max_seq = session.scalar(
        select(func.max(ConversationMessage.seq)).where(
            ConversationMessage.conversation_id == conversation_id
        )
    )
    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=model,
        provider=provider,
        seq=(max_seq or 0) + 1,
        meta={"done": True},
    )
    session.add(message)
    if conversation.title == DEFAULT_TITLE and role == "user" and content.strip():
        conversation.title = _derive_title(content)
    session.add(conversation)
    session.commit()
    session.refresh(message)
    return message


def update_message(
    session: Session,
    user_id: str,
    message_id: str,
    *,
    content: str | None = None,
    done: bool | None = None,
    error: str | None = None,
) -> ConversationMessage:
    message = session.get(ConversationMessage, message_id)
    if not message:
        raise NotFoundError("Message not found.")
    conversation = session.get(Conversation, message.conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise NotFoundError("Message not found.")
    if content is not None:
        message.content = content
    if error is not None:
        message.error = error
    meta = dict(message.meta or {})
    if done is not None:
        meta["done"] = done
    message.meta = meta
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def delete_message(session: Session, user_id: str, message_id: str) -> None:
    message = session.get(ConversationMessage, message_id)
    if not message:
        raise NotFoundError("Message not found.")
    conversation = session.get(Conversation, message.conversation_id)
    if not conversation or conversation.user_id != user_id:
        raise NotFoundError("Message not found.")
    session.delete(message)
    session.commit()


# ---------------------------------------------------------------- bulk actions


def export_conversations(session: Session, user_id: str) -> list[dict[str, Any]]:
    """Full JSON export of the user's conversations, newest first."""
    rows = session.scalars(
        select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at)
    ).all()
    return [
        {
            "title": c.title,
            "folder_id": c.folder_id,
            "archived": c.archived,
            "pinned": c.pinned,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "model": m.model,
                    "provider": m.provider,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in session.scalars(
                    select(ConversationMessage)
                    .where(ConversationMessage.conversation_id == c.id)
                    .order_by(ConversationMessage.seq)
                ).all()
            ],
        }
        for c in rows
    ]


def import_conversations(session: Session, user_id: str, items: list[dict[str, Any]]) -> int:
    """Restore conversations from an export. Folder assignments are honored
    only when the folder belongs to this user; message order is preserved."""
    import json as _json

    count = 0
    owned_folders = set(
        session.scalars(select(Folder.id).where(Folder.user_id == user_id)).all()
    )
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            continue
        conversation = Conversation(
            user_id=user_id,
            title=item["title"].strip() or DEFAULT_TITLE,
            folder_id=item.get("folder_id") if item.get("folder_id") in owned_folders else None,
            archived=bool(item.get("archived")),
            pinned=bool(item.get("pinned")),
        )
        session.add(conversation)
        session.flush()  # assign an id before linking messages
        messages = item.get("messages")
        if isinstance(messages, list):
            seq = 0
            for message in messages:
                if not isinstance(message, dict):
                    continue
                role = message.get("role")
                if role not in ("user", "assistant", "system"):
                    continue
                seq += 1
                content = message.get("content") or ""
                created_at = _parse_iso(message.get("created_at"))
                session.add(
                    ConversationMessage(
                        conversation_id=conversation.id,
                        role=role,
                        content=content if isinstance(content, str) else "",
                        model=str(message.get("model") or ""),
                        provider=str(message.get("provider") or ""),
                        seq=seq,
                        meta={"done": True},
                        created_at=created_at,
                    )
                )
        count += 1
    session.commit()
    return count


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def archive_all_conversations(session: Session, user_id: str) -> int:
    result = session.execute(
        Conversation.__table__.update()
        .where(Conversation.user_id == user_id, Conversation.archived.is_(False))
        .values(archived=True)
    )
    session.commit()
    return int(result.rowcount or 0)


def delete_all_conversations(session: Session, user_id: str) -> int:
    rows = session.scalars(
        select(Conversation.id).where(Conversation.user_id == user_id)
    ).all()
    count = len(rows)
    if count:
        session.execute(
            Conversation.__table__.delete().where(Conversation.user_id == user_id)
        )
        session.commit()
    return count


def _derive_title(content: str) -> str:
    """First meaningful line, capped at 40 chars — mirrors the old auto-title."""
    text = content.strip().splitlines()[0] if content.strip() else ""
    if len(text) > 40:
        text = f"{text[:37].rstrip()}..."
    return text or DEFAULT_TITLE
