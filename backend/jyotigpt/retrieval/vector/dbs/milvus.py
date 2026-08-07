"""Milvus vector-store client.

Connects via ``MILVUS_URI`` (optionally authenticated with
``MILVUS_TOKEN``). Collections are prefixed ``jyotigpt_`` and dash
characters are not allowed in Milvus names, so ``-`` is replaced with
``_``. Raw cosine scores span [-1, 1]; they are normalized to [0, 1].
"""

import json
import logging
from typing import List, Optional

from pymilvus import DataType, FieldSchema, MilvusClient as Client

from jyotigpt.config import MILVUS_DB, MILVUS_TOKEN, MILVUS_URI
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.vector.main import GetResult, SearchResult, VectorItem

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class MilvusClient:
    """CRUD/search client for a Milvus server."""

    def __init__(self):
        self.collection_prefix = "jyotigpt"
        if MILVUS_TOKEN is None:
            self.client = Client(uri=MILVUS_URI, db_name=MILVUS_DB)
        else:
            self.client = Client(uri=MILVUS_URI, db_name=MILVUS_DB, token=MILVUS_TOKEN)

    # --- internal helpers -------------------------------------------------

    def _safe_name(self, collection_name: str) -> str:
        """Milvus collection names cannot contain dashes."""
        return collection_name.replace("-", "_")

    def _to_get_result(self, result) -> GetResult:
        ids = []
        documents = []
        metadatas = []

        for match in result:
            _ids = []
            _documents = []
            _metadatas = []
            for item in match:
                _ids.append(item.get("id"))
                _documents.append(item.get("data", {}).get("text"))
                _metadatas.append(item.get("metadata"))

            ids.append(_ids)
            documents.append(_documents)
            metadatas.append(_metadatas)

        return GetResult(ids=ids, documents=documents, metadatas=metadatas)

    def _to_search_result(self, result) -> SearchResult:
        ids = []
        distances = []
        documents = []
        metadatas = []

        for match in result:
            _ids = []
            _distances = []
            _documents = []
            _metadatas = []

            for item in match:
                _ids.append(item.get("id"))
                # Milvus cosine similarity spans [-1, 1]; normalize to [0, 1].
                _distances.append((item.get("distance") + 1.0) / 2.0)
                _documents.append(item.get("entity", {}).get("data", {}).get("text"))
                _metadatas.append(item.get("entity", {}).get("metadata"))

            ids.append(_ids)
            distances.append(_distances)
            documents.append(_documents)
            metadatas.append(_metadatas)

        return SearchResult(
            ids=ids,
            distances=distances,
            documents=documents,
            metadatas=metadatas,
        )

    def _create_collection(self, collection_name: str, dimension: int):
        schema = self.client.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )
        schema.add_field(
            field_name="id",
            datatype=DataType.VARCHAR,
            is_primary=True,
            max_length=65535,
        )
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=dimension,
            description="vector",
        )
        schema.add_field(field_name="data", datatype=DataType.JSON, description="data")
        schema.add_field(
            field_name="metadata", datatype=DataType.JSON, description="metadata"
        )

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 100},
        )

        self.client.create_collection(
            collection_name=f"{self.collection_prefix}_{self._safe_name(collection_name)}",
            schema=schema,
            index_params=index_params,
        )

    def _as_filter_string(self, filter: dict) -> str:
        """Build the Milvus boolean expression for a metadata match."""
        return " && ".join(
            f'metadata["{key}"] == {json.dumps(value)}'
            for key, value in filter.items()
        )

    # --- public API -------------------------------------------------------

    def has_collection(self, collection_name: str) -> bool:
        return self.client.has_collection(
            collection_name=f"{self.collection_prefix}_{self._safe_name(collection_name)}"
        )

    def delete_collection(self, collection_name: str):
        return self.client.drop_collection(
            collection_name=f"{self.collection_prefix}_{self._safe_name(collection_name)}"
        )

    def search(
        self, collection_name: str, vectors: List[List[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """Nearest-neighbor lookup; returns up to ``limit`` rows with scores."""
        result = self.client.search(
            collection_name=f"{self.collection_prefix}_{self._safe_name(collection_name)}",
            data=vectors,
            limit=limit,
            output_fields=["data", "metadata"],
        )

        return self._to_search_result(result)

    def query(self, collection_name: str, filter: dict, limit: Optional[int] = None):
        """Rows whose metadata matches every key in ``filter`` (paginated)."""
        if not self.has_collection(collection_name):
            return None

        filter_string = self._as_filter_string(filter)

        max_limit = 16383  # per-request cap imposed by Milvus
        all_results = []
        remaining = limit if limit is not None else float("inf")

        try:
            offset = 0
            while remaining > 0:
                current_fetch = min(max_limit, remaining)

                results = self.client.query(
                    collection_name=f"{self.collection_prefix}_{self._safe_name(collection_name)}",
                    filter=filter_string,
                    output_fields=["*"],
                    limit=current_fetch,
                    offset=offset,
                )

                if not results:
                    break

                all_results.extend(results)
                remaining -= len(results)
                offset += len(results)

                # A short page means we have reached the end of the data.
                if len(results) < current_fetch:
                    break

            log.debug(all_results)
            return self._to_get_result([all_results])
        except Exception as e:
            log.exception(
                f"Error querying collection {collection_name} with limit {limit}: {e}"
            )
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Everything in the collection."""
        result = self.client.query(
            collection_name=f"{self.collection_prefix}_{self._safe_name(collection_name)}",
            filter='id != ""',
        )
        return self._to_get_result([result])

    def _collection_or_create(self, collection_name: str, items: List[VectorItem]):
        """Return the (prefixed, dashed) name, creating the collection first."""
        safe_name = self._safe_name(collection_name)
        prefixed = f"{self.collection_prefix}_{safe_name}"
        if not self.client.has_collection(collection_name=prefixed):
            self._create_collection(
                collection_name=safe_name, dimension=len(items[0]["vector"])
            )
        return prefixed

    def insert(self, collection_name: str, items: List[VectorItem]):
        """Insert rows, creating the collection if needed."""
        prefixed = self._collection_or_create(collection_name, items)

        return self.client.insert(
            collection_name=prefixed,
            data=[
                {
                    "id": item["id"],
                    "vector": item["vector"],
                    "data": {"text": item["text"]},
                    "metadata": item["metadata"],
                }
                for item in items
            ],
        )

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """Insert-or-update rows; creates the collection if needed."""
        prefixed = self._collection_or_create(collection_name, items)

        return self.client.upsert(
            collection_name=prefixed,
            data=[
                {
                    "id": item["id"],
                    "vector": item["vector"],
                    "data": {"text": item["text"]},
                    "metadata": item["metadata"],
                }
                for item in items
            ],
        )

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        """Delete rows by ``ids`` or by a metadata ``filter``.

        ``metadata`` is an accepted alias for ``filter`` — some callers pass
        the selector under that name.
        """
        prefixed = f"{self.collection_prefix}_{self._safe_name(collection_name)}"

        if ids:
            return self.client.delete(collection_name=prefixed, ids=ids)
        elif filter or metadata:
            return self.client.delete(
                collection_name=prefixed,
                filter=self._as_filter_string(filter or metadata),
            )

    def reset(self):
        """Drop every collection under the ``jyotigpt_`` prefix."""
        collection_names = self.client.list_collections()
        for collection_name in collection_names:
            if collection_name.startswith(self.collection_prefix):
                self.client.drop_collection(collection_name=collection_name)
