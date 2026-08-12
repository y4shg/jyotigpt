"""Password hashing, JWT sessions and API-key handling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from jyoti_api.config import get_settings


def _parse_ttl(value: str) -> timedelta:
    """Parse a timedelta string like '30d', '12h', '45m', or plain seconds."""
    value = value.strip().lower()
    unit_map = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds", "w": "weeks"}
    if value.isdigit():
        return timedelta(seconds=int(value))
    for suffix, unit in unit_map.items():
        if value.endswith(suffix) and value[:-1].isdigit():
            return timedelta(**{unit: int(value[:-1])})
    raise ValueError(f"Unrecognized TTL string: {value!r}")


def _password_digest(password: str) -> bytes:
    """SHA-256 pre-hash so bcrypt's 72-byte limit never silently truncates."""
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_digest(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_digest(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


# --------------------------------------------------------------------- JWT


def create_access_token(subject: str, jti: str, expires_in: str | None = None) -> str:
    settings = get_settings()
    ttl = _parse_ttl(expires_in or settings.jwt_expires_in)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "jti": jti,
        "iat": now,
        "exp": now + ttl,
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


# ------------------------------------------------------------------ API keys


def generate_api_key(name: str = "") -> tuple[str, str, str]:
    """Return (prefix, plaintext_key, sha256_hash). Only the hash is stored."""
    key = "jyoti-" + secrets.token_urlsafe(40)
    prefix = key[:11]
    return prefix, key, _hash_api_key(key)


def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    return hmac.compare_digest(_hash_api_key(key), key_hash)
