"""Compatibility bridge.

The chat HTTP surface now lives in ``jyotigpt.domains.chats``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... chats``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.chats.routes import router  # noqa: F401
