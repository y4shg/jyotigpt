"""Model catalog: provider models, custom presets, and flow-server pipelines.

The catalog is the union of what the configured providers offer, merged with
the user's custom presets (``ModelRecord`` rows: a base provider model with
overridden name/params) and, when flows are enabled, the pipelines served by
the flow server. Disabled custom presets drop their base model from the
catalog.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.config import Settings, get_settings
from jyoti_api.errors import NotFoundError, ValidationError
from jyoti_api.integrations.providers import list_ollama_models, list_openai_models
from jyoti_api.persistence.schema import ModelRecord
from jyoti_api.services import flows


def get_settings() -> Settings:
    from jyoti_api.config import get_settings as _get_settings

    return _get_settings()


async def list_models(session: Session) -> list[dict[str, Any]]:
    settings = get_settings()
    models: list[dict[str, Any]] = []
    if settings.openai_api_key:
        models.extend(await list_openai_models(settings))
    models.extend(await list_ollama_models(settings))
    # de-duplicate by id, prefer the first (openai) entry
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for model in models:
        if model["id"] in seen:
            continue
        seen.add(model["id"])
        unique.append(model)
    catalog = _merge_custom(session, unique)
    catalog.extend(await _flow_pipeline_models(session, settings))
    return catalog


def _merge_custom(session: Session, models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = {
        (record.provider, record.model_id): record
        for record in session.scalars(select(ModelRecord)).all()
    }
    result: list[dict[str, Any]] = []
    for model in models:
        record = records.pop((model["provider"], model["id"]), None)
        if record is not None and not record.enabled:
            continue  # disabled custom preset hides its base model
        entry = dict(model)
        if record is not None:
            entry["name"] = record.name or model["name"]
            entry["custom"] = True
            entry["params"] = record.params or {}
            entry.setdefault("info", {})
            entry["info"] = dict(entry["info"])
            entry["info"]["meta"] = dict(entry["info"].get("meta", {}))
            entry["info"]["meta"]["description"] = (
                record.params or {}
            ).get("description") or entry["info"]["meta"].get("description", "")
        else:
            entry["custom"] = False
            entry["params"] = {}
        result.append(entry)
    # Custom presets for models the provider is not currently serving still
    # show in the catalog (the preset may be aimed at a model not yet pulled).
    for (provider, model_id), record in records.items():
        if not record.enabled:
            continue
        result.append(
            {
                "id": model_id,
                "name": record.name or model_id,
                "provider": provider,
                "owned_by": "custom",
                "custom": True,
                "params": record.params or {},
                "info": {
                    "meta": {
                        "profile_image_url": "",
                        "description": (record.params or {}).get("description", ""),
                    }
                },
            }
        )
    return result


async def _flow_pipeline_models(
    session: Session, settings: Settings
) -> list[dict[str, Any]]:
    pipelines = await flows.list_pipelines(session, settings)
    result = []
    for pipeline in pipelines:
        pipeline_id = pipeline.get("id") or pipeline.get("name")
        if not pipeline_id:
            continue
        result.append(
            {
                "id": f"pipeline-{pipeline_id}",
                "name": pipeline.get("name") or pipeline_id,
                "provider": "flow",
                "owned_by": "flow",
                "pipeline": pipeline_id,
                "info": {
                    "meta": {
                        "profile_image_url": "",
                        "description": pipeline.get("description", ""),
                    }
                },
            }
        )
    return result


# ------------------------------------------------------------------- presets


def to_model_record_dto(record: ModelRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "provider": record.provider,
        "model_id": record.model_id,
        "name": record.name or record.model_id,
        "enabled": record.enabled,
        "params": record.params or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def list_model_records(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(select(ModelRecord).order_by(ModelRecord.created_at)).all()
    return [to_model_record_dto(r) for r in rows]


def upsert_model_record(
    session: Session,
    *,
    provider: str,
    model_id: str,
    name: str = "",
    enabled: bool = True,
    params: dict[str, Any] | None = None,
) -> ModelRecord:
    if provider not in ("ollama", "openai"):
        raise ValidationError("Provider must be 'ollama' or 'openai'.")
    model_id = (model_id or "").strip()
    if not model_id:
        raise ValidationError("Model ID is required.")
    record = session.scalars(
        select(ModelRecord).where(
            ModelRecord.provider == provider, ModelRecord.model_id == model_id
        )
    ).first()
    if record is None:
        record = ModelRecord(provider=provider, model_id=model_id)
        session.add(record)
    if name is not None:
        record.name = (name or "").strip()[:255]
    if enabled is not None:
        record.enabled = enabled
    if params is not None:
        record.params = params or {}
    session.commit()
    session.refresh(record)
    return record


def get_model_record(session: Session, provider: str, model_id: str) -> ModelRecord:
    record = session.scalars(
        select(ModelRecord).where(
            ModelRecord.provider == provider, ModelRecord.model_id == model_id
        )
    ).first()
    if record is None:
        raise NotFoundError("Custom model not found.")
    return record


def delete_model_record(session: Session, provider: str, model_id: str) -> None:
    record = session.scalars(
        select(ModelRecord).where(
            ModelRecord.provider == provider, ModelRecord.model_id == model_id
        )
    ).first()
    if record is None:
        raise NotFoundError("Custom model not found.")
    session.delete(record)
    session.commit()


def resolve_record_params(
    session: Session, provider: str, model_id: str
) -> dict[str, Any]:
    """The effective params of a custom preset, or {} when none exists."""
    record = session.scalars(
        select(ModelRecord).where(
            ModelRecord.provider == provider, ModelRecord.model_id == model_id
        )
    ).first()
    if record is None or not record.enabled:
        return {}
    return record.params or {}
