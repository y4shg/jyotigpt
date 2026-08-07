"""Compatibility bridge.

The folder HTTP surface now lives in ``jyotigpt.domains.folders``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... folders``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.folders.routes import router  # noqa: F401
