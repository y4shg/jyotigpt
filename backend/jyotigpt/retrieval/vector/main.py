"""Result models shared by the vector-store clients.

Every client in ``dbs/`` returns these shapes, so the retrieval layer
can treat all backends uniformly.
"""

from typing import Any, List, Optional

from pydantic import BaseModel


class VectorItem(BaseModel):
    """A single row to store: id, text, embedding, and arbitrary metadata."""

    id: str
    text: str
    vector: List[float | int]
    metadata: Any


class GetResult(BaseModel):
    """Rows fetched from a collection (no similarity distances)."""

    ids: Optional[List[List[str]]]
    documents: Optional[List[List[str]]]
    metadatas: Optional[List[List[Any]]]


class SearchResult(GetResult):
    """Rows fetched from a collection, ordered by similarity, with distances."""

    distances: Optional[List[List[float | int]]]
