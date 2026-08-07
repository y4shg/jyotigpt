"""Dynamic loading of user-supplied tool and function plugins.

Plugins are stored as Python source in the database. This module extracts
their docstring frontmatter, rewrites bare imports to the ``jyotigpt``
namespace, installs any declared pip requirements, and executes the source
into a fresh module to instantiate the expected plugin class.
"""

import logging
import os
import re
import subprocess
import sys
import tempfile
import types

from jyotigpt.env import PIP_OPTIONS, PIP_PACKAGE_INDEX_OPTIONS, SRC_LOG_LEVELS
from jyotigpt.models.functions import Functions
from jyotigpt.models.tools import Tools

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# Bare import prefixes rewritten to the packaged namespace when loading plugins.
_IMPORT_REWRITES = {
    "from utils": "from jyotigpt.utils",
    "from apps": "from jyotigpt.apps",
    "from main": "from jyotigpt.main",
    "from config": "from jyotigpt.config",
}

_FRONTMATTER_LINE = re.compile(r"^\s*([a-z_]+):\s*(.*)\s*$", re.IGNORECASE)
_FRONTMATTER_DELIMITER = '"""'


def extract_frontmatter(content):
    """Parse the leading triple-quoted docstring into a ``key: value`` dict.

    Returns an empty dict when the content does not open with a ``\"\"\"``
    line or when parsing fails.
    """
    frontmatter = {}

    try:
        lines = content.splitlines()
        if len(lines) < 1 or lines[0].strip() != _FRONTMATTER_DELIMITER:
            return {}

        for line in lines[1:]:
            if _FRONTMATTER_DELIMITER in line:
                break
            match = _FRONTMATTER_LINE.match(line)
            if match:
                key, value = match.groups()
                frontmatter[key.strip()] = value.strip()
    except Exception as e:
        log.exception(f"Failed to extract frontmatter: {e}")
        return {}

    return frontmatter


def replace_imports(content):
    """Rewrite legacy bare import statements to the ``jyotigpt`` namespace."""
    for old, new in _IMPORT_REWRITES.items():
        content = content.replace(old, new)
    return content


def _execute_plugin_source(module_name, content):
    """Execute plugin ``content`` inside a new module and register it.

    A temporary file backs ``__file__`` so plugin code that inspects its own
    path behaves normally. The temp file is always removed; on any execution
    error the partially-registered module is unregistered before re-raising.
    """
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module

    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    try:
        with open(temp_file.name, "w", encoding="utf-8") as f:
            f.write(content)
        module.__dict__["__file__"] = temp_file.name

        exec(content, module.__dict__)
        log.info(f"Loaded module: {module.__name__}")
        return module
    except Exception:
        del sys.modules[module_name]
        raise
    finally:
        os.unlink(temp_file.name)


def load_tool_module_by_id(tool_id, content=None):
    """Load a toolkit plugin and return ``(Tools instance, frontmatter)``.

    When ``content`` is omitted it is fetched from the database, its imports
    are rewritten, and the rewritten source is persisted back. When supplied
    directly, declared frontmatter requirements are installed first.
    """
    if content is None:
        tool = Tools.get_tool_by_id(tool_id)
        if not tool:
            raise Exception(f"Toolkit not found: {tool_id}")
        content = replace_imports(tool.content)
        Tools.update_tool_by_id(tool_id, {"content": content})
    else:
        frontmatter = extract_frontmatter(content)
        install_frontmatter_requirements(frontmatter.get("requirements", ""))

    module_name = f"tool_{tool_id}"
    try:
        module = _execute_plugin_source(module_name, content)
    except Exception as e:
        log.error(f"Error loading module: {tool_id}: {e}")
        raise e

    frontmatter = extract_frontmatter(content)
    if hasattr(module, "Tools"):
        return module.Tools(), frontmatter
    raise Exception("No Tools class found in the module")


def load_function_module_by_id(function_id, content=None):
    """Load a function plugin and return ``(instance, type, frontmatter)``.

    The plugin type is one of ``"pipe"``, ``"filter"``, or ``"action"``,
    chosen from the class the module exposes. On load failure the function is
    marked inactive in the database before the error propagates.
    """
    if content is None:
        function = Functions.get_function_by_id(function_id)
        if not function:
            raise Exception(f"Function not found: {function_id}")
        content = replace_imports(function.content)
        Functions.update_function_by_id(function_id, {"content": content})
    else:
        frontmatter = extract_frontmatter(content)
        install_frontmatter_requirements(frontmatter.get("requirements", ""))

    module_name = f"function_{function_id}"
    try:
        module = _execute_plugin_source(module_name, content)
    except Exception as e:
        log.error(f"Error loading module: {function_id}: {e}")
        Functions.update_function_by_id(function_id, {"is_active": False})
        raise e

    frontmatter = extract_frontmatter(content)
    if hasattr(module, "Pipe"):
        return module.Pipe(), "pipe", frontmatter
    if hasattr(module, "Filter"):
        return module.Filter(), "filter", frontmatter
    if hasattr(module, "Action"):
        return module.Action(), "action", frontmatter
    raise Exception("No Function class found in the module")


def install_frontmatter_requirements(requirements: str):
    """Pip-install the comma-separated requirements declared in frontmatter."""
    if not requirements:
        log.info("No requirements found in frontmatter.")
        return

    req_list = [req.strip() for req in requirements.split(",")]
    try:
        log.info(f"Installing requirements: {' '.join(req_list)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"]
            + PIP_OPTIONS
            + req_list
            + PIP_PACKAGE_INDEX_OPTIONS
        )
    except Exception as e:
        log.error(f"Error installing packages: {' '.join(req_list)}")
        raise e
