"""Compatibility bridge.

The configuration HTTP surface now lives in ``jyotigpt.domains.config``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... configs``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.config.routes import router  # noqa: F401
