"""Compatibility bridge.

The image generation HTTP surface now lives in ``jyotigpt.domains.images``.
This module only exists so the namespace-package import in ``main.py``
(``from jyotigpt.routers import ... images``) and the ``middleware.py``
import of ``GenerateImageForm``/``image_generations`` keep resolving; it
will be removed by the restructure pass.
"""

from jyotigpt.domains.images.routes import (  # noqa: F401
    GenerateImageForm,
    image_generations,
    router,
)
