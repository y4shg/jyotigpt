"""Compatibility bridge.

The pipelines admin surface now lives in ``jyotigpt.domains.pipelines``.
This module only exists so the namespace-package import in ``main.py``
(``from jyotigpt.routers import ... pipelines``) and the filter-middleware
imports from ``utils.chat`` / ``utils.middleware`` / ``routers.tasks``
keep resolving; it will be removed by the restructure pass.
"""

from jyotigpt.domains.pipelines.routes import router  # noqa: F401
from jyotigpt.domains.pipelines.service import (  # noqa: F401
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)
