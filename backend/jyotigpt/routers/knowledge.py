"""Compatibility bridge.

The knowledge-base HTTP surface now lives in ``jyotigpt.domains.knowledge``.
This module only exists so the namespace-package import in ``main.py``
(``from jyotigpt.routers import ... knowledge``) keeps resolving; it will
be removed by the restructure pass.
"""

from jyotigpt.domains.knowledge.routes import (  # noqa: F401
    KnowledgeFileIdForm,
    KnowledgeFilesResponse,
    router,
)
