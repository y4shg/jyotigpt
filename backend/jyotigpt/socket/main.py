"""Compatibility shim for the realtime engine.

All socket.io handling now lives in :mod:`jyotigpt.core.events`; this
module exists only so the established ``from jyotigpt.socket.main
import ...`` import paths keep resolving.  It will be removed by the
restructure pass.
"""

from jyotigpt.core.events import *  # noqa: F401,F403
