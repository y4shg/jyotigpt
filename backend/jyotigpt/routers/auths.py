"""Compatibility bridge.

The auth HTTP surface now lives in ``jyotigpt.domains.auths``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... auths``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.auths.routes import router  # noqa: F401
