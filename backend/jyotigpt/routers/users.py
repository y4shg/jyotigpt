"""Compatibility bridge.

The user account HTTP surface now lives in ``jyotigpt.domains.users``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... users``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.users.routes import router  # noqa: F401
