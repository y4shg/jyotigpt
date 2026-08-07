"""General-purpose helpers.

A dependency-light leaf module: message-chain reconstruction and role
extraction, OpenAI response templating, hashing, filename/email sanitizing,
duration parsing, and Ollama Modelfile parsing. Imported broadly across the
backend, so signatures here are treated as a stable contract.
"""

import collections.abc
import hashlib
import json
import logging
import re
import time
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Optional

from jyotigpt.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def deep_update(d, u):
    """Recursively merge mapping ``u`` into ``d`` in place, returning ``d``."""
    for key, value in u.items():
        if isinstance(value, collections.abc.Mapping):
            d[key] = deep_update(d.get(key, {}), value)
        else:
            d[key] = value
    return d


##############
# Message chain helpers
##############


def get_message_list(messages, message_id):
    """Walk parentId links from ``message_id`` back to the root.

    Returns the root-to-target chain as a list, or None if ``message_id`` is
    not present in ``messages``.
    """
    current_message = messages.get(message_id)
    if not current_message:
        return None

    message_list = []
    while current_message:
        message_list.insert(0, current_message)
        parent_id = current_message["parentId"]
        current_message = messages.get(parent_id) if parent_id else None

    return message_list


def get_content_from_message(message: dict) -> Optional[str]:
    """Extract text content from a message with string or block-list content."""
    if isinstance(message["content"], list):
        for item in message["content"]:
            if item["type"] == "text":
                return item["text"]
    else:
        return message["content"]
    return None


def get_messages_content(messages: list[dict]) -> str:
    """Render messages as ``ROLE: content`` lines joined by newlines."""
    return "\n".join(
        f"{message['role'].upper()}: {get_content_from_message(message)}"
        for message in messages
    )


def get_last_user_message_item(messages: list[dict]) -> Optional[dict]:
    """Return the last message with role ``user``, or None."""
    for message in reversed(messages):
        if message["role"] == "user":
            return message
    return None


def get_last_user_message(messages: list[dict]) -> Optional[str]:
    """Return the text content of the last user message, or None."""
    message = get_last_user_message_item(messages)
    if message is None:
        return None
    return get_content_from_message(message)


def get_last_assistant_message_item(messages: list[dict]) -> Optional[dict]:
    """Return the last message with role ``assistant``, or None."""
    for message in reversed(messages):
        if message["role"] == "assistant":
            return message
    return None


def get_last_assistant_message(messages: list[dict]) -> Optional[str]:
    """Return the text content of the last assistant message, or None."""
    for message in reversed(messages):
        if message["role"] == "assistant":
            return get_content_from_message(message)
    return None


def get_system_message(messages: list[dict]) -> Optional[dict]:
    """Return the first message with role ``system``, or None."""
    for message in messages:
        if message["role"] == "system":
            return message
    return None


def remove_system_message(messages: list[dict]) -> list[dict]:
    """Return a copy of ``messages`` with all system messages removed."""
    return [message for message in messages if message["role"] != "system"]


def pop_system_message(messages: list[dict]) -> tuple[Optional[dict], list[dict]]:
    """Return ``(system_message, messages_without_system)``."""
    return get_system_message(messages), remove_system_message(messages)


def prepend_to_first_user_message_content(
    content: str, messages: list[dict]
) -> list[dict]:
    """Prepend ``content`` to the first user message, then stop."""
    for message in messages:
        if message["role"] == "user":
            if isinstance(message["content"], list):
                for item in message["content"]:
                    if item["type"] == "text":
                        item["text"] = f"{content}\n{item['text']}"
            else:
                message["content"] = f"{content}\n{message['content']}"
            break
    return messages


def add_or_update_system_message(content: str, messages: list[dict]):
    """Prepend ``content`` to a leading system message, or insert one.

    If the first message is a system message its content is prefixed with
    ``content``; otherwise a new system message is inserted at index 0.
    """
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = f"{content}\n{messages[0]['content']}"
    else:
        messages.insert(0, {"role": "system", "content": content})
    return messages


def add_or_update_user_message(content: str, messages: list[dict]):
    """Append ``content`` to a trailing user message, or add a new one."""
    if messages and messages[-1].get("role") == "user":
        messages[-1]["content"] = f"{messages[-1]['content']}\n{content}"
    else:
        messages.append({"role": "user", "content": content})
    return messages


def append_or_update_assistant_message(content: str, messages: list[dict]):
    """Append ``content`` to a trailing assistant message, or add a new one."""
    if messages and messages[-1].get("role") == "assistant":
        messages[-1]["content"] = f"{messages[-1]['content']}\n{content}"
    else:
        messages.append({"role": "assistant", "content": content})
    return messages


##############
# OpenAI response templates
##############


def openai_chat_message_template(model: str):
    """Return a base OpenAI chat response skeleton for ``model``."""
    return {
        "id": f"{model}-{str(uuid.uuid4())}",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "logprobs": None, "finish_reason": None}],
    }


def openai_chat_chunk_message_template(
    model: str,
    content: Optional[str] = None,
    tool_calls: Optional[list[dict]] = None,
    usage: Optional[dict] = None,
) -> dict:
    """Build a ``chat.completion.chunk`` payload.

    With neither ``content`` nor ``tool_calls`` the chunk is terminal and
    carries ``finish_reason: stop``.
    """
    template = openai_chat_message_template(model)
    template["object"] = "chat.completion.chunk"

    template["choices"][0]["index"] = 0
    template["choices"][0]["delta"] = {}

    if content:
        template["choices"][0]["delta"]["content"] = content

    if tool_calls:
        template["choices"][0]["delta"]["tool_calls"] = tool_calls

    if not content and not tool_calls:
        template["choices"][0]["finish_reason"] = "stop"

    if usage:
        template["usage"] = usage
    return template


def openai_chat_completion_message_template(
    model: str,
    message: Optional[str] = None,
    tool_calls: Optional[list[dict]] = None,
    usage: Optional[dict] = None,
) -> dict:
    """Build a non-streaming ``chat.completion`` payload."""
    template = openai_chat_message_template(model)
    template["object"] = "chat.completion"
    if message is not None:
        template["choices"][0]["message"] = {
            "content": message,
            "role": "assistant",
            **({"tool_calls": tool_calls} if tool_calls else {}),
        }
    template["choices"][0]["finish_reason"] = "stop"

    if usage:
        template["usage"] = usage
    return template


##############
# Hashing / validation / filesystem
##############


def get_gravatar_url(email):
    """Return the Gravatar URL for ``email`` (SHA-256, mystery-person default)."""
    address = str(email).strip().lower()
    hash_hex = hashlib.sha256(address.encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_hex}?d=mp"


def calculate_sha256(file_path, chunk_size):
    """Return the SHA-256 hex digest of a file, read in ``chunk_size`` blocks."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_sha256_string(string):
    """Return the SHA-256 hex digest of ``string`` (UTF-8 encoded)."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(string.encode("utf-8"))
    return sha256_hash.hexdigest()


def validate_email_format(email: str) -> bool:
    """Return True for a basic ``x@y.z`` shape or any ``@localhost`` address."""
    if email.endswith("@localhost"):
        return True
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def sanitize_filename(file_name):
    """Lowercase, strip punctuation, and hyphenate whitespace in ``file_name``."""
    lower_case_file_name = file_name.lower()
    sanitized_file_name = re.sub(r"[^\w\s]", "", lower_case_file_name)
    return re.sub(r"\s+", "-", sanitized_file_name)


def extract_folders_after_data_docs(path):
    """Return cumulative folder tags below ``data/docs`` in ``path``.

    For ``.../data/docs/a/b/file.txt`` yields ``['a', 'a/b']``. Returns an
    empty list when the ``data/docs`` segment is absent.
    """
    path = Path(path)
    parts = path.parts

    try:
        index_data_docs = parts.index("data") + 1
        index_docs = parts.index("docs", index_data_docs) + 1
    except ValueError:
        return []

    tags = []
    folders = parts[index_docs:-1]
    for idx, _ in enumerate(folders):
        tags.append("/".join(folders[: idx + 1]))
    return tags


def parse_duration(duration: str) -> Optional[timedelta]:
    """Parse a duration like ``2h30m`` into a timedelta.

    ``"-1"`` and ``"0"`` map to None (no expiry). Raises ValueError when no
    number/unit pair is found. Units: ms, s, m, h, d, w.
    """
    if duration == "-1" or duration == "0":
        return None

    pattern = r"(-?\d+(\.\d+)?)(ms|s|m|h|d|w)"
    matches = re.findall(pattern, duration)
    if not matches:
        raise ValueError("Invalid duration string")

    unit_to_kwarg = {
        "ms": "milliseconds",
        "s": "seconds",
        "m": "minutes",
        "h": "hours",
        "d": "days",
        "w": "weeks",
    }

    total_duration = timedelta()
    for number, _, unit in matches:
        total_duration += timedelta(**{unit_to_kwarg[unit]: float(number)})
    return total_duration


##############
# Ollama Modelfile parsing
##############


def parse_ollama_modelfile(model_text):
    """Parse an Ollama Modelfile into ``{base_model_id, params}``.

    Extracts FROM, TEMPLATE, PARAMETER (typed per a known parameter table,
    plus repeated ``stop`` values), ADAPTER, SYSTEM, and MESSAGE directives.
    """
    parameters_meta = {
        "mirostat": int,
        "mirostat_eta": float,
        "mirostat_tau": float,
        "num_ctx": int,
        "repeat_last_n": int,
        "repeat_penalty": float,
        "temperature": float,
        "seed": int,
        "tfs_z": float,
        "num_predict": int,
        "top_k": int,
        "top_p": float,
        "num_keep": int,
        "typical_p": float,
        "presence_penalty": float,
        "frequency_penalty": float,
        "penalize_newline": bool,
        "numa": bool,
        "num_batch": int,
        "num_gpu": int,
        "main_gpu": int,
        "low_vram": bool,
        "f16_kv": bool,
        "vocab_only": bool,
        "use_mmap": bool,
        "use_mlock": bool,
        "num_thread": int,
    }

    data = {"base_model_id": None, "params": {}}

    base_model_match = re.search(
        r"^FROM\s+(\w+)", model_text, re.MULTILINE | re.IGNORECASE
    )
    if base_model_match:
        data["base_model_id"] = base_model_match.group(1)

    template_match = re.search(
        r'TEMPLATE\s+"""(.+?)"""', model_text, re.DOTALL | re.IGNORECASE
    )
    if template_match:
        data["params"] = {"template": template_match.group(1).strip()}

    stops = re.findall(r'PARAMETER stop "(.*?)"', model_text, re.IGNORECASE)
    if stops:
        data["params"]["stop"] = stops

    for param, param_type in parameters_meta.items():
        param_match = re.search(rf"PARAMETER {param} (.+)", model_text, re.IGNORECASE)
        if param_match:
            value = param_match.group(1)
            try:
                if param_type is int:
                    value = int(value)
                elif param_type is float:
                    value = float(value)
                elif param_type is bool:
                    value = value.lower() == "true"
            except Exception as e:
                log.exception(f"Failed to parse parameter {param}: {e}")
                continue
            data["params"][param] = value

    adapter_match = re.search(r"ADAPTER (.+)", model_text, re.IGNORECASE)
    if adapter_match:
        data["params"]["adapter"] = adapter_match.group(1)

    system_desc_match = re.search(
        r'SYSTEM\s+"""(.+?)"""', model_text, re.DOTALL | re.IGNORECASE
    )
    system_desc_match_single = re.search(
        r"SYSTEM\s+([^\n]+)", model_text, re.IGNORECASE
    )
    if system_desc_match:
        data["params"]["system"] = system_desc_match.group(1).strip()
    elif system_desc_match_single:
        data["params"]["system"] = system_desc_match_single.group(1).strip()

    messages = []
    message_matches = re.findall(r"MESSAGE (\w+) (.+)", model_text, re.IGNORECASE)
    for role, content in message_matches:
        messages.append({"role": role, "content": content})
    if messages:
        data["params"]["messages"] = messages

    return data


def convert_logit_bias_input_to_json(user_input):
    """Convert ``token:bias,...`` input into a JSON string, clamped to +/-100."""
    logit_bias_pairs = user_input.split(",")
    logit_bias_json = {}
    for pair in logit_bias_pairs:
        token, bias = pair.split(":")
        token = str(token.strip())
        bias = int(bias.strip())
        bias = 100 if bias > 100 else -100 if bias < -100 else bias
        logit_bias_json[token] = bias
    return json.dumps(logit_bias_json)
