"""Qdrant vector-store client.

Connects to a Qdrant server via ``QDRANT_URI`` (optionally preferring
gRPC). All collections live under the ``jyotigpt_`` prefix. Raw cosine
scores span [-1, 1]; they are normalized to [0, 1] with 1 = most similar.
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

from qdrant_client import QdrantClient as Qclient
from qdrant_client.http.models import PointStruct
from qdrant_client.models import models

from jyotigpt.config import (
    QDRANT_API_KEY,
    QDRANT_GRPC_PORT,
    QDRANT_ON_DISK,
    QDRANT_PREFER_GRPC,
    QDRANT_URI,
)
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.vector.main import GetResult, SearchResult, VectorItem

# Qdrant defaults to returning 10 results when no limit is given.
NO_LIMIT = 999999999

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class QdrantClient:
    """CRUD/search client for a Qdrant server."""

    def __init__(self):
        self.collection_prefix = "jyotigpt"
        self.QDRANT_URI = QDRANT_URI
        self.QDRANT_API_KEY = QDRANT_API_KEY
        self.QDRANT_ON_DISK = QDRANT_ON_DISK
        self.PREFER_GRPC = QDRANT_PREFER_GRPC
        self.GRPC_PORT = QDRANT_GRPC_PORT

        if not self.QDRANT_URI:
            self.client = None
            return

        # Accept either a full URL or a bare host, and honor the port from
        # the URL when gRPC is preferred.
        parsed = urlparse(self.QDRANT_URI)
        host = parsed.hostname or self.QDRANT_URI
        http_port = parsed.port or 6333  # default REST port

        if self.PREFER_GRPC:
            self.client = Qclient(
                host=host,
                port=http_port,
                grpc_port=self.GRPC_PORT,
                prefer_grpc=self.PREFER_GRPC,
                api_key=self.QDRANT_API_KEY,
            )
        else:
            self.client = Qclient(url=self.QDRANT_URI, api_key=self.QDRANT_API_KEY)

    # --- internal helpers -------------------------------------------------

    def _prefixed(self, collection_name: str) -> str:
        return f"{self.collection_prefix}_{collection_name}"

    def _points_to_get_result(self, points) -> GetResult:
        ids = []
        documents = []
        metadatas = []

        for point in points:
            payload = point.payload
            ids.append(point.id)
            documents.append(payload["text"])
            metadatas.append(payload["metadata"])

        return GetResult(
            ids=[ids],
            documents=[documents],
            metadatas=[metadatas],
        )

    def _create_collection(self, collection_name: str, dimension: int):
        collection_name_with_prefix = self._prefixed(collection_name)
        self.client.create_collection(
            collection_name=collection_name_with_prefix,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
                on_disk=self.QDRANT_ON_DISK,
            ),
        )

        log.info(f"collection {collection_name_with_prefix} successfully created!")

    def _create_collection_if_not_exists(self, collection_name, dimension):
        if not self.has_collection(collection_name=collection_name):
            self._create_collection(
                collection_name=collection_name, dimension=dimension
            )

    def _create_points(self, items: List[VectorItem]):
        return [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item in items
        ]

    # --- public API -------------------------------------------------------

    def has_collection(self, collection_name: str) -> bool:
        return self.client.collection_exists(self._prefixed(collection_name))

    def delete_collection(self, collection_name: str):
        return self.client.delete_collection(
            collection_name=self._prefixed(collection_name)
        )

    def search(
        self, collection_name: str, vectors: List[List[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """Nearest-neighbor lookup; returns up to ``limit`` rows with scores."""
        if limit is None:
            limit = NO_LIMIT  # otherwise qdrant would default to 10!

        query_response = self.client.query_points(
            collection_name=self._prefixed(collection_name),
            query=vectors[0],
            limit=limit,
        )
        get_result = self._points_to_get_result(query_response.points)
        return SearchResult(
            ids=get_result.ids,
            documents=get_result.documents,
            metadatas=get_result.metadatas,
            # qdrant scores cosine similarity in [-1, 1]; normalize to [0, 1].
            distances=[[(point.score + 1.0) / 2.0 for point in query_response.points]],
        )

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        """Rows whose metadata matches every key in ``filter``."""
        if not self.has_collection(collection_name):
            return None

        try:
            if limit is None:
                limit = NO_LIMIT  # otherwise qdrant would default to 10!

            field_conditions = [
                models.FieldCondition(
                    key=f"metadata.{key}", match=models.MatchValue(value=value)
                )
                for key, value in filter.items()
            ]

            points = self.client.query_points(
                collection_name=self._prefixed(collection_name),
                query_filter=models.Filter(should=field_conditions),
                limit=limit,
            )
            return self._points_to_get_result(points.points)
        except Exception as e:
            log.exception(f"Error querying a collection '{collection_name}': {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Everything in the collection."""
        points = self.client.query_points(
            collection_name=self._prefixed(collection_name),
            limit=NO_LIMIT,  # otherwise qdrant would default to 10!
        )
        return self._points_to_get_result(points.points)

    def insert(self, collection_name: str, items: List[VectorItem]):
        """Insert rows, creating the collection if needed."""
        self._create_collection_if_not_exists(collection_name, len(items[0]["vector"]))
        points = self._create_points(items)
        self.client.upload_points(self._prefixed(collection_name), points)

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """Insert-or-update rows; creates the collection if needed."""
        self._create_collection_if_not_exists(collection_name, len(items[0]["vector"]))
        points = self._create_points(items)
        return self.client.upsert(self._prefixed(collection_name), points)

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        """Delete rows by ``ids`` or by a metadata ``filter``.

        ``metadata`` is an accepted alias for ``filter`` — some callers pass
        the selector under that name. Rows are located by payload fields.
        """
        effective_filter = filter or metadata
        field_conditions = []

        if ids:
            field_conditions = [
                models.FieldCondition(
                    key="metadata.id",
                    match=models.MatchValue(value=id_value),
                )
                for id_value in ids
            ]
        elif effective_filter:
            field_conditions = [
                models.FieldCondition(
                    key=f"metadata.{key}",
                    match=models.MatchValue(value=value),
                )
                for key, value in effective_filter.items()
            ]

        return self.client.delete(
            collection_name=self._prefixed(collection_name),
            points_selector=models.FilterSelector(
                filter=models.Filter(must=field_conditions)
            ),
        )

    def reset(self):
        """Drop every collection under the ``jyotigpt_`` prefix."""
        collection_names = self.client.get_collections().collections
        for collection_name in collection_names:
            if collection_name.name.startswith(self.collection_prefix):
                self.client.delete_collection(collection_name=collection_name.name)
