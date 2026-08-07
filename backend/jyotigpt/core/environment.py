"""Runtime environment and process configuration.

This module is the single place where the process reads its surroundings:
filesystem anchors, deployment mode, compute device selection, logging
levels, data/storage paths, database connectivity, security secrets and
feature toggles.

Everything here is derived from environment variables (with a ``.env``
file consulted first) and module-level constants.  It must stay import
order-independent from the rest of the package: nothing below imports
from ``jyotigpt.core.settings`` or the persistence layer, so that any
subsystem can safely pull its environment values early.

The public names defined here (all UPPER_CASE) form the environment
contract consumed across the package.  The legacy ``jyotigpt.env``
module re-exports them for backwards compatibility.
"""

import importlib.metadata
import json
import logging
import os
import pkgutil
import shutil
import sys
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

from jyotigpt.constants import ERROR_MESSAGES

####################################
# Filesystem anchors
####################################

#: The ``jyotigpt`` package directory.
JYOTIGPT_DIR = Path(__file__).resolve().parent.parent
print(JYOTIGPT_DIR)

#: The ``backend/`` directory that contains the package.
BACKEND_DIR = JYOTIGPT_DIR.parent
BASE_DIR = BACKEND_DIR.parent  # the repository root (contains backend/)

print(BACKEND_DIR)
print(BASE_DIR)


def _load_dotenv() -> None:
    """Load ``.env`` from the repository root if ``python-dotenv`` is present."""
    try:
        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(str(BASE_DIR / ".env")))
    except ImportError:
        print("dotenv not installed, skipping...")


_load_dotenv()


def _flag(name: str, default: str) -> bool:
    """Read ``name`` as a boolean env var, honouring a string default."""
    return os.environ.get(name, default).lower() == "true"


def _integer(name: str, default: int) -> int:
    """Read ``name`` as an int env var, falling back to ``default``."""
    raw = os.environ.get(name, "")
    if raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _timeout_value(raw, fallback: int):
    """Normalize a raw env string as a timeout: empty means None (no timeout)."""
    if raw == "":
        return None
    try:
        return int(raw)
    except Exception:
        return fallback


####################################
# Deployment / runtime mode
####################################

#: ``dev``, ``test`` or ``prod`` — gates docs exposure and a few prod-only rewrites.
ENV = os.environ.get("ENV", "dev")

#: True when launched through the ``jyotigpt`` CLI (``__init__.py``).
FROM_INIT_PY = _flag("FROM_INIT_PY", "False")

#: True when running inside the container image.
DOCKER = _flag("DOCKER", "False")

#: True when the process should boot with third-party functions deactivated.
SAFE_MODE = _flag("SAFE_MODE", "false")

#: When True, trust authenticated reverse-proxy identity headers.
ENABLE_FORWARD_USER_INFO_HEADERS = _flag("ENABLE_FORWARD_USER_INFO_HEADERS", "False")

JYOTIGPT_BUILD_HASH = os.environ.get("JYOTIGPT_BUILD_HASH", "dev-build")

####################################
# Compute device
####################################

USE_CUDA = "true" if DOCKER else os.environ.get("USE_CUDA_DOCKER", "false")

if USE_CUDA.lower() == "true":
    try:
        import torch

        assert torch.cuda.is_available(), "CUDA not available"
        DEVICE_TYPE = "cuda"
    except Exception as e:
        cuda_error = (
            "Error when testing CUDA but USE_CUDA_DOCKER is true. "
            f"Resetting USE_CUDA_DOCKER to false: {e}"
        )
        os.environ["USE_CUDA_DOCKER"] = "false"
        USE_CUDA = "false"
        DEVICE_TYPE = "cpu"
else:
    DEVICE_TYPE = "cpu"

try:
    import torch

    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        DEVICE_TYPE = "mps"
except Exception:
    pass

####################################
# Logging
####################################

GLOBAL_LOG_LEVEL = os.environ.get("GLOBAL_LOG_LEVEL", "").upper()
if GLOBAL_LOG_LEVEL in logging.getLevelNamesMapping():
    logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL, force=True)
else:
    GLOBAL_LOG_LEVEL = "INFO"

log = logging.getLogger(__name__)
log.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")

if "cuda_error" in locals():
    log.exception(cuda_error)
    del cuda_error

#: Per-subsystem level overrides; each maps to ``<SOURCE>_LOG_LEVEL``.
_LOG_SOURCES = [
    "AUDIO",
    "COMFYUI",
    "CONFIG",
    "DB",
    "IMAGES",
    "MAIN",
    "MODELS",
    "OLLAMA",
    "OPENAI",
    "RAG",
    "WEBHOOK",
    "SOCKET",
    "OAUTH",
]

SRC_LOG_LEVELS = {}

for source in _LOG_SOURCES:
    log_env_var = source + "_LOG_LEVEL"
    SRC_LOG_LEVELS[source] = os.environ.get(log_env_var, "").upper()
    if SRC_LOG_LEVELS[source] not in logging.getLevelNamesMapping():
        SRC_LOG_LEVELS[source] = GLOBAL_LOG_LEVEL
    log.info(f"{log_env_var}: {SRC_LOG_LEVELS[source]}")

log.setLevel(SRC_LOG_LEVELS["CONFIG"])

####################################
# Branding / release metadata
####################################

JYOTIGPT_NAME = os.environ.get("JYOTIGPT_NAME", "JyotiGPT")
if JYOTIGPT_NAME != "JyotiGPT":
    JYOTIGPT_NAME += " (JyotiGPT)"

JYOTIGPT_FAVICON_URL = "https://jyotigpt.us.to/favicon.png"

TRUSTED_SIGNATURE_KEY = os.environ.get("TRUSTED_SIGNATURE_KEY", "")

if FROM_INIT_PY:
    PACKAGE_DATA = {"version": importlib.metadata.version("jyotigpt")}
else:
    try:
        PACKAGE_DATA = json.loads((BASE_DIR / "package.json").read_text())
    except Exception:
        PACKAGE_DATA = {"version": "0.0.0"}

VERSION = PACKAGE_DATA["version"]


def _parse_changelog_section(section):
    """Convert one ``<ul>`` of changelog items into a list of item dicts."""
    items = []
    for li in section.find_all("li"):
        raw_html = str(li)
        text = li.get_text(separator=" ", strip=True)

        parts = text.split(": ", 1)
        title = parts[0].strip() if len(parts) > 1 else ""
        content = parts[1].strip() if len(parts) > 1 else text

        items.append({"title": title, "content": content, "raw": raw_html})
    return items


def _load_changelog() -> dict:
    """Parse ``CHANGELOG.md`` into ``{version: {"date": ..., <section>: [...]}}``."""
    try:
        changelog_path = BASE_DIR / "CHANGELOG.md"
        with open(str(changelog_path.absolute()), "r", encoding="utf8") as file:
            changelog_content = file.read()
    except Exception:
        changelog_content = (pkgutil.get_data("jyotigpt", "CHANGELOG.md") or b"").decode()

    html_content = markdown.markdown(changelog_content)
    soup = BeautifulSoup(html_content, "html.parser")

    changelog_json = {}
    for version in soup.find_all("h2"):
        version_text = version.get_text().strip()
        version_number = version_text.split(" - ")[0][1:-1]  # strip the brackets
        date = version_text.split(" - ")[1]

        version_data = {"date": date}

        current = version.find_next_sibling()
        while current and current.name != "h2":
            if current.name == "h3":
                section_title = current.get_text().lower()  # e.g. "added", "fixed"
                section_items = _parse_changelog_section(current.find_next_sibling("ul"))
                version_data[section_title] = section_items
            current = current.find_next_sibling()

        changelog_json[version_number] = version_data

    return changelog_json


CHANGELOG = _load_changelog()

####################################
# Data / storage paths
####################################

DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data")).resolve()

if FROM_INIT_PY:
    NEW_DATA_DIR = Path(os.getenv("DATA_DIR", JYOTIGPT_DIR / "data")).resolve()
    NEW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Move a pre-existing data directory from the repository into the
    # installed package location (backing it up as a zip first).
    if DATA_DIR.exists() and DATA_DIR != NEW_DATA_DIR:
        log.info(f"Moving {DATA_DIR} to {NEW_DATA_DIR}")
        for item in DATA_DIR.iterdir():
            dest = NEW_DATA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        shutil.make_archive(DATA_DIR.parent / "jyotigpt_data", "zip", DATA_DIR)
        shutil.rmtree(DATA_DIR)

    DATA_DIR = Path(os.getenv("DATA_DIR", JYOTIGPT_DIR / "data"))

STATIC_DIR = Path(os.getenv("STATIC_DIR", JYOTIGPT_DIR / "static"))

FONTS_DIR = Path(os.getenv("FONTS_DIR", JYOTIGPT_DIR / "static" / "fonts"))

FRONTEND_BUILD_DIR = Path(os.getenv("FRONTEND_BUILD_DIR", BASE_DIR / "build")).resolve()

if FROM_INIT_PY:
    FRONTEND_BUILD_DIR = Path(
        os.getenv("FRONTEND_BUILD_DIR", JYOTIGPT_DIR / "frontend")
    ).resolve()

####################################
# Database
####################################

# Auto-migrate the legacy Ollama-era database file name.
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/jyotigpt.db")
    log.info("Database migrated from Ollama-JyotiGPT successfully.")

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/jyotigpt.db")

# ``postgres://`` is legacy; SQLAlchemy only accepts ``postgresql://``.
if "postgres://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

DATABASE_SCHEMA = os.environ.get("DATABASE_SCHEMA", None)

DATABASE_POOL_SIZE = _integer("DATABASE_POOL_SIZE", 0)
DATABASE_POOL_MAX_OVERFLOW = _integer("DATABASE_POOL_MAX_OVERFLOW", 0)
DATABASE_POOL_TIMEOUT = _integer("DATABASE_POOL_TIMEOUT", 30)
DATABASE_POOL_RECYCLE = _integer("DATABASE_POOL_RECYCLE", 3600)

RESET_CONFIG_ON_START = _flag("RESET_CONFIG_ON_START", "False")

ENABLE_REALTIME_CHAT_SAVE = _flag("ENABLE_REALTIME_CHAT_SAVE", "False")

####################################
# Redis
####################################

REDIS_URL = os.environ.get("REDIS_URL", "")
REDIS_SENTINEL_HOSTS = os.environ.get("REDIS_SENTINEL_HOSTS", "")
REDIS_SENTINEL_PORT = os.environ.get("REDIS_SENTINEL_PORT", "26379")

####################################
# Uvicorn workers
####################################

UVICORN_WORKERS = os.environ.get("UVICORN_WORKERS", "1")
try:
    UVICORN_WORKERS = int(UVICORN_WORKERS)
    if UVICORN_WORKERS < 1:
        UVICORN_WORKERS = 1
except ValueError:
    UVICORN_WORKERS = 1
    log.info(f"Invalid UVICORN_WORKERS value, defaulting to {UVICORN_WORKERS}")

####################################
# Authentication
####################################

JYOTIGPT_AUTH = _flag("JYOTIGPT_AUTH", "True")
JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER = os.environ.get(
    "JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER", None
)
JYOTIGPT_AUTH_TRUSTED_NAME_HEADER = os.environ.get("JYOTIGPT_AUTH_TRUSTED_NAME_HEADER", None)

BYPASS_MODEL_ACCESS_CONTROL = _flag("BYPASS_MODEL_ACCESS_CONTROL", "False")

JYOTIGPT_SECRET_KEY = os.environ.get(
    "JYOTIGPT_SECRET_KEY",
    os.environ.get(
        "JYOTIGPT_JWT_SECRET_KEY", "t0p-s3cr3t"
    ),  # DEPRECATED: remove at next major version
)

JYOTIGPT_SESSION_COOKIE_SAME_SITE = os.environ.get("JYOTIGPT_SESSION_COOKIE_SAME_SITE", "lax")

JYOTIGPT_SESSION_COOKIE_SECURE = _flag("JYOTIGPT_SESSION_COOKIE_SECURE", "false")

JYOTIGPT_AUTH_COOKIE_SAME_SITE = os.environ.get(
    "JYOTIGPT_AUTH_COOKIE_SAME_SITE", JYOTIGPT_SESSION_COOKIE_SAME_SITE
)

JYOTIGPT_AUTH_COOKIE_SECURE = _flag(
    "JYOTIGPT_AUTH_COOKIE_SECURE",
    os.environ.get("JYOTIGPT_SESSION_COOKIE_SECURE", "false"),
)

if JYOTIGPT_AUTH and JYOTIGPT_SECRET_KEY == "":
    raise ValueError(ERROR_MESSAGES.ENV_VAR_NOT_FOUND)

####################################
# Websocket
####################################

ENABLE_WEBSOCKET_SUPPORT = _flag("ENABLE_WEBSOCKET_SUPPORT", "True")

WEBSOCKET_MANAGER = os.environ.get("WEBSOCKET_MANAGER", "")

WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", REDIS_URL)
WEBSOCKET_REDIS_LOCK_TIMEOUT = os.environ.get("WEBSOCKET_REDIS_LOCK_TIMEOUT", 60)

WEBSOCKET_SENTINEL_HOSTS = os.environ.get("WEBSOCKET_SENTINEL_HOSTS", "")

WEBSOCKET_SENTINEL_PORT = os.environ.get("WEBSOCKET_SENTINEL_PORT", "26379")

####################################
# HTTP client timeouts
####################################

AIOHTTP_CLIENT_TIMEOUT = _timeout_value(os.environ.get("AIOHTTP_CLIENT_TIMEOUT", ""), 300)

AIOHTTP_CLIENT_SESSION_SSL = _flag("AIOHTTP_CLIENT_SESSION_SSL", "True")

AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST = _timeout_value(
    os.environ.get(
        "AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST",
        os.environ.get("AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST", "10"),
    ),
    10,
)

AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA = _timeout_value(
    os.environ.get("AIOHTTP_CLIENT_TIMEOUT_TOOL_SERVER_DATA", "10"), 10
)

AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL = _flag(
    "AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL", "True"
)

####################################
# Offline mode
####################################

OFFLINE_MODE = _flag("OFFLINE_MODE", "false")

if OFFLINE_MODE:
    os.environ["HF_HUB_OFFLINE"] = "1"

####################################
# Audit logging
####################################

#: File to append audit records to.
AUDIT_LOGS_FILE_PATH = f"{DATA_DIR}/audit.log"

#: Maximum size of a file before rotating into a new log file.
AUDIT_LOG_FILE_ROTATION_SIZE = os.getenv("AUDIT_LOG_FILE_ROTATION_SIZE", "10MB")

#: METADATA | REQUEST | REQUEST_RESPONSE
AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "NONE").upper()

MAX_BODY_LOG_SIZE = _integer("MAX_BODY_LOG_SIZE", 2048)

#: Comma separated list of url paths to exclude from audit logging.
AUDIT_EXCLUDED_PATHS = os.getenv("AUDIT_EXCLUDED_PATHS", "/chats,/chat,/folders").split(
    ","
)
AUDIT_EXCLUDED_PATHS = [path.strip() for path in AUDIT_EXCLUDED_PATHS]
AUDIT_EXCLUDED_PATHS = [path.lstrip("/") for path in AUDIT_EXCLUDED_PATHS]

####################################
# OpenTelemetry
####################################

ENABLE_OTEL = _flag("ENABLE_OTEL", "False")
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "jyotigpt")
OTEL_RESOURCE_ATTRIBUTES = os.environ.get(
    "OTEL_RESOURCE_ATTRIBUTES", ""
)  # e.g. key1=val1,key2=val2
OTEL_TRACES_SAMPLER = os.environ.get(
    "OTEL_TRACES_SAMPLER", "parentbased_always_on"
).lower()

####################################
# Tool / function pip options
####################################

PIP_OPTIONS = os.getenv("PIP_OPTIONS", "").split()
PIP_PACKAGE_INDEX_OPTIONS = os.getenv("PIP_PACKAGE_INDEX_OPTIONS", "").split()

####################################
# Progressive web app options
####################################

EXTERNAL_PWA_MANIFEST_URL = os.environ.get("EXTERNAL_PWA_MANIFEST_URL")
