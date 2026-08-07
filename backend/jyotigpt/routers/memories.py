"""Compatibility bridge.

The memories HTTP surface now lives in ``jyotigpt.domains.memories``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... memories``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.memories.routes import router  # noqa: F401
