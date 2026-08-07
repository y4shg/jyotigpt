"""Compatibility bridge.

The file HTTP surface now lives in ``jyotigpt.domains.files``. This module
only exists so the namespace-package imports in ``main.py`` (``from
jyotigpt.routers import ... files``), in ``images.py`` (``from
jyotigpt.routers.files import upload_file``), and in the external pipeline
keep resolving; it will be removed by the restructure pass.
"""

from jyotigpt.domains.files.routes import router  # noqa: F401
from jyotigpt.domains.files.service import (  # noqa: F401
    has_access_to_file,
    upload_file,
)
