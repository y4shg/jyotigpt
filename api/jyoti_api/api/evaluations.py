"""Feedback (evaluations) endpoints: /api/v1/evaluations/*

Users create/update/delete their own feedback rows; admins see, export, and
clear everything. The evaluations config (enable flag + model) lives in the
admin settings row key ``evaluations``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from jyoti_api.api.deps import AdminUser, CurrentUser, SessionDep
from jyoti_api.domain import evaluations as evaluations_domain
from jyoti_api.domain.settings import get_group, set_value

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])

EVALUATIONS_KEY = "evaluations"


class EvaluationConfig(BaseModel):
    enable_evaluations: bool = False
    model: str = ""


class FeedbackCreate(BaseModel):
    type: str = "rating"
    data: dict[str, Any] = {}
    meta: dict[str, Any] = {}


class FeedbackUpdate(BaseModel):
    type: str | None = None
    data: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


# ------------------------------------------------------------------ config


@router.get("/config")
def get_config(user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    config = get_group(session, EVALUATIONS_KEY)
    return {
        "enable_evaluations": bool(config.get("enable_evaluations", False)),
        "model": str(config.get("model", "")),
    }


@router.post("/config")
def update_config(body: EvaluationConfig, admin: AdminUser, session: SessionDep) -> dict[str, bool]:
    set_value(
        session,
        EVALUATIONS_KEY,
        {"enable_evaluations": body.enable_evaluations, "model": (body.model or "").strip()},
    )
    return {"ok": True}


# ----------------------------------------------------------------- feedback


@router.post("/feedback", status_code=201)
def create_feedback(
    body: FeedbackCreate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    feedback = evaluations_domain.create_feedback(
        session,
        user.id,
        type_=(body.type or "rating"),
        data=body.data,
        meta=body.meta,
    )
    return evaluations_domain.to_feedback_dto(feedback)


@router.get("/feedback/{feedback_id}")
def get_feedback(
    feedback_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    feedback = evaluations_domain.get_feedback(session, user.id, feedback_id)
    return evaluations_domain.to_feedback_dto(feedback)


@router.post("/feedback/{feedback_id}")
def update_feedback(
    feedback_id: str, body: FeedbackUpdate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    feedback = evaluations_domain.update_feedback(
        session,
        user.id,
        feedback_id,
        type_=body.type,
        data=body.data,
        meta=body.meta,
    )
    return evaluations_domain.to_feedback_dto(feedback)


@router.delete("/feedback/{feedback_id}")
def delete_feedback(
    feedback_id: str, user: CurrentUser, session: SessionDep
) -> dict[str, bool]:
    evaluations_domain.delete_feedback(session, user.id, feedback_id)
    return {"ok": True}


@router.get("/feedbacks/user")
def get_user_feedbacks(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    return evaluations_domain.list_user_feedbacks(session, user.id)


@router.delete("/feedbacks")
def delete_user_feedbacks(user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    evaluations_domain.delete_user_feedbacks(session, user.id)
    return {"ok": True}


@router.get("/feedbacks/all")
def get_all_feedbacks(admin: AdminUser, session: SessionDep) -> list[dict[str, Any]]:
    return evaluations_domain.list_all_feedbacks(session)


@router.delete("/feedbacks/all")
def delete_all_feedbacks(admin: AdminUser, session: SessionDep) -> dict[str, bool]:
    evaluations_domain.delete_all_feedbacks(session)
    return {"ok": True}


@router.get("/feedbacks/all/export")
def export_all_feedbacks(admin: AdminUser, session: SessionDep) -> list[dict[str, Any]]:
    return evaluations_domain.list_all_feedbacks(session)
