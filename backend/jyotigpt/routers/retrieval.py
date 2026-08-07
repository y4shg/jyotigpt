"""Compatibility bridge.

The retrieval HTTP surface now lives in ``jyotigpt.domains.retrieval``.
This module only exists so the namespace-package imports in ``main.py``
(``from jyotigpt.routers import ... retrieval``) and in ``middleware.py``
keep resolving; it will be removed by the restructure pass.
"""

from jyotigpt.domains.retrieval.routes import (
    router,
    SearchForm,
    process_web_search,
)  # noqa: F401
from jyotigpt.domains.retrieval.service import (  # noqa: F401
    BatchProcessFilesForm,
    ProcessFileForm,
    get_ef,
    get_rf,
    process_file,
    process_files_batch,
)
from jyotigpt.retrieval.utils import get_embedding_function  # noqa: F401
