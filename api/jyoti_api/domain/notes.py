"""Notes: simple per-user markdown notes (used by the playground's Notes tab)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Note


def to_note_dto(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


def list_notes(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Note).where(Note.user_id == user_id).order_by(Note.updated_at.desc())
    ).all()
    return [to_note_dto(n) for n in rows]


def create_note(session: Session, user_id: str, title: str, content: str) -> Note:
    note = Note(
        user_id=user_id,
        title=(title or "Untitled")[:200],
        content=(content or "")[:20000],
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def _owned(session: Session, user_id: str, note_id: str) -> Note:
    note = session.get(Note, note_id)
    if not note or note.user_id != user_id:
        raise NotFoundError("Note not found.")
    return note


def get_note(session: Session, user_id: str, note_id: str) -> dict[str, Any]:
    return to_note_dto(_owned(session, user_id, note_id))


def update_note(
    session: Session, user_id: str, note_id: str, title: str | None, content: str | None
) -> Note:
    note = _owned(session, user_id, note_id)
    if title is not None:
        note.title = (title or "Untitled")[:200]
    if content is not None:
        note.content = (content or "")[:20000]
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def delete_note(session: Session, user_id: str, note_id: str) -> None:
    note = _owned(session, user_id, note_id)
    session.delete(note)
    session.commit()
