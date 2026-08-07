"""Model catalogue HTTP routes.

Admins and workspace editors may create custom models; read access is
owner- or access-control based. Model ids are passed as query parameters
(rather than path parameters) so ids containing "/" keep working.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.models.models import ModelForm, ModelModel, ModelResponse, ModelUserResponse
from jyotigpt.utils.access_control import has_access, has_permission
from jyotigpt.utils.auth import get_admin_user, get_verified_user

from .service import models

router = APIRouter()


@router.get("/", response_model=list[ModelUserResponse])
async def get_models(id: Optional[str] = None, user=Depends(get_verified_user)):
    return models.list_models(is_admin=user.role == "admin", user_id=user.id)


@router.get("/base", response_model=list[ModelResponse])
async def get_base_models(user=Depends(get_admin_user)):
    return models.list_base()


@router.post("/create", response_model=Optional[ModelModel])
async def create_new_model(
    request: Request,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.models", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if models.get(form_data.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.MODEL_ID_TAKEN,
        )

    model = models.create(form_data, user.id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    return model


@router.get("/model", response_model=Optional[ModelResponse])
async def get_model_by_id(id: str, user=Depends(get_verified_user)):
    model = models.get(id)
    if model:
        if (
            user.role == "admin"
            or model.user_id == user.id
            or has_access(user.id, "read", model.access_control)
        ):
            return model
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/model/toggle", response_model=Optional[ModelResponse])
async def toggle_model_by_id(id: str, user=Depends(get_verified_user)):
    model = models.get(id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not (
        user.role == "admin"
        or model.user_id == user.id
        or has_access(user.id, "write", model.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    model = models.toggle(id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
        )
    return model


@router.post("/model/update", response_model=Optional[ModelModel])
async def update_model_by_id(
    id: str,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    model = models.get(id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return models.update(id, form_data)


@router.delete("/model/delete", response_model=bool)
async def delete_model_by_id(id: str, user=Depends(get_verified_user)):
    model = models.get(id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    return models.delete(id)


@router.delete("/delete/all", response_model=bool)
async def delete_all_models(user=Depends(get_admin_user)):
    return models.delete_all()
