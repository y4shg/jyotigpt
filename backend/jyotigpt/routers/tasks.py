"""Compatibility bridge.

The task-generation surface now lives in ``jyotigpt.domains.tasks``.
This module only exists so the namespace-package import in ``main.py``
(``from jyotigpt.routers import ... tasks``) and the task imports from
``utils.middleware`` keep resolving; it will be removed by the restructure
pass.
"""

from jyotigpt.domains.tasks.routes import (  # noqa: F401
    generate_chat_tags,
    generate_image_prompt,
    generate_queries,
    generate_title,
    router,
)
