"""Compatibility bridge.

The Ollama proxy HTTP surface now lives in ``jyotigpt.domains.ollama``.
This module only exists so the namespace-package import in ``main.py``
(``from jyotigpt.routers import ... ollama``) and the ``utils.chat`` /
``utils.models`` imports of ``generate_chat_completion`` /
``get_all_models`` keep resolving; it will be removed by the restructure
pass.
"""

from jyotigpt.domains.ollama.routes import (  # noqa: F401
    GenerateChatCompletionForm,
    generate_chat_completion,
    router,
)
from jyotigpt.domains.ollama.service import (  # noqa: F401
    get_all_models,
)
