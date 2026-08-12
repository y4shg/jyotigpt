"""Feedback (evaluations): persistence + serialization.

Feedback rows record a rating/comment a user attaches to a chat turn or
model. ``data`` holds the rating payload (rating, model_id, reason,
comment); ``meta`` ties it to a chat/message. Admins can list, export, and
clear all feedback.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from jyoti_api.errors import NotFoundError
from jyoti_api.persistence.schema import Feedback, User


def to_feedback_dto(feedback: Feedback) -> dict[str, Any]:
    return {
        "id": feedback.id,
        "user_id": feedback.user_id,
        "version": feedback.version,
        "type": feedback.type,
        "data": feedback.data or {},
        "meta": feedback.meta or {},
        "snapshot": feedback.snapshot,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None,
    }


def to_feedback_user_dto(feedback: Feedback, user: User) -> dict[str, Any]:
    """Admin listing: feedback row plus a minimal user payload."""
    dto = to_feedback_dto(feedback)
    dto["user"] = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
    }
    return dto


def create_feedback(
    session: Session,
    user_id: str,
    *,
    type_: str,
    data: dict[str, Any],
    meta: dict[str, Any],
    snapshot: dict[str, Any] | None = None,
) -> Feedback:
    feedback = Feedback(
        user_id=user_id,
        version=0,
        type=type_ or "rating",
        data=data or {},
        meta=meta or {},
        snapshot=snapshot,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def _owned(session: Session, user_id: str, feedback_id: str) -> Feedback:
    feedback = session.get(Feedback, feedback_id)
    if not feedback or feedback.user_id != user_id:
        raise NotFoundError("Feedback not found.")
    return feedback


def get_feedback(session: Session, user_id: str, feedback_id: str) -> Feedback:
    return _owned(session, user_id, feedback_id)


def update_feedback(
    session: Session,
    user_id: str,
    feedback_id: str,
    *,
    type_: str | None = None,
    data: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> Feedback:
    feedback = _owned(session, user_id, feedback_id)
    if type_ is not None:
        feedback.type = type_
    if data is not None:
        feedback.data = data
    if meta is not None:
        feedback.meta = meta
    feedback.version += 1
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def delete_feedback(session: Session, user_id: str, feedback_id: str) -> None:
    feedback = _owned(session, user_id, feedback_id)
    session.delete(feedback)
    session.commit()


def list_user_feedbacks(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Feedback)
        .where(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
    ).all()
    return [to_feedback_dto(f) for f in rows]


def delete_user_feedbacks(session: Session, user_id: str) -> None:
    session.execute(delete(Feedback).where(Feedback.user_id == user_id))
    session.commit()


def list_all_feedbacks(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Feedback, User)
        .join(User, Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
    ).all()
    return [to_feedback_user_dto(f, u) for f, u in rows]


def delete_all_feedbacks(session: Session) -> None:
    session.execute(delete(Feedback))
    session.commit()
