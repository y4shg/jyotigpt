"""Document endpoints: /api/v1/documents/* and the ingest entry point.

``/api/v1/ingest`` is the migration target for the old ``jyotigpt.routers.files``
pipeline import: upload a file (optionally straight into a collection) and
get back the stored document with its extracted text.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.domain import collections, documents
from jyoti_api.errors import ApiError

router = APIRouter(prefix="/api/v1", tags=["documents"])


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read()
    if not data:
        raise ApiError("Uploaded file is empty.")
    return data


@router.get("/documents")
def list_documents(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return documents.list_documents(session, user.id)


@router.post("/documents", status_code=201)
async def upload_document(
    user: CurrentUser, session: SessionDep, file: UploadFile = File(...)
) -> dict[str, Any]:
    settings = get_settings()
    content = await _read_upload(file)
    document = documents.store_upload(
        session,
        settings,
        user_id=user.id,
        filename=file.filename or "upload",
        content=content,
        content_type=file.content_type or "",
    )
    return documents.to_document_dto(document)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    settings = get_settings()
    documents.delete_document(session, settings, user.id, document_id)
    return {"ok": True}


class IngestRequest(BaseModel):
    collection_id: str | None = None


@router.post("/ingest", status_code=201)
async def ingest_document(
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
    collection_id: str | None = None,
) -> dict[str, Any]:
    """Upload a file and optionally embed it into a collection (pipeline path)."""
    settings = get_settings()
    content = await _read_upload(file)
    document = documents.store_upload(
        session,
        settings,
        user_id=user.id,
        filename=file.filename or "upload",
        content=content,
        content_type=file.content_type or "",
    )
    result: dict[str, Any] = documents.to_document_dto(document)
    if collection_id:
        try:
            items = await collections.add_document_item(
                session,
                settings,
                user_id=user.id,
                collection_id=collection_id,
                document_id=document.id,
            )
            result["items_created"] = len(items)
        except ApiError as exc:
            result["collection_error"] = exc.detail
    return result
