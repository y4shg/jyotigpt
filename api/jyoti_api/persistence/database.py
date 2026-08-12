"""Database engine, session factory and declarative base.

SQLite is the default store (under DATA_DIR); set DATABASE_URL to a
PostgreSQL/other URL to override. Tables are created by Alembic migrations;
on a fresh boot the app also runs `Base.metadata.create_all` so the server
works even before migrations are applied.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from jyoti_api.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_url = _settings.resolved_database_url
_is_sqlite = _url.startswith("sqlite")

_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_url, **_engine_kwargs)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create tables if the database is empty (migrations are authoritative)."""
    from jyoti_api.persistence import schema  # noqa: F401  (register tables)

    Base.metadata.create_all(bind=engine)
