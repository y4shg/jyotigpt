"""File storage service.

Owns the file CRUD + content-serving logic behind the ``/api/v1/files``
router. Persistence goes through ``models.files.Files`` and object storage
through ``storage.provider.Storage``; access control is a mix of file
ownership and knowledge-base membership (files attached to a knowledge base
are readable/writable by its members).
"""

import logging
import os
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.files import (
    FileForm,
    FileModel,
    FileModelResponse,
    Files,
)
from jyotigpt.models.knowledge import Knowledges
from jyotigpt.routers.audio import transcribe
from jyotigpt.routers.retrieval import ProcessFileForm, process_file
from jyotigpt.storage.provider import Storage

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Content types that are rendered inline instead of force-downloaded.
_AUDIO_CONTENT_TYPES = (
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/x-m4a",
)

# Image types are stored but never passed through the RAG pipeline.
_IMAGE_CONTENT_TYPES = ("image/png", "image/jpeg", "image/gif")


def has_access_to_file(file_id, access_type: str, user) -> bool:
    """True if ``user`` reaches ``file_id`` through a knowledge base.

    Files uploaded directly (no knowledge base) stay private to their
    owner; only knowledge-base files can be shared via membership.
    """
    file = Files.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    has_access = False
    knowledge_base_id = file.meta.get("collection_name") if file.meta else None

    if knowledge_base_id:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
            user.id, access_type
        )
        for knowledge_base in knowledge_bases:
            if knowledge_base.id == knowledge_base_id:
                has_access = True
                break

    return has_access


def can_access(file, user, access_type: str) -> bool:
    """Ownership-or-membership gate shared by the read/write endpoints."""
    return file.user_id == user.id or user.role == "admin" or has_access_to_file(
        file.id, access_type, user
    )


def _process_uploaded_file(request, file_item, file: dict, process: bool, user):
    """Run the RAG pipeline over a freshly uploaded file.

    Audio files are transcribed first; images are skipped entirely;
    everything else is passed straight to ``process_file``. A failure here
    is reported on the returned item rather than failing the upload.
    """
    content_type = file.get("content_type")
    file_id = file_item.id

    if not process or content_type in _IMAGE_CONTENT_TYPES:
        return file_item

    try:
        if content_type in _AUDIO_CONTENT_TYPES:
            file_path = Storage.get_file(file_item.path)
            result = transcribe(request, file_path)
            process_file(
                request,
                ProcessFileForm(file_id=file_id, content=result.get("text", "")),
                user=user,
            )
        else:
            process_file(request, ProcessFileForm(file_id=file_id), user=user)

        file_item = Files.get_file_by_id(id=file_id)
    except Exception as e:
        log.exception(e)
        log.error(f"Error processing file: {file_id}")
        file_item = FileModelResponse(
            **{
                **file_item.model_dump(),
                "error": str(e.detail) if hasattr(e, "detail") else str(e),
            }
        )

    return file_item


def upload_file(request, file, user, file_metadata=None, process=True):
    """Persist ``file`` and (optionally) index it into the retrieval store.

    The stored name is ``{uuid}_{basename}`` so downloads can never escape
    the upload directory; the user-visible filename is kept in ``meta``.
    """
    file_metadata = file_metadata or {}
    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        id = str(uuid.uuid4())
        name = filename
        filename = f"{id}_{filename}"
        contents, file_path = Storage.upload_file(file.file, filename)

        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": id,
                    "filename": name,
                    "path": file_path,
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": len(contents),
                        "data": file_metadata,
                    },
                }
            ),
        )

        if file_item:
            file_item = _process_uploaded_file(
                request,
                file_item,
                {"content_type": file.content_type},
                process,
                user,
            )

        if file_item:
            return file_item
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def _file_response(file_path: Path, file: FileModel, attachment: bool) -> FileResponse:
    """Build a FileResponse with the RFC 5987-encoded filename.

    PDFs are always inlined; explicit ``attachment`` forces a download;
    anything else defaults to attachment unless it is plain text.
    """
    filename = file.meta.get("name", file.filename)
    encoded_filename = quote(filename)
    headers = {}

    if attachment:
        headers["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{encoded_filename}"
        )
    else:
        content_type = file.meta.get("content_type")
        if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            headers["Content-Disposition"] = (
                f"inline; filename*=UTF-8''{encoded_filename}"
            )
            content_type = "application/pdf"
        elif content_type != "text/plain":
            headers["Content-Disposition"] = (
                f"attachment; filename*=UTF-8''{encoded_filename}"
            )

    return FileResponse(file_path, headers=headers, media_type=content_type)


def serve_file_content(file: FileModel, attachment: bool) -> FileResponse:
    """Stream a stored file's bytes with the right disposition."""
    try:
        file_path = Path(Storage.get_file(file.path))

        if file_path.is_file():
            return _file_response(file_path, file, attachment)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    except Exception as e:
        log.exception(e)
        log.error("Error getting file content")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
        )


def serve_file_as_attachment(file: FileModel) -> FileResponse:
    """Serve a stored file for download (used by the ``/content/{name}`` path)."""
    file_path = file.path

    # Handle Unicode filenames
    filename = file.meta.get("name", file.filename)
    encoded_filename = quote(filename)  # RFC5987 encoding
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
    }

    if file_path:
        file_path = Path(Storage.get_file(file_path))

        if file_path.is_file():
            return FileResponse(file_path, headers=headers)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # No stored file: fall back to serving the extracted text as .txt
    file_content = file.content.get("content", "") if file.content else ""
    file_name = file.filename

    def generator():
        yield file_content.encode("utf-8")

    return StreamingResponse(
        generator(),
        media_type="text/plain",
        headers=headers,
    )
