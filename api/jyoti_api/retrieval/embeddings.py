"""Embedding generation via the Ollama embeddings API."""

from __future__ import annotations

from typing import Any

import httpx

from jyoti_api.config import Settings

DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"


async def resolve_embedding_model(settings: Settings) -> str:
    return (settings.rag_embedding_model or DEFAULT_EMBEDDING_MODEL).strip()


async def embed_texts(
    settings: Settings, texts: list[str], model: str
) -> list[list[float]]:
    """Embed one or more texts (one vector per text, in order)."""
    if not texts:
        return []
    base = settings.ollama_base_url.rstrip("/")
    vectors: list[list[float]] = []
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                response = await client.post(
                    f"{base}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                response.raise_for_status()
                vectors.append(_vector_from_payload(response.json()))
    except httpx.HTTPError as exc:
        from jyoti_api.errors import ApiError

        raise ApiError(f"Embedding request failed: {exc}") from exc
    return vectors


def _vector_from_payload(payload: dict[str, Any]) -> list[float]:
    if "embedding" in payload:
        return payload["embedding"]
    if "embeddings" in payload:
        return payload["embeddings"][0]
    raise ApiError("Ollama returned an unexpected embeddings payload.")


async def embed_query(settings: Settings, text: str) -> list[float]:
    model = await resolve_embedding_model(settings)
    vectors = await embed_texts(settings, [text], model)
    return vectors[0] if vectors else []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
