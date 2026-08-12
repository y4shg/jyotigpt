"""Notes endpoints: /api/v1/notes (per-user markdown notes)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import notes as domain

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])


class NoteBody(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=20000)


class NoteCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    content: str = Field(default="", max_length=20000)


@router.get("")
def list_notes(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return domain.list_notes(session, user.id)


@router.post("", status_code=201)
def create_note(body: NoteCreate, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    return domain.to_note_dto(domain.create_note(session, user.id, body.title, body.content))


@router.get("/{note_id}")
def get_note(note_id: str, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    return domain.get_note(session, user.id, note_id)


@router.patch("/{note_id}")
def update_note(
    note_id: str, body: NoteBody, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    return domain.to_note_dto(
        domain.update_note(session, user.id, note_id, body.title, body.content)
    )


@router.delete("/{note_id}")
def delete_note(note_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    domain.delete_note(session, user.id, note_id)
    return {"ok": True}
