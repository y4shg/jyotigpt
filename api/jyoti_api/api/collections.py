"""Collection endpoints: /api/v1/collections/* + /api/v1/search"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.domain import collections
from jyoti_api.retrieval.search import search_collections

router = APIRouter(prefix="/api/v1", tags=["collections"])


class CollectionWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    embedding_model: str = ""
    is_shared: bool = False


class CollectionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    embedding_model: str | None = None
    is_shared: bool | None = None


class CollectionTextItem(BaseModel):
    content: str = Field(min_length=1)


class CollectionDocumentItem(BaseModel):
    document_id: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    collection_ids: list[str] = []
    top_k: int | None = Field(default=None, ge=1, le=50)


# ------------------------------------------------------------------ crud


@router.get("/collections")
def list_collections(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return collections.list_collections(session, user.id)


@router.post("/collections", status_code=201)
def create_collection(
    body: CollectionWrite, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    collection = collections.create_collection(
        session,
        user.id,
        name=body.name,
        description=body.description,
        embedding_model=body.embedding_model,
        is_shared=body.is_shared,
    )
    return collections.to_collection_dto(session, collection)


@router.get("/collections/{collection_id}")
def get_collection(
    collection_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    collection = collections.get_collection(session, user.id, collection_id)
    return collections.to_collection_dto(session, collection)


@router.patch("/collections/{collection_id}")
def update_collection(
    collection_id: str, body: CollectionPatch, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    collection = collections.update_collection(
        session,
        user.id,
        collection_id,
        name=body.name,
        description=body.description,
        embedding_model=body.embedding_model,
        is_shared=body.is_shared,
    )
    return collections.to_collection_dto(session, collection)


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    collections.delete_collection(session, user.id, collection_id)
    return {"ok": True}


# ------------------------------------------------------------------- items


@router.get("/collections/{collection_id}/items")
def list_items(
    collection_id: str,
    user: CurrentUser,
    session: SessionDep,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return collections.list_items(
        session, user.id, collection_id, limit=limit, offset=offset
    )


@router.post("/collections/{collection_id}/items/text", status_code=201)
async def add_text_item(
    collection_id: str, body: CollectionTextItem, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    settings = get_settings()
    items = await collections.add_text_item(
        session,
        settings,
        user_id=user.id,
        collection_id=collection_id,
        content=body.content,
    )
    return {
        "collection_id": collection_id,
        "items_created": len(items),
        "items": [collections.to_item_dto(i) for i in items],
    }


@router.post("/collections/{collection_id}/items/document", status_code=201)
async def add_document_item(
    collection_id: str, body: CollectionDocumentItem, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    settings = get_settings()
    items = await collections.add_document_item(
        session,
        settings,
        user_id=user.id,
        collection_id=collection_id,
        document_id=body.document_id,
    )
    return {
        "collection_id": collection_id,
        "items_created": len(items),
        "items": [collections.to_item_dto(i) for i in items],
    }


@router.delete("/collections/{collection_id}/items/{item_id}")
def remove_item(
    collection_id: str, item_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    collections.remove_item(session, user.id, collection_id, item_id)
    return {"ok": True}


# ------------------------------------------------------------------- search


@router.post("/search")
async def search(body: SearchRequest, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    """Semantic search across the user's collections (RAG entry point)."""
    settings = get_settings()
    results = await search_collections(
        session,
        settings,
        user_id=user.id,
        collection_ids=body.collection_ids,
        query=body.query,
        top_k=body.top_k,
    )
    return {"query": body.query, "results": results}
