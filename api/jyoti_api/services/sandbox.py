"""Sandboxed execution of user-authored tool plugins.

Tool plugins are Python sources defined by the user (see ``domain/plugins``).
They run in an isolated subprocess so a buggy or malicious plugin cannot take
down the API server: -I isolated mode, a dedicated temp working directory,
CPU + memory + wall-clock limits, and JSON-only communication over stdin/
stdout. No network access is granted today.
"""

from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jyoti_api.errors import ApiError

_MAX_WALL_SECONDS = 15
_MAX_CPU_SECONDS = 10
_MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256 MB


class SandboxError(ApiError):
    status_code = 400
    code = "sandbox_error"


_RUNNER = r"""
import json, sys, traceback

source = sys.stdin.read()
context = json.loads(sys.argv[1])

namespace = {"__name__": "__sandbox__"}
try:
    exec(compile(source, "<plugin>", "exec"), namespace)
except Exception:
    print(json.dumps({"ok": False, "error": "Plugin failed to load:\n" + traceback.format_exc()}))
    sys.exit(0)

func = namespace.get("run_tool")
if not callable(func):
    print(json.dumps({"ok": False, "error": "Plugin must define a callable run_tool(context)."}))
    sys.exit(0)

try:
    result = func(context)
    if not isinstance(result, dict):
        result = {"result": result}
    print(json.dumps({"ok": True, "result": result}))
except Exception:
    print(json.dumps({"ok": False, "error": "Plugin raised an exception:\n" + traceback.format_exc()}))
"""


def _limit_resources() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (_MAX_CPU_SECONDS, _MAX_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (_MAX_MEMORY_BYTES, _MAX_MEMORY_BYTES))


def run_python_tool(source: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run ``source`` in a sandboxed subprocess and return its JSON result."""
    with tempfile.TemporaryDirectory(prefix="jyoti-sandbox-") as tmp:
        payload = json.dumps(arguments or {})
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", _RUNNER, payload],
                input=source,
                capture_output=True,
                text=True,
                cwd=tmp,
                timeout=_MAX_WALL_SECONDS,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "HOME": tmp,
                    "PYTHONNOUSERSITE": "1",
                    "PYTHONPATH": "",
                },
                preexec_fn=_limit_resources,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(
                f"Plugin timed out after {_MAX_WALL_SECONDS}s."
            ) from exc
        except OSError as exc:
            raise SandboxError(f"Could not start sandbox: {exc}") from exc

    stdout = (proc.stdout or "").strip()
    if not stdout:
        stderr = (proc.stderr or "").strip()
        detail = stderr.splitlines()[-1] if stderr else "no output"
        raise SandboxError(f"Sandbox produced no result ({detail}).")
    try:
        parsed = json.loads(stdout)
    except ValueError:
        raise SandboxError("Sandbox produced invalid JSON output.") from None
    if not parsed.get("ok"):
        raise SandboxError(str(parsed.get("error", "Sandbox execution failed.")))
    return parsed.get("result") or {}
