"""Semantic search over collection chunks."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.config import Settings
from jyoti_api.errors import NotFoundError
from jyoti_api.persistence.schema import Collection, CollectionItem
from jyoti_api.retrieval.embeddings import cosine_similarity, embed_query


async def search_collections(
    session: Session,
    settings: Settings,
    *,
    user_id: str,
    collection_ids: list[str],
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return the best-matching chunks across the given collections."""
    query = (query or "").strip()
    if not query:
        return []
    collection_ids = [c for c in collection_ids or [] if c]
    if not collection_ids:
        return []
    top_k = top_k or settings.rag_top_k or 4

    owned = set(
        session.scalars(
            select(Collection.id).where(
                Collection.user_id == user_id,
                Collection.id.in_(collection_ids),
            )
        ).all()
    )
    shared = set(
        session.scalars(
            select(Collection.id).where(
                Collection.is_shared.is_(True),
                Collection.id.in_(collection_ids),
            )
        ).all()
    )
    allowed = owned | shared
    if not allowed:
        raise NotFoundError("No matching collections found.")
    allowed = [c for c in collection_ids if c in allowed]
    if not allowed:
        return []

    vector = await embed_query(settings, query)
    if not vector:
        return []

    rows = session.scalars(
        select(CollectionItem).where(
            CollectionItem.collection_id.in_(allowed),
            CollectionItem.embedding.is_not(None),
        )
    ).all()
    scored = []
    for item in rows:
        score = cosine_similarity(vector, item.embedding or [])
        if score <= 0:
            continue
        scored.append(
            {
                "id": item.id,
                "collection_id": item.collection_id,
                "chunk_index": item.chunk_index,
                "content": item.chunk_text,
                "source": item.source_ref,
                "score": round(score, 4),
            }
        )
    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[:top_k]


def to_context(results: list[dict[str, Any]]) -> str:
    """Flatten search results into the context block injected into prompts."""
    if not results:
        return ""
    blocks = []
    for result in results:
        source = result.get("source") or "unknown"
        blocks.append(f"[{source}]\n{result.get('content', '')}")
    return "\n\n".join(blocks)
