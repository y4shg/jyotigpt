"""Compatibility shim for the environment layer.

All runtime environment handling now lives in
:mod:`jyotigpt.core.environment`; this module exists only so the
established ``from jyotigpt.env import ...`` import paths keep
resolving.  It will be removed by the restructure pass.
"""

from jyotigpt.core.environment import *  # noqa: F401,F403
