"""Knowledge-base service.

Knowledge bases group uploaded files for retrieval. This module owns the
non-HTTP logic behind the ``/api/v1/knowledge`` router: access gating,
file-list resolution (pruning references to deleted files), vector-store
cleanup, and the cross-domain model detachment that happens when a
knowledge base is deleted.
"""

import logging
from typing import Optional

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.files import FileMetadataResponse, Files
from jyotigpt.models.knowledge import KnowledgeUserResponse, Knowledges
from jyotigpt.models.models import ModelForm, Models
from jyotigpt.retrieval.vector.connector import VECTOR_DB_CLIENT
from jyotigpt.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


def can_access(knowledge, user, access_type: str) -> bool:
    """Ownership-or-membership gate shared by the read/write endpoints."""
    return (
        knowledge.user_id == user.id
        or user.role == "admin"
        or has_access(user.id, access_type, knowledge.access_control)
    )


def resolve_files(knowledge) -> tuple[list[str], list[FileMetadataResponse]]:
    """Resolve a knowledge base's stored file ids to their metadata.

    Ids whose file rows no longer exist are pruned from ``data`` so a
    knowledge base never points at ghost files.
    """
    file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
    files = Files.get_file_metadatas_by_ids(file_ids)

    if len(files) != len(file_ids):
        missing = set(file_ids) - {file.id for file in files}
        if missing:
            pruned = [file_id for file_id in file_ids if file_id not in missing]
            data = knowledge.data or {}
            data["file_ids"] = pruned
            Knowledges.update_knowledge_data_by_id(id=knowledge.id, data=data)
            files = Files.get_file_metadatas_by_ids(pruned)

    return file_ids, files


def list_knowledge_bases(user, permission: str) -> list[KnowledgeUserResponse]:
    """Every knowledge base reachable by ``user``, decorated with files.

    Admins see all bases; everyone else sees bases they own or that grant
    ``permission`` through their access-control rules.
    """
    if user.role == "admin":
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
            user.id, permission
        )

    return [
        KnowledgeUserResponse(
            **knowledge_base.model_dump(), files=resolve_files(knowledge_base)[1]
        )
        for knowledge_base in knowledge_bases
    ]


def drop_collection(collection_name: str) -> None:
    """Delete a vector collection, tolerating one that never existed."""
    try:
        VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
    except Exception as e:
        log.debug(e)


def remove_vector_content(collection_name: str, file_id: str) -> None:
    """Delete a file's vectors from a collection, tolerating a missing one."""
    try:
        VECTOR_DB_CLIENT.delete(
            collection_name=collection_name, filter={"file_id": file_id}
        )
    except Exception as e:
        log.debug("This was most likely caused by bypassing embedding processing")
        log.debug(e)


def delete_file_collection_and_row(file_id: str) -> None:
    """Remove a file's dedicated vector collection and its database row."""
    try:
        file_collection = f"file-{file_id}"
        if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection):
            VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)
    except Exception as e:
        log.debug("This was most likely caused by bypassing embedding processing")
        log.debug(e)

    Files.delete_file_by_id(file_id)


def detach_from_models(knowledge_id: str) -> None:
    """Strip a deleted knowledge base from every model that references it."""
    models = Models.get_all_models()
    for model in models:
        if not (model.meta and hasattr(model.meta, "knowledge")):
            continue

        knowledge_list = model.meta.knowledge or []
        updated = [k for k in knowledge_list if k.get("id") != knowledge_id]

        if len(updated) != len(knowledge_list):
            log.info(
                f"Updating model {model.id} to remove knowledge base {knowledge_id}"
            )
            model.meta.knowledge = updated
            Models.update_model_by_id(
                model.id,
                ModelForm(
                    id=model.id,
                    name=model.name,
                    base_model_id=model.base_model_id,
                    meta=model.meta,
                    params=model.params,
                    access_control=model.access_control,
                    is_active=model.is_active,
                ),
            )
