"""Model endpoints: /api/v1/models/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from jyoti_api.api.deps import CurrentUser, SessionDep
from jyoti_api.domain import models

router = APIRouter(prefix="/api/v1", tags=["models"])


class ModelPreset(BaseModel):
    provider: str = Field(pattern="^(ollama|openai)$")
    model_id: str = Field(min_length=1, max_length=255)
    name: str = ""
    enabled: bool = True
    params: dict[str, Any] = {}


@router.get("/models")
async def catalog(session: SessionDep) -> list[dict[str, Any]]:
    return await models.list_models(session)


@router.get("/models/custom")
def list_custom(session: SessionDep) -> list[dict[str, Any]]:
    return models.list_model_records(session)


@router.post("/models/create", status_code=201)
def create_model(body: ModelPreset, session: SessionDep) -> dict[str, Any]:
    record = models.upsert_model_record(
        session,
        provider=body.provider,
        model_id=body.model_id,
        name=body.name,
        enabled=body.enabled,
        params=body.params,
    )
    return models.to_model_record_dto(record)


@router.patch("/models/{provider}/{model_id}")
def update_model(
    provider: str, model_id: str, body: ModelPreset, session: SessionDep
) -> dict[str, Any]:
    record = models.upsert_model_record(
        session,
        provider=provider,
        model_id=model_id,
        name=body.name,
        enabled=body.enabled,
        params=body.params,
    )
    return models.to_model_record_dto(record)


@router.delete("/models/{provider}/{model_id}")
def delete_model(provider: str, model_id: str, session: SessionDep) -> dict[str, bool]:
    models.delete_model_record(session, provider, model_id)
    return {"ok": True}
