"""Compatibility bridge.

The function plugin HTTP surface now lives in ``jyotigpt.domains.functions``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... functions``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.functions.routes import router  # noqa: F401
