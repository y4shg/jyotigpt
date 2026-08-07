"""Compatibility bridge.

The OpenAI proxy HTTP surface now lives in ``jyotigpt.domains.openai``.
This module only exists so the namespace-package import in ``main.py``
(``from jyotigpt.routers import ... openai``) and the ``utils.chat`` /
``utils.models`` imports of ``generate_chat_completion`` /
``get_all_models`` keep resolving; it will be removed by the restructure
pass.
"""

from jyotigpt.domains.openai.routes import (  # noqa: F401
    generate_chat_completion,
    router,
)
from jyotigpt.domains.openai.service import (  # noqa: F401
    get_all_models,
    get_all_models_responses,
)
