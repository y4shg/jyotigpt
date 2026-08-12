"""Shared FastAPI dependencies: database session, current user, role gates."""

from __future__ import annotations

from typing import Annotated

import jwt as pyjwt
from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.config import get_settings
from jyoti_api.domain import security
from jyoti_api.domain.accounts import ROLE_ADMIN, to_public
from jyoti_api.errors import AuthError, ForbiddenError
from jyoti_api.persistence.database import get_session
from jyoti_api.persistence.schema import ApiKey, Session as DbSession, User

SESSION_COOKIE = "jyoti_session"

SessionDep = Annotated[Session, Depends(get_session)]


def _resolve_api_key(session: Session, key: str) -> User:
    from datetime import datetime, timezone

    key_hash = security._hash_api_key(key)
    record = session.scalars(select(ApiKey).where(ApiKey.key_hash == key_hash)).first()
    if not record:
        raise AuthError("Invalid API key.")
    user = session.get(User, record.user_id)
    if not user or user.status == "deactivated":
        raise AuthError("This account has been deactivated.")
    record.last_used_at = datetime.now(timezone.utc)
    session.add(record)
    return user


def _session_record_valid(session: Session, jti: str | None) -> bool:
    """A JWT is only honored while its server-side session exists and is not revoked."""
    if not jti:
        return False
    record = session.scalars(
        select(DbSession).where(DbSession.token_jti == jti)
    ).first()
    return record is not None and not record.revoked


def _user_from_token(session: Session, token: str) -> User | None:
    try:
        payload = security.decode_token(token)
        if not _session_record_valid(session, payload.get("jti")):
            return None
        user = session.get(User, payload.get("sub"))
        if user and user.status != "deactivated":
            return user
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        pass
    return None


def get_current_user(
    session: SessionDep,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    jyoti_session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Resolve the authenticated user from cookie, Bearer token, or API key.

    An explicit Authorization header wins over the session cookie (a scripted
    caller must never be shadowed by a browser session cookie on the same
    client); the cookie is the default for the web app.
    """
    if authorization:
        if authorization.startswith("Bearer "):
            user = _user_from_token(session, authorization[7:].strip())
            if user:
                return user
        elif authorization.startswith("Key "):
            return _resolve_api_key(session, authorization[4:].strip())

    if jyoti_session:
        user = _user_from_token(session, jyoti_session)
        if user:
            return user

    # trusted reverse-proxy header auth (optional)
    settings = get_settings()
    if settings.auth_trusted_email_header:
        email = request.headers.get(settings.auth_trusted_email_header)
        if email:
            from jyoti_api.domain.accounts import trusted_header_user

            name = request.headers.get(settings.auth_trusted_name_header) if settings.auth_trusted_name_header else ""
            return trusted_header_user(session, email, name)

    raise AuthError("Not authenticated.")


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != ROLE_ADMIN:
        raise ForbiddenError("Administrator privileges required.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def public_user(user: User) -> dict:
    return to_public(user)
