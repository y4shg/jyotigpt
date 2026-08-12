"""Per-user preferences, memory entries, profile image and password.

Own design: a single JSON document per user (``user_settings`` table) holding
the Settings-modal preferences, merged over an allow-listed set of defaults.
Only known keys are persisted; each key's type/choices are validated on write
so the doc can never drift into a shape the UI cannot render.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.domain import accounts, security
from jyoti_api.domain.security import verify_password
from jyoti_api.errors import AuthError, NotFoundError, ValidationError
from jyoti_api.persistence.schema import MemoryEntry, Session as DbSession, User, UserSetting

_DEFAULTS: dict[str, Any] = {
    # general
    "theme": "dark",
    "language": "en",
    "notifications": True,
    "system_prompt": "",
    "keep_alive": "5m",
    "request_mode": "",
    # interface
    "landing_mode": "chat",  # default | chat
    "chat_direction": "auto",  # auto | ltr | rtl
    "widescreen": False,
    "chat_bubble_ui": True,
    "auto_title": True,
    "auto_tags": False,
    "stream_large_chunks": False,
    "response_auto_copy": False,
    "haptic_feedback": False,
    # audio
    "stt_engine": "default",  # default | browser
    "tts_engine": "default",  # default | browser
    "auto_playback": False,
    "playback_speed": 1.0,  # 0.5 - 2.0
    "voice": "default",
    "kokoro_dtype": "q8",
    # personalization
    "auto_memory": False,
}

_CHOICES: dict[str, tuple[type, tuple[Any, ...]]] = {
    "theme": (str, ("dark", "light")),
    "language": (str, ()),
    "notifications": (bool, ()),
    "system_prompt": (str, ()),
    "keep_alive": (str, ()),
    "request_mode": (str, ()),
    "landing_mode": (str, ("default", "chat")),
    "chat_direction": (str, ("auto", "ltr", "rtl")),
    "widescreen": (bool, ()),
    "chat_bubble_ui": (bool, ()),
    "auto_title": (bool, ()),
    "auto_tags": (bool, ()),
    "stream_large_chunks": (bool, ()),
    "response_auto_copy": (bool, ()),
    "haptic_feedback": (bool, ()),
    "stt_engine": (str, ("default", "browser")),
    "tts_engine": (str, ("default", "browser")),
    "auto_playback": (bool, ()),
    "playback_speed": (float, ()),
    "voice": (str, ()),
    "kokoro_dtype": (str, ("q8", "f16", "f32")),
    "auto_memory": (bool, ()),
}


def _coerce(key: str, value: Any) -> Any:
    """Validate one key against its declared type and choices."""
    if key not in _CHOICES:
        raise ValidationError(f"Unknown preference: {key}")
    kind, choices = _CHOICES[key]
    if kind is bool:
        if not isinstance(value, bool):
            raise ValidationError(f"Preference '{key}' must be a boolean.")
    elif kind is float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"Preference '{key}' must be a number.")
        if not 0.5 <= value <= 2.0:
            raise ValidationError(f"Preference '{key}' must be between 0.5 and 2.0.")
    elif kind is str:
        if not isinstance(value, str):
            raise ValidationError(f"Preference '{key}' must be a string.")
        if choices and value not in choices:
            raise ValidationError(f"Preference '{key}' has an invalid value.")
    return value


def get_user_settings(session: Session, user_id: str) -> dict[str, Any]:
    row = session.get(UserSetting, user_id)
    stored = dict(row.value) if row else {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in stored.items() if k in _DEFAULTS})
    return merged


def update_user_settings(
    session: Session, user_id: str, patch: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise ValidationError("Settings must be a JSON object.")
    row = session.get(UserSetting, user_id)
    merged = dict(_DEFAULTS)
    if row:
        merged.update({k: v for k, v in row.value.items() if k in _DEFAULTS})
    for key, value in patch.items():
        merged[key] = _coerce(key, value)
    if not row:
        row = UserSetting(user_id=user_id, value=merged)
        session.add(row)
    else:
        row.value = merged
    session.commit()
    session.refresh(row)
    return merged


# -------------------------------------------------------------------- memory


def list_memory(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user_id)
        .order_by(MemoryEntry.created_at.desc())
    ).all()
    return [_memory_dto(e) for e in rows]


def add_memory(session: Session, user_id: str, content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        raise ValidationError("Memory content cannot be empty.")
    entry = MemoryEntry(user_id=user_id, content=content)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _memory_dto(entry)


def update_memory(session: Session, user_id: str, entry_id: str, content: str) -> dict[str, Any]:
    entry = _owned_memory(session, user_id, entry_id)
    content = (content or "").strip()
    if not content:
        raise ValidationError("Memory content cannot be empty.")
    entry.content = content
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return _memory_dto(entry)


def delete_memory(session: Session, user_id: str, entry_id: str) -> None:
    entry = _owned_memory(session, user_id, entry_id)
    session.delete(entry)
    session.commit()


def _owned_memory(session: Session, user_id: str, entry_id: str) -> MemoryEntry:
    entry = session.get(MemoryEntry, entry_id)
    if not entry or entry.user_id != user_id:
        raise NotFoundError("Memory entry not found.")
    return entry


def _memory_dto(entry: MemoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "content": entry.content,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


# ------------------------------------------------------------------- profile


_DATA_URL_RE = re.compile(r"^data:image/(png|jpe?g|webp|gif);base64,([A-Za-z0-9+/=]+)$")
_MAX_AVATAR_BYTES = 300 * 1024


def set_avatar(session: Session, user: User, image_data: str) -> dict[str, Any]:
    """Store a base64 data-URL avatar on the user (mirrors the old UI)."""
    match = _DATA_URL_RE.match(image_data or "")
    if not match:
        raise ValidationError("Avatar must be a base64 data URL (png/jpeg/webp/gif).")
    payload = match.group(2)
    import base64

    try:
        raw = base64.b64decode(payload, validate=True)
    except Exception:
        raise ValidationError("Avatar data is not valid base64.")
    if not raw or len(raw) > _MAX_AVATAR_BYTES:
        raise ValidationError("Avatar must be smaller than 300 KB.")
    user.image = image_data
    session.add(user)
    session.commit()
    session.refresh(user)
    return accounts.to_public(user)


def change_password(
    session: Session,
    user: User,
    current_password: str,
    new_password: str,
    *,
    current_jti: str | None = None,
) -> None:
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.")
    if len(new_password or "") < 6:
        raise ValidationError("New password must be at least 6 characters long.")
    user.password_hash = security.hash_password(new_password)
    session.add(user)
    # Revoke every other session; the one that made this request stays valid.
    for db_session in session.scalars(
        select(DbSession).where(
            DbSession.user_id == user.id,
            DbSession.revoked.is_(False),
            DbSession.token_jti != (current_jti or ""),
        )
    ).all():
        db_session.revoked = True
        session.add(db_session)
    session.commit()
