"""Authentication endpoints: /api/v1/auth/*"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, EmailStr, Field

from jyoti_api.api.deps import SESSION_COOKIE, CurrentUser, SessionDep
from jyoti_api.config import get_settings
from jyoti_api.domain import accounts, security
from jyoti_api.errors import AuthError

logger = logging.getLogger("jyoti_api")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class SignInRequest(BaseModel):
    # plain string: sign-in identifiers are looked up, not validated (LDAP
    # usernames may not even be emails)
    email: str
    password: str
    ldap: bool = False


class SignUpRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str
    user: dict[str, Any]


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    secure = settings.app_env == "production"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
        max_age=30 * 24 * 3600,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post("/signin", response_model=TokenOut)
def sign_in(body: SignInRequest, session: SessionDep, response: Response) -> dict[str, Any]:
    settings = get_settings()
    if body.ldap and settings.enable_ldap:
        user = accounts.ldap_authenticate(session, body.email, body.password)
    else:
        user = accounts.authenticate(session, body.email, body.password)
    accounts.touch_user(session, user)
    token = accounts.create_session(session, user)
    _set_session_cookie(response, token)
    return {"token": token, "user": accounts.to_public(user)}


@router.post("/signup", response_model=TokenOut)
def sign_up(body: SignUpRequest, session: SessionDep, response: Response) -> dict[str, Any]:
    user = accounts.sign_up(session, body.name, body.email, body.password)
    token = accounts.create_session(session, user)
    _set_session_cookie(response, token)
    return {"token": token, "user": accounts.to_public(user)}


@router.post("/ldap/signin", response_model=TokenOut)
def ldap_sign_in(body: SignInRequest, session: SessionDep, response: Response) -> dict[str, Any]:
    settings = get_settings()
    if not settings.enable_ldap:
        raise AuthError("LDAP sign-in is not enabled.")
    user = accounts.ldap_authenticate(session, body.email, body.password)
    accounts.touch_user(session, user)
    token = accounts.create_session(session, user)
    _set_session_cookie(response, token)
    return {"token": token, "user": accounts.to_public(user)}


@router.get("/ldap/config")
def ldap_config(user: CurrentUser) -> dict[str, Any]:
    settings = get_settings()
    return {
        "enabled": settings.enable_ldap,
        "server_host": settings.ldap_server_host,
        "port": settings.ldap_server_port,
        "search_base": settings.ldap_search_base,
        "use_tls": settings.ldap_use_tls,
    }


@router.get("/session")
def current_session(user: CurrentUser) -> dict[str, Any]:
    return {"user": accounts.to_public(user)}


@router.post("/signout")
def sign_out(
    session: SessionDep,
    user: CurrentUser,
    response: Response,
    jyoti_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, bool]:
    _clear_session_cookie(response)
    if jyoti_session:
        # The cookie is cleared regardless; revocation only matters when the
        # token is still decodable (a stale or corrupt cookie has no session
        # row to revoke, so sign-out must still succeed).
        try:
            payload = security.decode_token(jyoti_session)
            accounts.revoke_session(session, payload.get("jti"))
        except Exception:  # pragma: no cover - defensive
            logger.debug("signout: could not revoke token", exc_info=True)
    return {"ok": True}
