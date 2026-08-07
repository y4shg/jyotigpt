"""Authentication utilities.

Provides password hashing, JWT issuance/decoding, API-key generation, HMAC
signature verification, and the FastAPI dependency callables used to resolve
and authorize the current request's user.
"""

import base64
import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Union

import bcrypt
import jwt
import requests
from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pytz import UTC

from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import (
    JYOTIGPT_SECRET_KEY,
    SRC_LOG_LEVELS,
    STATIC_DIR,
    TRUSTED_SIGNATURE_KEY,
)
from jyotigpt.models.users import Users

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])

SESSION_SECRET = JYOTIGPT_SECRET_KEY
ALGORITHM = "HS256"

bearer_security = HTTPBearer(auto_error=False)


##############
# Signature / licensing
##############


def verify_signature(payload: str, signature: str) -> bool:
    """Return True when ``signature`` is a valid HMAC-SHA256 of ``payload``.

    The comparison is constant-time to avoid leaking information through
    timing side channels.
    """
    try:
        digest = hmac.new(
            TRUSTED_SIGNATURE_KEY, payload.encode(), hashlib.sha256
        ).digest()
        expected = base64.b64encode(digest).decode()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def override_static(path: str, content: str) -> None:
    """Write base64-encoded ``content`` into the static dir under ``path``.

    ``path`` is rejected if it contains a separator or parent reference so a
    payload cannot escape the static directory.
    """
    if "/" in path or ".." in path:
        log.error(f"Invalid path: {path}")
        return

    file_path = os.path.join(STATIC_DIR, path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as handle:
        handle.write(base64.b64decode(content))


def get_license_data(app, key) -> bool:
    """Fetch license metadata for ``key`` and apply it onto ``app.state``.

    Returns True on a successful exchange. Recognized payload keys:
    ``resources`` (base64 static overrides), ``count`` (seat count),
    ``name`` (instance name), and ``metadata``.
    """
    if not key:
        return False

    try:
        res = requests.post(
            "https://api.jyotigpt.us.to/api/v1/license/",
            json={"key": key, "version": "1"},
            timeout=5,
        )
    except Exception as ex:
        log.exception(f"License: Uncaught Exception: {ex}")
        return False

    if not getattr(res, "ok", False):
        log.error(
            f"License: retrieval issue: {getattr(res, 'text', 'unknown error')}"
        )
        return False

    payload = getattr(res, "json", lambda: {})()
    for name, value in payload.items():
        if name == "resources":
            for resource_path, resource_content in value.items():
                override_static(resource_path, resource_content)
        elif name == "count":
            app.state.USER_COUNT = value
        elif name == "name":
            app.state.JYOTIGPT_NAME = value
        elif name == "metadata":
            app.state.LICENSE_METADATA = value
    return True


##############
# Passwords / tokens
##############


def verify_password(plain_password, hashed_password):
    """Verify a plaintext password against its bcrypt hash.

    Returns None (not False) when no hash is supplied, matching callers that
    distinguish "no credential on record" from "credential mismatch". A
    malformed stored hash is treated as a mismatch rather than an error.
    """
    if not hashed_password:
        return None
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8")
        )
    except (TypeError, ValueError):
        return False


def get_password_hash(password):
    """Return a bcrypt hash for ``password``.

    Passwords longer than 72 bytes are truncated to 72 bytes before hashing,
    bcrypt's effective input limit. Modern bcrypt rejects oversized secrets
    instead of truncating them, so the truncation is done here explicitly to
    keep the historical behavior.
    """
    return bcrypt.hashpw(
        password.encode("utf-8")[:72], bcrypt.gensalt()
    ).decode("utf-8")


def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """Encode ``data`` into a signed JWT, optionally with an expiry claim."""
    payload = data.copy()
    if expires_delta:
        payload["exp"] = datetime.now(UTC) + expires_delta
    return jwt.encode(payload, SESSION_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT, returning its claims or None if invalid."""
    try:
        return jwt.decode(token, SESSION_SECRET, algorithms=[ALGORITHM])
    except Exception:
        return None


def extract_token_from_auth_header(auth_header: str):
    """Strip the ``Bearer `` prefix off an Authorization header value."""
    return auth_header[len("Bearer ") :]


def create_api_key():
    """Mint a new API key of the form ``sk-<hex>``."""
    return f"sk-{uuid.uuid4().hex}"


def get_http_authorization_cred(auth_header: Optional[str]):
    """Parse an Authorization header into credentials, or None on failure."""
    if not auth_header:
        return None
    try:
        scheme, credentials = auth_header.split(" ")
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
    except Exception:
        return None


##############
# FastAPI dependencies
##############


def get_current_user(
    request: Request,
    background_tasks: BackgroundTasks,
    auth_token: HTTPAuthorizationCredentials = Depends(bearer_security),
):
    """Resolve the authenticated user for a request.

    Accepts either a bearer JWT or an ``sk-`` API key, from the Authorization
    header or the ``token`` cookie. API-key auth is gated by per-request and
    per-endpoint restriction settings.
    """
    token = auth_token.credentials if auth_token is not None else None
    if token is None:
        token = request.cookies.get("token")
    if token is None:
        raise HTTPException(status_code=403, detail="Not authenticated")

    if token.startswith("sk-"):
        if not request.state.enable_api_key:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED,
            )

        config = request.app.state.config
        if config.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS:
            allowed_paths = [
                path.strip()
                for path in str(config.API_KEY_ALLOWED_ENDPOINTS).split(",")
            ]
            request_path = request.url.path
            permitted = any(
                request_path == allowed or request_path.startswith(allowed + "/")
                for allowed in allowed_paths
            )
            if not permitted:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.API_KEY_NOT_ALLOWED,
                )

        return get_current_user_by_api_key(token)

    data = decode_token(token)
    if not (data is not None and "id" in data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    user = Users.get_user_by_id(data["id"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )

    # Bump last-active out of band so it never blocks the response.
    if background_tasks:
        background_tasks.add_task(Users.update_user_last_active_by_id, user.id)
    return user


def get_current_user_by_api_key(api_key: str):
    """Resolve a user directly from an API key, updating last-active."""
    user = Users.get_user_by_api_key(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )
    Users.update_user_last_active_by_id(user.id)
    return user


def get_verified_user(user=Depends(get_current_user)):
    """Require the current user to hold the ``user`` or ``admin`` role."""
    if user.role not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


def get_admin_user(user=Depends(get_current_user)):
    """Require the current user to hold the ``admin`` role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user
