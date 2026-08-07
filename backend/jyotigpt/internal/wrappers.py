"""Legacy Peewee connection plumbing.

The Peewee layer exists only to replay the pre-SQLAlchemy schema migrations
(``internal/migrations``) against an existing database before SQLAlchemy takes
ownership of the schema. This module provides a Peewee connection that handles
Postgres reconnects, plus per-request connection-state isolation via context
variables.
"""

import logging
from contextvars import ContextVar

from jyotigpt.env import SRC_LOG_LEVELS
from peewee import InterfaceError, OperationalError, PostgresqlDatabase, SqliteDatabase
from playhouse.db_url import connect, parse
from playhouse.shortcuts import ReconnectMixin

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

# Default per-context connection state; copied so mutations never leak
# between contexts.
_DB_STATE_DEFAULTS = {
    "closed": None,
    "conn": None,
    "ctx": None,
    "transactions": None,
}
_db_state: ContextVar = ContextVar("db_state", default=_DB_STATE_DEFAULTS.copy())


class PeeweeConnectionState:
    """Attribute proxy that stores connection state in a ``ContextVar``.

    Peewee expects a mutable per-thread state object; this class redirects
    reads/writes to the context-local dict so concurrent tasks each keep their
    own connection lifecycle.
    """

    def __init__(self, **kwargs):
        super().__setattr__("_state", _db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        return self._state.get()[name]


class CustomReconnectMixin(ReconnectMixin):
    """Reconnect on the transient Postgres/Peewee error signatures."""

    reconnect_errors = (
        (OperationalError, "termin"),
        (InterfaceError, "closed"),
    )


class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    """A Postgres database that transparently reconnects after drops."""


def register_connection(db_url):
    """Build a Peewee connection for ``db_url``, tuned per backend.

    SQLite and Postgres both get autoconnect (managed by Peewee) and
    connection reuse; Postgres additionally uses the reconnect mixin. Any
    other backend raises ``ValueError``.
    """
    db = connect(db_url, unquote_password=True)
    if isinstance(db, PostgresqlDatabase):
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to PostgreSQL database")

        # Rebuild as a reconnecting database and open it immediately.
        connection = parse(db_url, unquote_password=True)
        db = ReconnectingPostgresqlDatabase(**connection)
        db.connect(reuse_if_open=True)
    elif isinstance(db, SqliteDatabase):
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to SQLite database")
    else:
        raise ValueError("Unsupported database connection")
    return db
