"""Compatibility bridge.

The model catalogue HTTP surface now lives in ``jyotigpt.domains.models``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... models``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.models.routes import router  # noqa: F401
