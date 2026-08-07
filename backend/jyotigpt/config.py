"""Compatibility shim for the config layer.

All settings machinery now lives in :mod:`jyotigpt.core.settings`
(which also depends on :mod:`jyotigpt.core.environment` for the env
layer); this module exists only so the established ``from jyotigpt.config
import ...`` import paths keep resolving.  It will be removed by the
restructure pass.
"""

from jyotigpt.core.settings import *  # noqa: F401,F403
