"""Memory domain service.

Memories are persisted to the database and mirrored into a per-user vector
collection so they can be retrieved semantically. The embedding function is
injected by the caller (it lives on the app state at the HTTP layer).
"""

import logging
from typing import Callable, Optional

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.memories import Memories, MemoryModel
from jyotigpt.retrieval.vector.connector import VECTOR_DB_CLIENT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


def _collection(user_id: str) -> str:
    return f"user-memory-{user_id}"


class MemoriesService:
    def add(self, user_id: str, content: str, embed: Callable) -> MemoryModel:
        memory = Memories.insert_new_memory(user_id, content)

        VECTOR_DB_CLIENT.upsert(
            collection_name=_collection(user_id),
            items=[
                {
                    "id": memory.id,
                    "text": memory.content,
                    "vector": embed(memory.content),
                    "metadata": {"created_at": memory.created_at},
                }
            ],
        )

        return memory

    def get_by_user(self, user_id: str) -> list[MemoryModel]:
        return Memories.get_memories_by_user_id(user_id)

    def query(
        self, user_id: str, content: str, k: Optional[int], embed: Callable
    ) -> list[dict]:
        return VECTOR_DB_CLIENT.search(
            collection_name=_collection(user_id),
            vectors=[embed(content)],
            limit=k,
        )

    def reset(self, user_id: str, embed: Callable) -> bool:
        """Rebuild the user's memory collection from the stored memories."""
        VECTOR_DB_CLIENT.delete_collection(_collection(user_id))

        memories = Memories.get_memories_by_user_id(user_id)
        VECTOR_DB_CLIENT.upsert(
            collection_name=_collection(user_id),
            items=[
                {
                    "id": memory.id,
                    "text": memory.content,
                    "vector": embed(memory.content),
                    "metadata": {
                        "created_at": memory.created_at,
                        "updated_at": memory.updated_at,
                    },
                }
                for memory in memories
            ],
        )

        return True

    def delete_by_user(self, user_id: str) -> bool:
        result = Memories.delete_memories_by_user_id(user_id)

        if result:
            try:
                VECTOR_DB_CLIENT.delete_collection(_collection(user_id))
            except Exception as e:
                log.error(e)
            return True

        return False

    def update(
        self,
        memory_id: str,
        content: Optional[str],
        user_id: str,
        embed: Callable,
    ) -> Optional[MemoryModel]:
        memory = Memories.update_memory_by_id_and_user_id(memory_id, content, user_id)

        # A new embedding is only re-pushed when fresh content is supplied;
        # a null content just clears the stored row.
        if content is not None and memory is not None:
            VECTOR_DB_CLIENT.upsert(
                collection_name=_collection(user_id),
                items=[
                    {
                        "id": memory.id,
                        "text": memory.content,
                        "vector": embed(memory.content),
                        "metadata": {
                            "created_at": memory.created_at,
                            "updated_at": memory.updated_at,
                        },
                    }
                ],
            )

        return memory

    def delete(self, memory_id: str, user_id: str) -> bool:
        result = Memories.delete_memory_by_id_and_user_id(memory_id, user_id)

        if result:
            VECTOR_DB_CLIENT.delete(
                collection_name=_collection(user_id), ids=[memory_id]
            )
            return True

        return False


memories = MemoriesService()
