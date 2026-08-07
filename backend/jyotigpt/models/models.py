"""Model registry persistence.

A ``model`` row is either a *base* model (proxied to an upstream provider,
``base_model_id`` is null) or an override that wraps one (it sets
``base_model_id``). Overrides carry params, display meta, and optional
access-control rules restricting read/write by group or user.
"""

import logging
import time
from typing import Optional

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.internal.db import Base, JSONField, get_db
from jyotigpt.models.users import UserResponse, Users
from jyotigpt.utils.access_control import has_access
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, JSON, Text

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


# Arbitrary extra keys are allowed in both params and meta.
class ModelParams(BaseModel):
    model_config = ConfigDict(extra="allow")


class ModelMeta(BaseModel):
    profile_image_url: Optional[str] = "/static/favicon.png"

    description: Optional[str] = None
    """User-facing description of the model."""

    capabilities: Optional[dict] = None

    model_config = ConfigDict(extra="allow")


class Model(Base):
    __tablename__ = "model"

    id = Column(Text, primary_key=True)
    """The model's id as used in the API. Overrides an existing model if reused."""
    user_id = Column(Text)

    base_model_id = Column(Text, nullable=True)
    """Optional pointer to the actual upstream model to proxy requests to."""

    name = Column(Text)
    """The human-readable display name of the model."""

    params = Column(JSONField)
    """JSON-encoded blob of parameters, see ``ModelParams``."""

    meta = Column(JSONField)
    """JSON-encoded blob of metadata, see ``ModelMeta``."""

    access_control = Column(JSON, nullable=True)
    """Data access rules for this entry.

    - ``None``: public, available to every user with the "user" role.
    - ``{}``: private, restricted to the owner.
    - Custom permissions: per-group / per-user ``read`` and ``write`` rules,
      e.g. ``{"read": {"group_ids": [...], "user_ids": [...]}}``.
    """

    is_active = Column(Boolean, default=True)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class ModelModel(BaseModel):
    id: str
    user_id: str
    base_model_id: Optional[str] = None

    name: str
    params: ModelParams
    meta: ModelMeta

    access_control: Optional[dict] = None

    is_active: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


class ModelUserResponse(ModelModel):
    user: Optional[UserResponse] = None


class ModelResponse(ModelModel):
    pass


class ModelForm(BaseModel):
    id: str
    base_model_id: Optional[str] = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_control: Optional[dict] = None
    is_active: bool = True


class ModelsTable:
    def insert_new_model(
        self, form_data: ModelForm, user_id: str
    ) -> Optional[ModelModel]:
        model = ModelModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        try:
            with get_db() as db:
                result = Model(**model.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)

                if result:
                    return ModelModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            print(e)
            return None

    def get_all_models(self) -> list[ModelModel]:
        with get_db() as db:
            return [ModelModel.model_validate(model) for model in db.query(Model).all()]

    def get_models(self) -> list[ModelUserResponse]:
        with get_db() as db:
            models = []
            for model in db.query(Model).filter(Model.base_model_id != None).all():
                user = Users.get_user_by_id(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **ModelModel.model_validate(model).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return models

    def get_base_models(self) -> list[ModelModel]:
        with get_db() as db:
            return [
                ModelModel.model_validate(model)
                for model in db.query(Model).filter(Model.base_model_id == None).all()
            ]

    def get_models_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[ModelUserResponse]:
        models = self.get_models()
        return [
            model
            for model in models
            if model.user_id == user_id
            or has_access(user_id, permission, model.access_control)
        ]

    def get_model_by_id(self, id: str) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                model = db.get(Model, id)
                return ModelModel.model_validate(model)
        except Exception:
            return None

    def toggle_model_by_id(self, id: str) -> Optional[ModelModel]:
        with get_db() as db:
            try:
                is_active = db.query(Model).filter_by(id=id).first().is_active

                db.query(Model).filter_by(id=id).update(
                    {
                        "is_active": not is_active,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                return self.get_model_by_id(id)
            except Exception:
                return None

    def update_model_by_id(self, id: str, model: ModelForm) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                # The id is immutable; update only the remaining fields.
                result = (
                    db.query(Model)
                    .filter_by(id=id)
                    .update(model.model_dump(exclude={"id"}))
                )
                db.commit()

                model = db.get(Model, id)
                db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            print(e)

            return None

    def delete_model_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Model).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_all_models(self) -> bool:
        try:
            with get_db() as db:
                db.query(Model).delete()
                db.commit()

                return True
        except Exception:
            return False


Models = ModelsTable()
