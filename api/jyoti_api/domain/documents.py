"""Documents: upload storage + text extraction.

Uploads live under ``DATA_DIR/uploads/<user_id>/`` keyed by a random id with
the original filename appended; the ``documents`` table stores metadata and
the extracted text. Large files are stored without parsing.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.config import Settings
from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Document
from jyoti_api.retrieval import chunker

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-]+")


def _safe_filename(filename: str) -> str:
    name = _SAFE_NAME.sub("_", filename or "upload").strip("._")
    return name[:160] or "upload"


def to_document_dto(document: Document) -> dict[str, Any]:
    return {
        "id": document.id,
        "user_id": document.user_id,
        "filename": document.filename,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "checksum": document.checksum,
        "extracted_text": document.extracted_text,
        "meta": document.meta or {},
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


def store_upload(
    session: Session,
    settings: Settings,
    *,
    user_id: str,
    filename: str,
    content: bytes,
    content_type: str = "",
) -> Document:
    if not content:
        raise ValidationError("Uploaded file is empty.")
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(
            f"File exceeds the {settings.max_upload_size_mb} MB upload limit."
        )
    safe_name = _safe_filename(filename)
    storage_key = f"uploads/{user_id}/{uuid.uuid4().hex}-{safe_name}"
    path = settings.data_dir / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    extracted = ""
    if len(content) <= settings.content_extraction_max_mb * 1024 * 1024:
        extracted = chunker.extract_text(path, content_type)

    document = Document(
        user_id=user_id,
        filename=safe_name,
        storage_key=storage_key,
        content_type=content_type or "",
        size_bytes=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        extracted_text=extracted,
        meta={},
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def store_text(
    session: Session,
    settings: Settings,
    *,
    user_id: str,
    text: str,
    filename: str = "note.txt",
) -> Document:
    return store_upload(
        session,
        settings,
        user_id=user_id,
        filename=filename,
        content=(text or "").encode("utf-8"),
        content_type="text/plain",
    )


def list_documents(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    ).all()
    return [to_document_dto(d) for d in rows]


def _owned(session: Session, user_id: str, document_id: str) -> Document:
    document = session.get(Document, document_id)
    if not document or document.user_id != user_id:
        raise NotFoundError("Document not found.")
    return document


def get_document(session: Session, user_id: str, document_id: str) -> Document:
    return _owned(session, user_id, document_id)


def delete_document(session: Session, settings: Settings, user_id: str, document_id: str) -> None:
    document = _owned(session, user_id, document_id)
    path = settings.data_dir / document.storage_key
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    session.delete(document)
    session.commit()


def resolve_path(settings: Settings, document: Document) -> Path:
    return settings.data_dir / document.storage_key
