"""Elasticsearch vector-store client.

Index strategy: instead of creating one index per collection, every
collection is stored in a shared set of indexes — one index per embedding
dimension (``{prefix}_d{dim}``) — and rows are separated by a
``collection`` keyword field. This keeps the number of indexes bounded
while the embedding length stays fixed per model.

Note: scores are returned raw as ``cosineSimilarity + 1.0`` (the cosine
term spans [-1, 1], so scores end up in [0, 2]).
"""

import ssl
from typing import List, Optional

from elasticsearch import BadRequestError, Elasticsearch
from elasticsearch.helpers import bulk, scan

from jyotigpt.config import (
    ELASTICSEARCH_API_KEY,
    ELASTICSEARCH_CA_CERTS,
    ELASTICSEARCH_CLOUD_ID,
    ELASTICSEARCH_INDEX_PREFIX,
    ELASTICSEARCH_PASSWORD,
    ELASTICSEARCH_URL,
    ELASTICSEARCH_USERNAME,
    SSL_ASSERT_FINGERPRINT,
)
from jyotigpt.retrieval.vector.main import GetResult, SearchResult, VectorItem


class ElasticsearchClient:
    """CRUD/search client for an Elasticsearch cluster."""

    def __init__(self):
        self.index_prefix = ELASTICSEARCH_INDEX_PREFIX
        self.client = Elasticsearch(
            hosts=[ELASTICSEARCH_URL],
            ca_certs=ELASTICSEARCH_CA_CERTS,
            api_key=ELASTICSEARCH_API_KEY,
            cloud_id=ELASTICSEARCH_CLOUD_ID,
            basic_auth=(
                (ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
                if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD
                else None
            ),
            ssl_assert_fingerprint=SSL_ASSERT_FINGERPRINT,
        )

    # --- internal helpers -------------------------------------------------

    def _get_index_name(self, dimension: int) -> str:
        return f"{self.index_prefix}_d{str(dimension)}"

    def _scan_result_to_get_result(self, result) -> Optional[GetResult]:
        if not result:
            return None

        ids = [hit["_id"] for hit in result]
        documents = [hit["_source"].get("text") for hit in result]
        metadatas = [hit["_source"].get("metadata") for hit in result]

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def _result_to_get_result(self, result) -> Optional[GetResult]:
        if not result["hits"]["hits"]:
            return None

        ids = [hit["_id"] for hit in result["hits"]["hits"]]
        documents = [hit["_source"].get("text") for hit in result["hits"]["hits"]]
        metadatas = [hit["_source"].get("metadata") for hit in result["hits"]["hits"]]

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def _result_to_search_result(self, result) -> SearchResult:
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

    def _create_index(self, dimension: int):
        body = {
            "mappings": {
                "dynamic_templates": [
                    {
                        "strings": {
                            "match_mapping_type": "string",
                            "mapping": {"type": "keyword"},
                        }
                    }
                ],
                "properties": {
                    "collection": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": dimension,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "text": {"type": "text"},
                    "metadata": {"type": "object"},
                },
            }
        }
        self.client.indices.create(index=self._get_index_name(dimension), body=body)

    def _create_batches(self, items: List[VectorItem], batch_size=100):
        for i in range(0, len(items), batch_size):
            yield items[i : min(i + batch_size, len(items))]

    def _has_index(self, dimension: int):
        return self.client.indices.exists(
            index=self._get_index_name(dimension=dimension)
        )

    def get_or_create_index(self, dimension: int):
        if not self._has_index(dimension=dimension):
            self._create_index(dimension=dimension)

    # --- collections ------------------------------------------------------

    def has_collection(self, collection_name) -> bool:
        query_body = {"query": {"bool": {"filter": []}}}
        query_body["query"]["bool"]["filter"].append(
            {"term": {"collection": collection_name}}
        )

        try:
            result = self.client.count(index=f"{self.index_prefix}*", body=query_body)
            return result.body["count"] > 0
        except Exception:
            return None

    def delete_collection(self, collection_name: str):
        query = {"query": {"term": {"collection": collection_name}}}
        self.client.delete_by_query(index=f"{self.index_prefix}*", body=query)

    # --- reads ------------------------------------------------------------

    def search(
        self, collection_name: str, vectors: List[List[float]], limit: int
    ) -> Optional[SearchResult]:
        """Nearest-neighbor lookup; returns up to ``limit`` rows with scores."""
        query = {
            "size": limit,
            "_source": ["text", "metadata"],
            "query": {
                "script_score": {
                    "query": {
                        "bool": {"filter": [{"term": {"collection": collection_name}}]}
                    },
                    "script": {
                        "source": "cosineSimilarity(params.vector, 'vector') + 1.0",
                        "params": {"vector": vectors[0]},  # single query vector
                    },
                }
            },
        }

        result = self.client.search(
            index=self._get_index_name(len(vectors[0])), body=query
        )

        return self._result_to_search_result(result)

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
            query_body["query"]["bool"]["filter"].append({"term": {field: value}})
        query_body["query"]["bool"]["filter"].append(
            {"term": {"collection": collection_name}}
        )
        size = limit if limit else 10

        try:
            result = self.client.search(
                index=f"{self.index_prefix}*",
                body=query_body,
                size=size,
            )

            return self._result_to_get_result(result)
        except Exception:
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        """Everything in the collection (via scroll/scan)."""
        query = {
            "query": {"bool": {"filter": [{"term": {"collection": collection_name}}]}},
            "_source": ["text", "metadata"],
        }
        results = list(scan(self.client, index=f"{self.index_prefix}*", query=query))

        return self._scan_result_to_get_result(results)

    # --- writes -----------------------------------------------------------

    def insert(self, collection_name: str, items: List[VectorItem]):
        """Insert rows, creating the dimension index if needed."""
        dimension = len(items[0]["vector"])
        if not self._has_index(dimension=dimension):
            self._create_index(dimension=dimension)

        for batch in self._create_batches(items):
            actions = [
                {
                    "_index": self._get_index_name(dimension=dimension),
                    "_id": item["id"],
                    "_source": {
                        "collection": collection_name,
                        "vector": item["vector"],
                        "text": item["text"],
                        "metadata": item["metadata"],
                    },
                }
                for item in batch
            ]
            bulk(self.client, actions)

    def upsert(self, collection_name: str, items: List[VectorItem]):
        """Insert-or-update rows; creates the dimension index if needed."""
        if not self._has_index(dimension=len(items[0]["vector"])):
            self._create_index(dimension=len(items[0]["vector"]))

        for batch in self._create_batches(items):
            actions = [
                {
                    "_op_type": "update",
                    "_index": self._get_index_name(dimension=len(item["vector"])),
                    "_id": item["id"],
                    "doc": {
                        "collection": collection_name,
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
        """Delete a collection's rows by ``ids`` or a metadata ``filter``.

        ``metadata`` is an accepted alias for ``filter`` — some callers pass
        the selector under that name.
        """
        effective_filter = filter or metadata
        query = {
            "query": {"bool": {"filter": [{"term": {"collection": collection_name}}]}}
        }
        if ids:
            query["query"]["bool"]["filter"].append({"terms": {"_id": ids}})
        elif effective_filter:
            for field, value in effective_filter.items():
                query["query"]["bool"]["filter"].append(
                    {"term": {f"metadata.{field}": value}}
                )

        self.client.delete_by_query(index=f"{self.index_prefix}*", body=query)

    def reset(self):
        """Delete every index under the configured prefix."""
        indices = self.client.indices.get(index=f"{self.index_prefix}*")
        for index in indices:
            self.client.indices.delete(index=index)
