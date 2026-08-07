"""Prompt (slash-command template) routes.

Prompts are keyed by their command with a leading ``/``. Listing is split
between a read view (all prompts the user may read) and a write view (those
they may edit). Creating a prompt requires the workspace.prompts permission
for non-admins and refuses a taken command.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.models.prompts import PromptForm, PromptModel, Prompts, PromptUserResponse
from jyotigpt.utils.access_control import has_access, has_permission
from jyotigpt.utils.auth import get_verified_user

router = APIRouter()


@router.get("/", response_model=list[PromptModel])
async def get_prompts(user=Depends(get_verified_user)):
    if user.role == "admin":
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read")

    return prompts


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(user=Depends(get_verified_user)):
    if user.role == "admin":
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "write")

    return prompts


@router.post("/create", response_model=Optional[PromptModel])
async def create_new_prompt(
    request: Request, form_data: PromptForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.prompts", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    prompt = Prompts.get_prompt_by_command(form_data.command)
    if prompt is None:
        prompt = Prompts.insert_new_prompt(user.id, form_data)

        if prompt:
            return prompt
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.COMMAND_TAKEN,
    )


@router.get("/command/{command}", response_model=Optional[PromptModel])
async def get_prompt_by_command(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command(f"/{command}")

    if prompt:
        if (
            user.role == "admin"
            or prompt.user_id == user.id
            or has_access(user.id, "read", prompt.access_control)
        ):
            return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/command/{command}/update", response_model=Optional[PromptModel])
async def update_prompt_by_command(
    command: str,
    form_data: PromptForm,
    user=Depends(get_verified_user),
):
    prompt = Prompts.get_prompt_by_command(f"/{command}")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    prompt = Prompts.update_prompt_by_command(f"/{command}", form_data)
    if prompt:
        return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


@router.delete("/command/{command}/delete", response_model=bool)
async def delete_prompt_by_command(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command(f"/{command}")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Prompts.delete_prompt_by_command(f"/{command}")
    return result
