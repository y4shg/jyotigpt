"""Compatibility bridge.

The channel HTTP surface now lives in ``jyotigpt.domains.channels``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... channels``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.channels.routes import router  # noqa: F401
