"""Compatibility shim for the pipe engine.

All function-pipe handling now lives in :mod:`jyotigpt.core.pipes`;
this module exists only so the established ``from jyotigpt.functions
import ...`` import paths keep resolving.  It will be removed by the
restructure pass.
"""

from jyotigpt.core.pipes import *  # noqa: F401,F403
