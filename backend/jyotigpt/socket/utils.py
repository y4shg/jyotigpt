"""Compatibility shim for the realtime primitives.

The distributed lock and pool now live in :mod:`jyotigpt.core.events`;
this module exists only so the established ``from jyotigpt.socket.utils
import ...`` import paths keep resolving.  It will be removed by the
restructure pass.
"""

from jyotigpt.core.events import *  # noqa: F401,F403
