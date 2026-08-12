"""Collections (knowledge bases): persistence, chunking + embedding.

A collection groups ``CollectionItem`` rows — each row is one chunk of text
with its embedding vector. Items are produced from uploaded documents or from
manually added text; embeddings come from the Ollama embeddings API.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jyoti_api.config import Settings
from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.persistence.schema import Collection, CollectionItem, Document
from jyoti_api.retrieval import chunker
from jyoti_api.retrieval.embeddings import embed_texts, resolve_embedding_model


def to_collection_dto(session: Session, collection: Collection) -> dict[str, Any]:
    item_count = session.scalar(
        select(func.count(CollectionItem.id)).where(
            CollectionItem.collection_id == collection.id
        )
    )
    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "embedding_model": collection.embedding_model,
        "is_shared": collection.is_shared,
        "item_count": item_count or 0,
        "created_at": collection.created_at.isoformat() if collection.created_at else None,
        "updated_at": collection.updated_at.isoformat() if collection.updated_at else None,
    }


def list_collections(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Collection)
        .where((Collection.user_id == user_id) | (Collection.is_shared.is_(True)))
        .order_by(Collection.created_at)
    ).all()
    return [to_collection_dto(session, c) for c in rows]


def create_collection(
    session: Session,
    user_id: str,
    *,
    name: str,
    description: str = "",
    embedding_model: str = "",
    is_shared: bool = False,
) -> Collection:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Collection name is required.")
    collection = Collection(
        user_id=user_id,
        name=name[:200],
        description=(description or ""),
        embedding_model=(embedding_model or "").strip()[:255],
        is_shared=is_shared,
    )
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def _owned(session: Session, user_id: str, collection_id: str) -> Collection:
    collection = session.get(Collection, collection_id)
    if not collection:
        raise NotFoundError("Collection not found.")
    if collection.user_id != user_id and not collection.is_shared:
        raise NotFoundError("Collection not found.")
    return collection


def update_collection(
    session: Session,
    user_id: str,
    collection_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    embedding_model: str | None = None,
    is_shared: bool | None = None,
) -> Collection:
    collection = _owned(session, user_id, collection_id)
    if collection.user_id != user_id:
        raise NotFoundError("Collection not found.")  # shared collections are read-only
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("Collection name is required.")
        collection.name = name[:200]
    if description is not None:
        collection.description = description
    if embedding_model is not None:
        collection.embedding_model = (embedding_model or "").strip()[:255]
    if is_shared is not None:
        collection.is_shared = is_shared
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def delete_collection(session: Session, user_id: str, collection_id: str) -> None:
    collection = _owned(session, user_id, collection_id)
    if collection.user_id != user_id:
        raise NotFoundError("Collection not found.")
    session.delete(collection)
    session.commit()


# ------------------------------------------------------------------- items


def to_item_dto(item: CollectionItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "collection_id": item.collection_id,
        "document_id": item.document_id,
        "chunk_index": item.chunk_index,
        "content": item.chunk_text,
        "source": item.source_ref,
        "has_embedding": item.embedding is not None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def list_items(
    session: Session, user_id: str, collection_id: str, *, limit: int = 200, offset: int = 0
) -> list[dict[str, Any]]:
    collection = _owned(session, user_id, collection_id)
    rows = session.scalars(
        select(CollectionItem)
        .where(CollectionItem.collection_id == collection.id)
        .order_by(CollectionItem.chunk_index, CollectionItem.created_at)
        .limit(limit)
        .offset(offset)
    ).all()
    return [to_item_dto(i) for i in rows]


async def _chunk_and_embed(
    session: Session,
    settings: Settings,
    collection: Collection,
    *,
    text: str,
    source_ref: str,
    document_id: str | None = None,
    start_index: int = 0,
) -> list[CollectionItem]:
    model = collection.embedding_model or await resolve_embedding_model(settings)
    chunks = chunker.chunk_text(
        text, settings.rag_chunk_size, settings.rag_chunk_overlap
    )
    if not chunks:
        return []
    vectors = await embed_texts(settings, chunks, model)
    items = []
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        item = CollectionItem(
            collection_id=collection.id,
            document_id=document_id,
            chunk_index=start_index + index,
            chunk_text=chunk,
            embedding=vector,
            source_ref=source_ref,
        )
        session.add(item)
        items.append(item)
    if collection.embedding_model != model:
        collection.embedding_model = model
        session.add(collection)
    session.commit()
    return items


async def add_text_item(
    session: Session,
    settings: Settings,
    *,
    user_id: str,
    collection_id: str,
    content: str,
) -> list[CollectionItem]:
    collection = _owned(session, user_id, collection_id)
    if collection.user_id != user_id:
        raise NotFoundError("Collection not found.")
    content = (content or "").strip()
    if not content:
        raise ValidationError("Text content is required.")
    source_ref = f"note-{uuid.uuid4().hex[:8]}"
    return await _chunk_and_embed(
        session, settings, collection, text=content, source_ref=source_ref
    )


async def add_document_item(
    session: Session,
    settings: Settings,
    *,
    user_id: str,
    collection_id: str,
    document_id: str,
) -> list[CollectionItem]:
    collection = _owned(session, user_id, collection_id)
    if collection.user_id != user_id:
        raise NotFoundError("Collection not found.")
    document = session.get(Document, document_id)
    if not document or document.user_id != user_id:
        raise NotFoundError("Document not found.")
    if not document.extracted_text.strip():
        raise ValidationError(
            "This file type could not be parsed for retrieval."
        )
    existing = session.scalars(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.document_id == document.id,
        )
    ).all()
    if existing:
        raise ValidationError("This document is already in the collection.")
    source_ref = chunker.split_source_ref(document.filename, 0)
    return await _chunk_and_embed(
        session,
        settings,
        collection,
        text=document.extracted_text,
        source_ref=source_ref,
        document_id=document.id,
    )


def remove_item(session: Session, user_id: str, collection_id: str, item_id: str) -> None:
    collection = _owned(session, user_id, collection_id)
    if collection.user_id != user_id:
        raise NotFoundError("Collection not found.")
    item = session.get(CollectionItem, item_id)
    if not item or item.collection_id != collection.id:
        raise NotFoundError("Collection item not found.")
    session.delete(item)
    session.commit()


def get_collection(session: Session, user_id: str, collection_id: str) -> Collection:
    return _owned(session, user_id, collection_id)
