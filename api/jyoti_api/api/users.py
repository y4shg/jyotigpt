"""User management + API keys: /api/v1/users/*"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from jyoti_api.api.deps import AdminUser, CurrentUser, SessionDep
from jyoti_api.domain import accounts, security
from jyoti_api.errors import ConflictError, NotFoundError, ValidationError
from jyoti_api.persistence.schema import ApiKey, User
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    role: str = "user"  # admin | user | pending


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: str | None = None
    status: str | None = None  # active | deactivated


class ApiKeyCreate(BaseModel):
    name: str = ""


class ApiKeyOut(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: Any = None
    key: str | None = None  # only present once, on creation


# ---------------------------------------------------------------- own profile


@router.get("/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return accounts.to_public(user, include_keys=True)


@router.patch("/me")
def update_me(body: UserUpdate, user: CurrentUser, session: SessionDep) -> dict[str, Any]:
    if body.name is not None:
        if not body.name.strip():
            raise ValidationError("Name cannot be empty.")
        user.name = body.name.strip()
    if body.email is not None:
        email = body.email.strip().lower()
        if email != user.email:
            clash = session.scalars(select(User).where(User.email == email)).first()
            if clash:
                raise ConflictError("An account with this email already exists.")
            user.email = email
    if body.password is not None:
        user.password_hash = security.hash_password(body.password)
    if body.role is not None or body.status is not None:
        raise ValidationError("Role/status changes must be made by an administrator.")
    session.add(user)
    session.commit()
    session.refresh(user)
    return accounts.to_public(user)


# ------------------------------------------------------------------ API keys


@router.get("/api-keys")
def list_api_keys(user: CurrentUser, session: SessionDep) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at)
    ).all()
    return [
        {"id": k.id, "name": k.name, "prefix": k.prefix, "created_at": k.created_at.isoformat()}
        for k in rows
    ]


@router.post("/api-keys", response_model=ApiKeyOut)
def create_api_key(
    body: ApiKeyCreate, user: CurrentUser, session: SessionDep
) -> dict[str, Any]:
    settings = get_settings_guard()
    prefix, key, key_hash = security.generate_api_key(body.name)
    record = ApiKey(user_id=user.id, name=body.name, prefix=prefix, key_hash=key_hash)
    session.add(record)
    session.commit()
    session.refresh(record)
    return {
        "id": record.id,
        "name": record.name,
        "prefix": record.prefix,
        "created_at": record.created_at.isoformat(),
        "key": key,
    }


def get_settings_guard() -> Any:
    from jyoti_api.config import get_settings

    settings = get_settings()
    if not settings.enable_api_keys:
        raise ValidationError("API keys are disabled.")
    return settings


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: str, user: CurrentUser, session: SessionDep) -> dict[str, bool]:
    record = session.scalars(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    ).first()
    if not record:
        raise NotFoundError("API key not found.")
    session.delete(record)
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------ admin (all users)


@router.get("")
def list_users(user: AdminUser, session: SessionDep) -> list[dict[str, Any]]:
    rows = session.scalars(select(User).order_by(User.created_at)).all()
    return [accounts.to_public(u) for u in rows]


@router.post("")
def create_user(body: UserCreate, user: AdminUser, session: SessionDep) -> dict[str, Any]:
    if body.role not in ("admin", "user", "pending"):
        raise ValidationError("Invalid role.")
    existing = session.scalars(select(User).where(User.email == body.email.lower())).first()
    if existing:
        raise ConflictError("A user with this email already exists.")
    new_user = User(
        name=body.name,
        email=body.email.lower(),
        password_hash=security.hash_password(body.password),
        role=body.role,
        status="active",
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return accounts.to_public(new_user)


@router.patch("/{user_id}")
def update_user(
    user_id: str, body: UserUpdate, admin: AdminUser, session: SessionDep
) -> dict[str, Any]:
    target = session.get(User, user_id)
    if not target:
        raise NotFoundError("User not found.")
    if body.name is not None:
        target.name = body.name
    if body.email is not None:
        email = body.email.strip().lower()
        clash = session.scalars(select(User).where(User.email == email, User.id != user_id)).first()
        if clash:
            raise ConflictError("A user with this email already exists.")
        target.email = email
    if body.password is not None:
        target.password_hash = security.hash_password(body.password)
    if body.role is not None:
        if body.role not in ("admin", "user", "pending"):
            raise ValidationError("Invalid role.")
        target.role = body.role
    if body.status is not None:
        if body.status not in ("active", "deactivated"):
            raise ValidationError("Invalid status.")
        target.status = body.status
    session.add(target)
    session.commit()
    session.refresh(target)
    return accounts.to_public(target)


@router.delete("/{user_id}")
def delete_user(user_id: str, admin: AdminUser, session: SessionDep) -> dict[str, bool]:
    target = session.get(User, user_id)
    if not target:
        raise NotFoundError("User not found.")
    if target.id == admin.id:
        raise ValidationError("You cannot delete your own account.")
    session.delete(target)
    session.commit()
    return {"ok": True}
