"""HTTP surface for knowledge bases.

Knowledge bases group uploaded files for retrieval. Read endpoints are
open to any verified user; mutating endpoints require ownership or write
membership; ``/reindex`` is admin-only. File processing is delegated to
the retrieval domain.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.files import FileMetadataResponse, FileModel, Files
from jyotigpt.models.knowledge import (
    KnowledgeForm,
    KnowledgeResponse,
    KnowledgeUserResponse,
    Knowledges,
)
from jyotigpt.routers.retrieval import (
    BatchProcessFilesForm,
    ProcessFileForm,
    process_file,
    process_files_batch,
)
from jyotigpt.utils.access_control import has_permission
from jyotigpt.utils.auth import get_verified_user

from jyotigpt.domains.knowledge.service import (
    can_access,
    delete_file_collection_and_row,
    detach_from_models,
    drop_collection,
    list_knowledge_bases,
    remove_vector_content,
    resolve_files,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


class KnowledgeFilesResponse(KnowledgeResponse):
    files: list[FileMetadataResponse]


class KnowledgeFileIdForm(BaseModel):
    file_id: str


############################
# GetKnowledgeBases
############################


@router.get("/", response_model=list[KnowledgeUserResponse])
async def get_knowledge(user=Depends(get_verified_user)):
    return list_knowledge_bases(user, "read")


@router.get("/list", response_model=list[KnowledgeUserResponse])
async def get_knowledge_list(user=Depends(get_verified_user)):
    return list_knowledge_bases(user, "write")


############################
# CreateNewKnowledge
############################


@router.post("/create", response_model=Optional[KnowledgeResponse])
async def create_new_knowledge(
    request: Request, form_data: KnowledgeForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.knowledge", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge = Knowledges.insert_new_knowledge(user.id, form_data)

    if knowledge:
        return knowledge
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.FILE_EXISTS,
    )


############################
# ReindexKnowledgeFiles
############################


@router.post("/reindex", response_model=bool)
async def reindex_knowledge_files(request: Request, user=Depends(get_verified_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge_bases = Knowledges.get_knowledge_bases()

    log.info(f"Starting reindexing for {len(knowledge_bases)} knowledge bases")

    for knowledge_base in knowledge_bases:
        try:
            files = Files.get_files_by_ids(knowledge_base.data.get("file_ids", []))

            try:
                if VECTOR_DB_CLIENT.has_collection(collection_name=knowledge_base.id):
                    VECTOR_DB_CLIENT.delete_collection(
                        collection_name=knowledge_base.id
                    )
            except Exception as e:
                log.error(f"Error deleting collection {knowledge_base.id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error deleting vector DB collection",
                )

            failed_files = []
            for file in files:
                try:
                    process_file(
                        request,
                        ProcessFileForm(
                            file_id=file.id, collection_name=knowledge_base.id
                        ),
                        user=user,
                    )
                except Exception as e:
                    log.error(
                        f"Error processing file {file.filename} (ID: {file.id}): {str(e)}"
                    )
                    failed_files.append({"file_id": file.id, "error": str(e)})
                    continue

        except Exception as e:
            log.error(f"Error processing knowledge base {knowledge_base.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing knowledge base",
            )

        if failed_files:
            log.warning(
                f"Failed to process {len(failed_files)} files in knowledge base {knowledge_base.id}"
            )
            for failed in failed_files:
                log.warning(f"File ID: {failed['file_id']}, Error: {failed['error']}")

    log.info("Reindexing completed successfully")
    return True


############################
# GetKnowledgeById
############################


@router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role == "admin" or can_access(knowledge, user, "read"):
        _, files = resolve_files(knowledge)
        return KnowledgeFilesResponse(**knowledge.model_dump(), files=files)
    return None


############################
# UpdateKnowledgeById
############################


@router.post("/{id}/update", response_model=Optional[KnowledgeFilesResponse])
async def update_knowledge_by_id(
    id: str,
    form_data: KnowledgeForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge = Knowledges.update_knowledge_by_id(id=id, form_data=form_data)
    if knowledge:
        file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
        files = Files.get_files_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.ID_TAKEN,
    )


############################
# AddFileToKnowledge
############################


@router.post("/{id}/file/add", response_model=Optional[KnowledgeFilesResponse])
def add_file_to_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not file.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_PROCESSED,
        )

    # Add content to the vector database
    try:
        process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
        )
    except Exception as e:
        log.debug(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    data = knowledge.data or {}
    file_ids = data.get("file_ids", [])

    if form_data.file_id not in file_ids:
        file_ids.append(form_data.file_id)
        data["file_ids"] = file_ids

        knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

        if knowledge:
            files = Files.get_file_metadatas_by_ids(file_ids)

            return KnowledgeFilesResponse(
                **knowledge.model_dump(),
                files=files,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("knowledge"),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT("file_id"),
    )


############################
# UpdateFileFromKnowledge
############################


@router.post("/{id}/file/update", response_model=Optional[KnowledgeFilesResponse])
def update_file_from_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database, then re-add it
    remove_vector_content(knowledge.id, form_data.file_id)

    try:
        process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    data = knowledge.data or {}
    file_ids = data.get("file_ids", [])

    files = Files.get_file_metadatas_by_ids(file_ids)

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=files,
    )


############################
# RemoveFileFromKnowledge
############################


@router.post("/{id}/file/remove", response_model=Optional[KnowledgeFilesResponse])
def remove_file_from_knowledge_by_id(
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database, then the file itself
    remove_vector_content(knowledge.id, form_data.file_id)
    delete_file_collection_and_row(form_data.file_id)

    data = knowledge.data or {}
    file_ids = data.get("file_ids", [])

    if form_data.file_id in file_ids:
        file_ids.remove(form_data.file_id)
        data["file_ids"] = file_ids

        knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

        if knowledge:
            files = Files.get_file_metadatas_by_ids(file_ids)

            return KnowledgeFilesResponse(
                **knowledge.model_dump(),
                files=files,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("knowledge"),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT("file_id"),
    )


############################
# DeleteKnowledgeById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    log.info(f"Deleting knowledge base: {id} (name: {knowledge.name})")

    # Update models that reference this knowledge base
    detach_from_models(id)

    # Clean up the vector DB
    drop_collection(id)
    return Knowledges.delete_knowledge_by_id(id=id)


############################
# ResetKnowledgeById
############################


@router.post("/{id}/reset", response_model=Optional[KnowledgeResponse])
async def reset_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    drop_collection(id)

    return Knowledges.update_knowledge_data_by_id(id=id, data={"file_ids": []})


############################
# AddFilesToKnowledge
############################


@router.post("/{id}/files/batch/add", response_model=Optional[KnowledgeFilesResponse])
def add_files_to_knowledge_batch(
    request: Request,
    id: str,
    form_data: list[KnowledgeFileIdForm],
    user=Depends(get_verified_user),
):
    """
    Add multiple files to a knowledge base
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not can_access(knowledge, user, "write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get files content
    log.info(f"files/batch/add - {len(form_data)} files")
    files: list[FileModel] = []
    for form in form_data:
        file = Files.get_file_by_id(form.file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {form.file_id} not found",
            )
        files.append(file)

    # Process files
    try:
        result = process_files_batch(
            request=request,
            form_data=BatchProcessFilesForm(files=files, collection_name=id),
            user=user,
        )
    except Exception as e:
        log.error(
            f"add_files_to_knowledge_batch: Exception occurred: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Add successful files to the knowledge base
    data = knowledge.data or {}
    existing_file_ids = data.get("file_ids", [])

    # Only add files that were successfully processed
    successful_file_ids = [r.file_id for r in result.results if r.status == "completed"]
    for file_id in successful_file_ids:
        if file_id not in existing_file_ids:
            existing_file_ids.append(file_id)

    data["file_ids"] = existing_file_ids
    knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

    # If there were any errors, include them in the response
    if result.errors:
        error_details = [f"{err.file_id}: {err.error}" for err in result.errors]
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=Files.get_file_metadatas_by_ids(existing_file_ids),
            warnings={
                "message": "Some files failed to process",
                "errors": error_details,
            },
        )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=Files.get_file_metadatas_by_ids(existing_file_ids),
    )
