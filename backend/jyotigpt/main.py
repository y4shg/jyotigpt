"""Application entry point: build the ASGI app via the bootstrap factory.

Everything that used to live here — state wiring, middleware, router
includes, the platform endpoints, static mounts — now lives in
:mod:`jyotigpt.bootstrap`, which carries the same process-level side
effects (safe mode, stdout logging, the ASCII banner) that this module
used to.  Uvicorn is invoked with the ``jyotigpt.main:app`` import
string, so all this module needs to expose is ``app``.
"""

from jyotigpt.bootstrap import create_app

app = create_app()
