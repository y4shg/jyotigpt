"""Compatibility bridge.

The audio HTTP surface now lives in ``jyotigpt.domains.audio``.
This module only exists so the namespace package import in ``main.py``
(``from jyotigpt.routers import ... audio``) keeps resolving; it will be
removed by the restructure pass. Note that ``routers.files`` imports
``transcribe`` from here, so it is re-exported from the service.
"""

from jyotigpt.domains.audio.routes import router  # noqa: F401
from jyotigpt.domains.audio.service import transcribe  # noqa: F401
