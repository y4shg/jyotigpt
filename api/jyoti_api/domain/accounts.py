"""User accounts: sign-up, sign-in, LDAP, trusted-header auth, serialization."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyoti_api.config import get_settings
from jyoti_api.domain import security
from jyoti_api.errors import AuthError, ValidationError
from jyoti_api.persistence.schema import ApiKey, Session as DbSession, User

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_PENDING = "pending"

STATUS_ACTIVE = "active"
STATUS_DEACTIVATED = "deactivated"


def to_public(user: User, include_keys: bool = False) -> dict[str, Any]:
    """Serialize a user without secrets."""
    payload = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "image": user.image,
        "about": user.about,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
    }
    if include_keys:
        payload["api_keys"] = [
            {"id": k.id, "name": k.name, "prefix": k.prefix, "created_at": k.created_at.isoformat()}
            for k in user.api_keys
        ]
    return payload


def touch_user(session: Session, user: User) -> None:
    user.last_active_at = datetime.now(timezone.utc)
    session.add(user)


def bootstrap_admin(session: Session) -> User | None:
    """Create the default admin on first boot when no users exist."""
    settings = get_settings()
    existing = session.scalars(select(User)).first()
    if existing:
        return None
    if not settings.admin_email:
        return None
    admin = User(
        name="Admin",
        email=settings.admin_email,
        password_hash=security.hash_password(settings.admin_password),
        role=ROLE_ADMIN,
        status=STATUS_ACTIVE,
    )
    session.add(admin)
    session.commit()
    return admin


def _validate_signup(name: str, email: str, password: str) -> None:
    if not name or not name.strip():
        raise ValidationError("Name cannot be empty.")
    if not _EMAIL_RE.match(email or ""):
        raise ValidationError("Enter a valid email address.")
    if len(password or "") < 6:
        raise ValidationError("Password must be at least 6 characters long.")


def sign_up(session: Session, name: str, email: str, password: str) -> User:
    settings = get_settings()
    if not settings.enable_signup:
        raise ValidationError("Sign-up is disabled by the administrator.")
    _validate_signup(name, email, password)
    email = email.strip().lower()
    existing = session.scalars(select(User).where(User.email == email)).first()
    if existing:
        raise ValidationError("An account with this email already exists.")
    role = settings.default_user_role if settings.default_user_role in (
        ROLE_ADMIN, ROLE_USER, ROLE_PENDING
    ) else ROLE_PENDING
    user = User(
        name=name.strip(),
        email=email,
        password_hash=security.hash_password(password),
        role=role,
        status=STATUS_ACTIVE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> User:
    email = (email or "").strip().lower()
    user = session.scalars(select(User).where(User.email == email)).first()
    if not user or not user.password_hash or not security.verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")
    if user.status == STATUS_DEACTIVATED:
        raise AuthError("This account has been deactivated.")
    return user


# --------------------------------------------------------------------- LDAP


def ldap_authenticate(session: Session, email: str, password: str) -> User:
    """Bind against the configured LDAP server; create/refresh the local user."""
    settings = get_settings()
    if not settings.enable_ldap:
        raise AuthError("LDAP sign-in is not enabled.")
    if not email or not password:
        raise AuthError("LDAP credentials are required.")

    import ldap3

    server = ldap3.Server(
        settings.ldap_server_host,
        port=settings.ldap_server_port,
        use_ssl=settings.ldap_use_tls,
        connect_timeout=10,
    )
    bind_dn, bind_password = settings.ldap_app_dn, settings.ldap_app_password
    try:
        conn = ldap3.Connection(server, user=bind_dn or None, password=bind_password or None)
        if not conn.bind():
            raise AuthError("LDAP server rejected the service bind.")
        search_filter = settings.ldap_search_filter.replace("{{mail}}", email)
        conn.search(
            settings.ldap_search_base,
            search_filter,
            attributes=[settings.ldap_attribute_for_mail, settings.ldap_attribute_for_username],
        )
        if not conn.entries:
            raise AuthError("No LDAP account matches this email.")
        entry = conn.entries[0]
        user_dn = entry.entry_dn
        conn.unbind()

        user_conn = ldap3.Connection(server, user=user_dn, password=password, connect_timeout=10)
        if not user_conn.bind():
            raise AuthError("LDAP credentials rejected.")
        user_conn.unbind()

        mail = _ldap_attr(entry, settings.ldap_attribute_for_mail) or email
        username = _ldap_attr(entry, settings.ldap_attribute_for_username) or mail
    except AuthError:
        raise
    except Exception as exc:  # pragma: no cover - ldap transport errors
        raise AuthError(f"LDAP lookup failed: {exc}") from exc

    user = session.scalars(select(User).where(User.email == mail.lower())).first()
    if user:
        if user.status == STATUS_DEACTIVATED:
            raise AuthError("This account has been deactivated.")
        user.ldap_dn = user_dn
        if not user.password_hash:
            user.password_hash = security.hash_password(secrets_placeholder())
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    role = settings.default_user_role if settings.default_user_role in (
        ROLE_ADMIN, ROLE_USER, ROLE_PENDING
    ) else ROLE_PENDING
    user = User(
        name=username,
        email=mail.lower(),
        password_hash=security.hash_password(secrets_placeholder()),
        role=role,
        status=STATUS_ACTIVE,
        ldap_dn=user_dn,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _ldap_attr(entry: Any, attr: str) -> str:
    try:
        value = entry[attr].value
        return value.decode() if isinstance(value, bytes) else str(value)
    except Exception:
        return ""


def secrets_placeholder() -> str:
    """Random unusable password for LDAP-only accounts (no local login)."""
    import secrets

    return "!" + secrets.token_urlsafe(32)


# --------------------------------------------------------- trusted headers


def trusted_header_user(session: Session, email: str, name: str) -> User:
    """Resolve the user claimed by the upstream reverse proxy."""
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise AuthError("Trusted-header auth requires a valid email.")
    user = session.scalars(select(User).where(User.email == email)).first()
    if user:
        if user.status == STATUS_DEACTIVATED:
            raise AuthError("This account has been deactivated.")
        if name and user.name != name:
            user.name = name
            session.add(user)
        session.commit()
        session.refresh(user)
        return user
    role = get_settings().default_user_role if get_settings().default_user_role in (
        ROLE_ADMIN, ROLE_USER, ROLE_PENDING
    ) else ROLE_PENDING
    user = User(
        name=name or email.split("@")[0],
        email=email,
        password_hash=security.hash_password(secrets_placeholder()),
        role=role,
        status=STATUS_ACTIVE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------- sessions


def create_session(session: Session, user: User) -> str:
    import uuid

    jti = uuid.uuid4().hex
    token = security.create_access_token(subject=user.id, jti=jti)
    db_session = DbSession(
        user_id=user.id, token_jti=jti, expires_at=_jwt_expiry(token)
    )
    session.add(db_session)
    session.commit()
    return token


def revoke_session(session: Session, jti: str | None) -> None:
    if not jti:
        return
    db_session = session.scalars(
        select(DbSession).where(DbSession.token_jti == jti)
    ).first()
    if db_session:
        db_session.revoked = True
        session.add(db_session)
        session.commit()


def _jwt_expiry(token: str) -> datetime:
    payload = security.decode_token(token)
    return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
