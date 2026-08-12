"""Folders: persistence + serialization.

Folders are a user-owned naming layer over conversations. ``parent_id`` is
kept for nesting compatibility with the old app's model; the current UI is
flat, so nesting is stored but not traversed.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Conversation, Folder


def to_folder_dto(session: Session, folder: Folder) -> dict[str, Any]:
    count = session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.user_id == folder.user_id,
            Conversation.folder_id == folder.id,
            Conversation.archived.is_(False),
        )
    )
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "conversation_count": count or 0,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
    }


def list_folders(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Folder).where(Folder.user_id == user_id).order_by(Folder.created_at)
    ).all()
    return [to_folder_dto(session, f) for f in rows]


def create_folder(session: Session, user_id: str, name: str, parent_id: str | None = None) -> Folder:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Folder name is required.")
    folder = Folder(user_id=user_id, name=name[:120], parent_id=parent_id)
    session.add(folder)
    session.commit()
    session.refresh(folder)
    return folder


def _owned(session: Session, user_id: str, folder_id: str) -> Folder:
    folder = session.get(Folder, folder_id)
    if not folder or folder.user_id != user_id:
        raise NotFoundError("Folder not found.")
    return folder


def rename_folder(session: Session, user_id: str, folder_id: str, name: str) -> Folder:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Folder name is required.")
    folder = _owned(session, user_id, folder_id)
    folder.name = name[:120]
    session.add(folder)
    session.commit()
    session.refresh(folder)
    return folder


def delete_folder(session: Session, user_id: str, folder_id: str) -> None:
    folder = _owned(session, user_id, folder_id)
    # un-file conversations rather than deleting them
    session.execute(
        Conversation.__table__.update()
        .where(
            Conversation.user_id == user_id,
            Conversation.folder_id == folder.id,
        )
        .values(folder_id=None)
    )
    session.delete(folder)
    session.commit()
