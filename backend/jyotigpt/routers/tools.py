"""Compatibility bridge.

The tool plugin HTTP surface now lives in ``jyotigpt.domains.tools``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... tools``) keeps resolving; it will be
removed by the restructure pass.
"""

from jyotigpt.domains.tools.routes import router  # noqa: F401
