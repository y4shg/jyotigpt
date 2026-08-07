"""Prompt-template rendering for auxiliary generation tasks.

Provides placeholder substitution used when constructing prompts for
title/tag/query/emoji/autocomplete generation, RAG context assembly, and
mixture-of-agents responses. Handles date/time tokens, prompt/message
excerpting (start/end/middle-truncate), and query/context injection.
"""

import logging
import math
import re
import uuid
from datetime import datetime
from typing import Optional

from jyotigpt.config import DEFAULT_RAG_TEMPLATE
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.utils.misc import get_last_user_message, get_messages_content

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def get_task_model_id(
    default_model_id: str, task_model: str, task_model_external: str, models
) -> str:
    """Resolve which model handles an auxiliary task.

    Local (Ollama-owned) default models may be overridden by ``task_model``;
    external models may be overridden by ``task_model_external``. The override
    is only applied when it names a model that actually exists.
    """
    task_model_id = default_model_id

    if models[task_model_id].get("owned_by") == "ollama":
        if task_model and task_model in models:
            task_model_id = task_model
    else:
        if task_model_external and task_model_external in models:
            task_model_id = task_model_external

    return task_model_id


def prompt_variables_template(template: str, variables: dict[str, str]) -> str:
    """Replace each ``variable`` key with its value in ``template``."""
    for variable, value in variables.items():
        template = template.replace(variable, value)
    return template


def prompt_template(
    template: str, user_name: Optional[str] = None, user_location: Optional[str] = None
) -> str:
    """Substitute date/time and user tokens into ``template``.

    Fills ``{{CURRENT_DATE}}``, ``{{CURRENT_TIME}}``, ``{{CURRENT_DATETIME}}``,
    ``{{CURRENT_WEEKDAY}}``, ``{{USER_NAME}}``, and ``{{USER_LOCATION}}``.
    Missing user values default to ``"Unknown"``.
    """
    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d")
    formatted_time = now.strftime("%I:%M:%S %p")
    formatted_weekday = now.strftime("%A")

    template = template.replace("{{CURRENT_DATE}}", formatted_date)
    template = template.replace("{{CURRENT_TIME}}", formatted_time)
    template = template.replace(
        "{{CURRENT_DATETIME}}", f"{formatted_date} {formatted_time}"
    )
    template = template.replace("{{CURRENT_WEEKDAY}}", formatted_weekday)

    template = template.replace("{{USER_NAME}}", user_name if user_name else "Unknown")
    template = template.replace(
        "{{USER_LOCATION}}", user_location if user_location else "Unknown"
    )

    return template


def _excerpt_text(text: str, start_length, end_length, middle_length) -> str:
    """Return a slice of ``text`` per the matched excerpt directive.

    Exactly one of the length groups is non-None; ``middle_length`` keeps the
    head and tail joined by an ellipsis when the text is longer than the limit.
    """
    if start_length is not None:
        return text[: int(start_length)]
    if end_length is not None:
        return text[-int(end_length) :]
    if middle_length is not None:
        limit = int(middle_length)
        if len(text) <= limit:
            return text
        head = text[: math.ceil(limit / 2)]
        tail = text[-math.floor(limit / 2) :]
        return f"{head}...{tail}"
    return ""


def replace_prompt_variable(template: str, prompt: str) -> str:
    """Substitute ``{{prompt}}`` and its excerpt variants (case-insensitive)."""

    def replacement_function(match):
        full_match = match.group(0).lower()
        if full_match == "{{prompt}}":
            return prompt
        return _excerpt_text(
            prompt, match.group(1), match.group(2), match.group(3)
        )

    pattern = r"(?i){{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}"
    return re.sub(pattern, replacement_function, template)


def replace_messages_variable(
    template: str, messages: Optional[list[dict]] = None
) -> str:
    """Substitute ``{{MESSAGES}}`` and its excerpt variants.

    Message excerpts operate on the number of messages (not characters);
    the middle-truncate variant joins the head and tail slices with a newline.
    """

    def replacement_function(match):
        full_match = match.group(0)
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if messages is None:
            return ""

        if full_match == "{{MESSAGES}}":
            return get_messages_content(messages)
        if start_length is not None:
            return get_messages_content(messages[: int(start_length)])
        if end_length is not None:
            return get_messages_content(messages[-int(end_length) :])
        if middle_length is not None:
            mid = int(middle_length)
            if len(messages) <= mid:
                return get_messages_content(messages)
            half = mid // 2
            start_msgs = messages[:half]
            end_msgs = messages[-half:] if mid % 2 == 0 else messages[-(half + 1) :]
            return f"{get_messages_content(start_msgs)}\n{get_messages_content(end_msgs)}"
        return ""

    pattern = r"{{MESSAGES}}|{{MESSAGES:START:(\d+)}}|{{MESSAGES:END:(\d+)}}|{{MESSAGES:MIDDLETRUNCATE:(\d+)}}"
    return re.sub(pattern, replacement_function, template)


def rag_template(template: str, context: str, query: str):
    """Inject retrieval context and the user query into a RAG template.

    Falls back to the default template when empty. Query placeholders present
    inside the context are neutralized via a random sentinel before the real
    query is substituted, so untrusted context cannot inject query tokens.
    """
    if template.strip() == "":
        template = DEFAULT_RAG_TEMPLATE

    template = prompt_template(template)

    if "[context]" not in template and "{{CONTEXT}}" not in template:
        log.debug(
            "WARNING: The RAG template does not contain the '[context]' or '{{CONTEXT}}' placeholder."
        )

    if "<context>" in context and "</context>" in context:
        log.debug(
            "WARNING: Potential prompt injection attack: the RAG "
            "context contains '<context>' and '</context>'. This might be "
            "nothing, or the user might be trying to hack something."
        )

    query_placeholders = []
    if "[query]" in context:
        placeholder = "{{QUERY" + str(uuid.uuid4()) + "}}"
        template = template.replace("[query]", placeholder)
        query_placeholders.append(placeholder)

    if "{{QUERY}}" in context:
        placeholder = "{{QUERY" + str(uuid.uuid4()) + "}}"
        template = template.replace("{{QUERY}}", placeholder)
        query_placeholders.append(placeholder)

    template = template.replace("[context]", context)
    template = template.replace("{{CONTEXT}}", context)
    template = template.replace("[query]", query)
    template = template.replace("{{QUERY}}", query)

    for placeholder in query_placeholders:
        template = template.replace(placeholder, query)

    return template


def _user_kwargs(user: Optional[dict]) -> dict:
    """Extract name/location kwargs from a user dict for ``prompt_template``."""
    if not user:
        return {}
    return {"user_name": user.get("name"), "user_location": user.get("location")}


def title_generation_template(
    template: str, messages: list[dict], user: Optional[dict] = None
) -> str:
    """Render a title-generation prompt from the conversation."""
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)
    return prompt_template(template, **_user_kwargs(user))


def tags_generation_template(
    template: str, messages: list[dict], user: Optional[dict] = None
) -> str:
    """Render a tag-generation prompt from the conversation."""
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)
    return prompt_template(template, **_user_kwargs(user))


def image_prompt_generation_template(
    template: str, messages: list[dict], user: Optional[dict] = None
) -> str:
    """Render an image-prompt-generation prompt from the conversation."""
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)
    return prompt_template(template, **_user_kwargs(user))


def emoji_generation_template(
    template: str, prompt: str, user: Optional[dict] = None
) -> str:
    """Render an emoji-generation prompt from a single prompt string."""
    template = replace_prompt_variable(template, prompt)
    return prompt_template(template, **_user_kwargs(user))


def autocomplete_generation_template(
    template: str,
    prompt: str,
    messages: Optional[list[dict]] = None,
    type: Optional[str] = None,
    user: Optional[dict] = None,
) -> str:
    """Render an autocomplete prompt, filling the completion ``{{TYPE}}``."""
    template = template.replace("{{TYPE}}", type if type else "")
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)
    return prompt_template(template, **_user_kwargs(user))


def query_generation_template(
    template: str, messages: list[dict], user: Optional[dict] = None
) -> str:
    """Render a search-query-generation prompt from the conversation."""
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)
    return prompt_template(template, **_user_kwargs(user))


def moa_response_generation_template(
    template: str, prompt: str, responses: list[str]
) -> str:
    """Render a mixture-of-agents synthesis prompt.

    Substitutes the originating ``{{prompt}}`` (with excerpt variants) and
    joins the candidate ``{{responses}}`` as triple-quoted blocks.
    """

    def replacement_function(match):
        full_match = match.group(0)
        if full_match == "{{prompt}}":
            return prompt
        return _excerpt_text(
            prompt, match.group(1), match.group(2), match.group(3)
        )

    pattern = r"{{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}"
    template = re.sub(pattern, replacement_function, template)

    joined = "\n\n".join(f'"""{response}"""' for response in responses)
    return template.replace("{{responses}}", joined)


def tools_function_calling_generation_template(template: str, tools_specs: str) -> str:
    """Substitute the available ``{{TOOLS}}`` specification into the template."""
    return template.replace("{{TOOLS}}", tools_specs)
