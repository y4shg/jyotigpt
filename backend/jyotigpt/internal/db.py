"""Database engine, session, and migration bootstrap.

Replays the legacy Peewee migrations (``internal/migrations``) at import time
so pre-existing databases from the older ORM are upgraded before SQLAlchemy
owns the schema. Provides the declarative ``Base`` all model classes extend,
the scoped ``Session``, and a ``get_db`` context manager for dependency
injection.
"""

import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from jyotigpt.env import (
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
    DATABASE_SCHEMA,
    DATABASE_URL,
    JYOTIGPT_DIR,
    SRC_LOG_LEVELS,
)
from jyotigpt.internal.wrappers import register_connection
from peewee_migrate import Router
from sqlalchemy import Dialect, MetaData, create_engine, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(types.TypeDecorator):
    """A JSON column serialized into a text column.

    Values are ``json.dumps``-ed on the way in and ``json.loads``-ed on the
    way out; ``NULL`` round-trips as ``None``.
    """

    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[_T], dialect: Dialect) -> Any:
        if value is not None:
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    # Peewee-era serialization hooks, retained for migration tooling.
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


def handle_peewee_migration(DATABASE_URL):
    """Replay the legacy Peewee migrations against the target database.

    Must run before SQLAlchemy metadata is created so the schema is already
    at the current revision. Mirrors the historical behavior of not
    pre-binding ``db``: a connection failure therefore surfaces through the
    ``finally`` guard rather than the original exception.
    """
    # db = None
    try:
        # The legacy driver only understands the "postgres://" scheme.
        db = register_connection(DATABASE_URL.replace("postgresql://", "postgres://"))
        migrate_dir = JYOTIGPT_DIR / "internal" / "migrations"
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
        db.close()

    except Exception as e:
        log.error(f"Failed to initialize the database connection: {e}")
        raise
    finally:
        # Properly closing the database connection
        if db and not db.is_closed():
            db.close()

        # Assert if db connection has been closed
        assert db.is_closed(), "Database connection is still open."


handle_peewee_migration(DATABASE_URL)


SQLALCHEMY_DATABASE_URL = DATABASE_URL
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    if DATABASE_POOL_SIZE > 0:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=DATABASE_POOL_SIZE,
            max_overflow=DATABASE_POOL_MAX_OVERFLOW,
            pool_timeout=DATABASE_POOL_TIMEOUT,
            pool_recycle=DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=QueuePool,
        )
    else:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool
        )


SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
metadata_obj = MetaData(schema=DATABASE_SCHEMA)
Base = declarative_base(metadata=metadata_obj)
Session = scoped_session(SessionLocal)


def get_session():
    """Yield a fresh session, closing it when the caller is done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)
