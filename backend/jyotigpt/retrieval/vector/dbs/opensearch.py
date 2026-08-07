"""OpenSearch vector-store client.

Connects to OpenSearch with the configured URI and credentials. Each
collection is its own index under the ``jyotigpt_`` prefix, with a faiss
HNSW knn-vector field. Cosine similarity is computed via script_score and
normalized to [0, 1] with 1 = most similar.
"""

from typing import List, Optional

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from jyotigpt.config import (
    OPENSEARCH_CERT_VERIFY,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_SSL,
    OPENSEARCH_URI,
    OPENSEARCH_USERNAME,
)
from jyotigpt.retrieval.vector.main import GetResult, SearchResult, VectorItem


class OpenSearchClient:
    """CRUD/search client for an OpenSearch server."""

    def __init__(self):
        self.index_prefix = "jyotigpt"
        self.client = OpenSearch(
            hosts=[OPENSEARCH_URI],
            use_ssl=OPENSEARCH_SSL,
            verify_certs=OPENSEARCH_CERT_VERIFY,
            http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
        )

    # --- internal helpers -------------------------------------------------

    def _get_index_name(self, collection_name: str) -> str:
        return f"{self.index_prefix}_{collection_name}"

    def _result_to_get_result(self, result) -> Optional[GetResult]:
        if not result["hits"]["hits"]:
            return None

        ids = [hit["_id"] for hit in result["hits"]["hits"]]
        documents = [hit["_source"].get("text") for hit in result["hits"]["hits"]]
        metadatas = [hit["_source"].get("metadata") for hit in result["hits"]["hits"]]

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def _result_to_search_result(self, result) -> Optional[SearchResult]:
        if not result["hits"]["hits"]:
            return None

        ids = [hit["_id"] for hit in result["hits"]["hits"]]
        distances = [hit["_score"] for hit in result["hits"]["hits"]]
        documents = [hit["_source"].get("text") for hit in result["hits"]["hits"]]
        metadatas = [hit["_source"].get("metadata") for hit in result["hits"]["hits"]]

        return SearchResult(
            ids=[ids],
            distances=[distances],
            documents=[documents],
            metadatas=[metadatas],
        )

    def _create_index(self, collection_name: str, dimension: int):
        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "vector": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "index": True,
                        "similarity": "faiss",
                        "method": {
                            "name": "hnsw",
                            # Inner product approximates cosine similarity.
                            "space_type": "innerproduct",
                            "engine": "faiss",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16,
                            },
                        },
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "object"},
                }
            },
        }
        self.client.indices.create(
            index=self._get_index_name(collection_name), body=body
        )

    def _create_index_if_not_exists(self, collection_name: str, dimension: int):
        if not self.has_collection(collection_name):
            self._create_index(collection_name, dimension)

    def _create_batches(self, items: List[VectorItem], batch_size=100):
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]

    # --- collections ------------------------------------------------------

    def has_collection(self, collection_name: str) -> bool:
        # "Collection" is mapped to "index" here to match the other backends.
        return self.client.indices.exists(index=self._get_index_name(collection_name))

    def delete_collection(self, collection_name: str):
        self.client.indices.delete(index=self._get_index_name(collection_name))

    # --- reads ------------------------------------------------------------

    def search(
        self, collection_name: str, vectors: List[List[float | int]], limit: int
    ) -> Optional[SearchResult]:
        """Nearest-neighbor lookup; returns up to ``limit`` rows with scores."""
        try:
            if not self.has_collection(collection_name):
                return None

            query = {
                "size": limit,
                "_source": ["text", "metadata"],
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            # cosine similarity spans [-1, 1]; normalize to [0, 1].
                            "source": "(cosineSimilarity(params.query_value, doc[params.field]) + 1.0) / 2.0",
                            "params": {
                                "field": "vector",
                                "query_value": vectors[0],  # single query vector
                            },
                        },
                    }
                },
            }

            result = self.client.search(
                index=self._get_index_name(collection_name), body=query
            )

            return self._result_to_search_result(result)
        except Exception:
            return None

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        """Rows whose metadata matches every key in ``filter``."""
        if not self.has_collection(collection_name):
            return None

        query_body = {
            "query": {"bool": {"filter": []}},
            "_source": ["text", "metadata"],
        }

        for field, value in filter.items():
            query_body["query"]["bool"]["filter"].append(
                {"match": {"metadata." + str(field): value}}
            )

        size = limit if limit else 10

        try:
            result = self.client.search(
                index=self._get_index_name(collection_name),
                body=query_body,
                size=size,
            )

            return self._result_to_get_result(result)
        except Exception:
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Everything in the collection."""
        query = {"query": {"match_all": {}}, "_source": ["text", "metadata"]}

        result = self.client.search(
            index=self._get_index_name(collection_name), body=query
        )
        return self._result_to_get_result(result)

    # --- writes -----------------------------------------------------------

    def insert(self, collection_name: str, items: List[VectorItem]):
        """Insert rows, creating the index if needed."""
        self._create_index_if_not_exists(
            collection_name=collection_name, dimension=len(items[0]["vector"])
        )

        for batch in self._create_batches(items):
            actions = [
                {
                    "_op_type": "index",
                    "_index": self._get_index_name(collection_name),
                    "_id": item["id"],
                    "_source": {
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": item["metadata"],
                    },
                }
                for item in batch
            ]
            bulk(self.client, actions)

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """Insert-or-update rows; creates the index if needed."""
        self._create_index_if_not_exists(
            collection_name=collection_name, dimension=len(items[0]["vector"])
        )

        for batch in self._create_batches(items):
            actions = [
                {
                    "_op_type": "update",
                    "_index": self._get_index_name(collection_name),
                    "_id": item["id"],
                    "doc": {
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": item["metadata"],
                    },
                    "doc_as_upsert": True,
                }
                for item in batch
            ]
            bulk(self.client, actions)

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
        effective_filter = filter or metadata
        if ids:
            actions = [
                {
                    "_op_type": "delete",
                    "_index": self._get_index_name(collection_name),
                    "_id": id,
                }
                for id in ids
            ]
            bulk(self.client, actions)
        elif effective_filter:
            query_body = {"query": {"bool": {"filter": []}}}
            for field, value in effective_filter.items():
                query_body["query"]["bool"]["filter"].append(
                    {"match": {"metadata." + str(field): value}}
                )
            self.client.delete_by_query(
                index=self._get_index_name(collection_name), body=query_body
            )

    def reset(self):
        """Delete every index under the ``jyotigpt_`` prefix."""
        indices = self.client.indices.get(index=f"{self.index_prefix}_*")
        for index in indices:
            self.client.indices.delete(index=index)
