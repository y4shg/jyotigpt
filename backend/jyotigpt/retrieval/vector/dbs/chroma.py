"""Chroma vector-store client (default backend).

Talks to a local persistent Chroma at ``CHROMA_DATA_PATH``, or to a
standalone Chroma server when ``CHROMA_HTTP_HOST`` is set. Distances come
back from Chroma as cosine *distance* (2 = worst, 0 = best); they are
flipped into a [0, 1] similarity score where 1 = most similar.
"""

import logging
from typing import List, Optional

import chromadb
from chromadb import Settings
from chromadb.utils.batch_utils import create_batches

from jyotigpt.config import (
    CHROMA_CLIENT_AUTH_CREDENTIALS,
    CHROMA_CLIENT_AUTH_PROVIDER,
    CHROMA_DATABASE,
    CHROMA_DATA_PATH,
    CHROMA_HTTP_HEADERS,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_HTTP_SSL,
    CHROMA_TENANT,
)
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.vector.main import GetResult, SearchResult, VectorItem

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class ChromaClient:
    """CRUD/search client for a Chroma store."""

    def __init__(self):
        settings = {"allow_reset": True, "anonymized_telemetry": False}
        if CHROMA_CLIENT_AUTH_PROVIDER is not None:
            settings["chroma_client_auth_provider"] = CHROMA_CLIENT_AUTH_PROVIDER
        if CHROMA_CLIENT_AUTH_CREDENTIALS is not None:
            settings["chroma_client_auth_credentials"] = (
                CHROMA_CLIENT_AUTH_CREDENTIALS
            )

        if CHROMA_HTTP_HOST != "":
            self.client = chromadb.HttpClient(
                host=CHROMA_HTTP_HOST,
                port=CHROMA_HTTP_PORT,
                headers=CHROMA_HTTP_HEADERS,
                ssl=CHROMA_HTTP_SSL,
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
                settings=Settings(**settings),
            )
        else:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DATA_PATH,
                settings=Settings(**settings),
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
            )

    def has_collection(self, collection_name: str) -> bool:
        """True if a collection with this name exists."""
        return collection_name in self.client.list_collections()

    def delete_collection(self, collection_name: str):
        return self.client.delete_collection(name=collection_name)

    def search(
        self, collection_name: str, vectors: List[List[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """Nearest-neighbor lookup: returns up to ``limit`` rows with scores."""
        try:
            collection = self.client.get_collection(name=collection_name)
            if not collection:
                return None

            result = collection.query(query_embeddings=vectors, n_results=limit)

            # Chroma reports cosine distance (2 = worst, 0 = best); convert
            # that to a similarity score in [0, 1] where 1 = most similar.
            distances = [(2 - dist) / 2 for dist in result["distances"][0]]

            return SearchResult(
                ids=result["ids"],
                distances=[distances],
                documents=result["documents"],
                metadatas=result["metadatas"],
            )
        except Exception:
            return None

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """Rows matching ``filter``, without distances."""
        try:
            collection = self.client.get_collection(name=collection_name)
            if not collection:
                return None

            result = collection.get(where=filter, limit=limit)

            return GetResult(
                ids=[result["ids"]],
                documents=[result["documents"]],
                metadatas=[result["metadatas"]],
            )
        except Exception:
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Everything in the collection."""
        collection = self.client.get_collection(name=collection_name)
        if not collection:
            return None

        result = collection.get()
        return GetResult(
            ids=[result["ids"]],
            documents=[result["documents"]],
            metadatas=[result["metadatas"]],
        )

    def _split_items(self, items: List[VectorItem]):
        return (
            [item["id"] for item in items],
            [item["text"] for item in items],
            [item["vector"] for item in items],
            [item["metadata"] for item in items],
        )

    def insert(self, collection_name: str, items: List[VectorItem]):
        """Insert rows, creating the collection if needed (cosine space)."""
        collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids, documents, embeddings, metadatas = self._split_items(items)
        for batch in create_batches(
            api=self.client,
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        ):
            collection.add(*batch)

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """Insert-or-update rows; creates the collection if needed."""
        collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        ids, documents, embeddings, metadatas = self._split_items(items)
        collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        """Delete rows by ``ids`` or by a ``filter``.

        ``metadata`` is an accepted alias for ``filter`` — some callers pass
        the selector under that name.
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            if not collection:
                return

            if ids:
                collection.delete(ids=ids)
            elif filter or metadata:
                collection.delete(where=filter or metadata)
        except Exception:
            # Missing collection means there is nothing to delete — fine.
            log.debug(
                f"Attempted to delete from non-existent collection {collection_name}. Ignoring."
            )

    def reset(self):
        """Wipe the whole store (all collections and rows)."""
        return self.client.reset()
