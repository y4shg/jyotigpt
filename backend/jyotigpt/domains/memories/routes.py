"""Memory HTTP routes.

Exposes per-user memory management (list, add, query, reset, update, delete)
plus a diagnostic embeddings endpoint. Every mutation keeps the vector store
in sync via the domain service; the embedding function is taken from the app
state.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from jyotigpt.models.memories import MemoryModel
from jyotigpt.utils.auth import get_verified_user

from .service import memories

router = APIRouter()


@router.get("/ef")
async def get_embeddings(request: Request):
    return {"result": request.app.state.EMBEDDING_FUNCTION("hello world")}


@router.get("/", response_model=list[MemoryModel])
async def get_memories(user=Depends(get_verified_user)):
    return memories.get_by_user(user.id)


class AddMemoryForm(BaseModel):
    content: str


class MemoryUpdateModel(BaseModel):
    content: Optional[str] = None


class QueryMemoryForm(BaseModel):
    content: str
    k: Optional[int] = 1


@router.post("/add", response_model=Optional[MemoryModel])
async def add_memory(
    request: Request,
    form_data: AddMemoryForm,
    user=Depends(get_verified_user),
):
    memory = memories.add(
        user.id, form_data.content, request.app.state.EMBEDDING_FUNCTION
    )

    return memory


@router.post("/query")
async def query_memory(
    request: Request, form_data: QueryMemoryForm, user=Depends(get_verified_user)
):
    return memories.query(
        user.id,
        form_data.content,
        form_data.k,
        request.app.state.EMBEDDING_FUNCTION,
    )


@router.post("/reset", response_model=bool)
async def reset_memory_from_vector_db(
    request: Request, user=Depends(get_verified_user)
):
    return memories.reset(user.id, request.app.state.EMBEDDING_FUNCTION)


@router.delete("/delete/user", response_model=bool)
async def delete_memory_by_user_id(user=Depends(get_verified_user)):
    return memories.delete_by_user(user.id)


@router.post("/{memory_id}/update", response_model=Optional[MemoryModel])
async def update_memory_by_id(
    memory_id: str,
    request: Request,
    form_data: MemoryUpdateModel,
    user=Depends(get_verified_user),
):
    memory = memories.update(
        memory_id,
        form_data.content,
        user.id,
        request.app.state.EMBEDDING_FUNCTION,
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.delete("/{memory_id}", response_model=bool)
async def delete_memory_by_id(memory_id: str, user=Depends(get_verified_user)):
    return memories.delete(memory_id, user.id)
