"""Outbound webhook delivery.

Formats a notification message for common webhook targets (Slack, Google
Chat, Discord, Microsoft Teams) and POSTs it. Unrecognized URLs receive
the raw event payload.
"""

import json
import logging

import requests

from jyotigpt.config import JYOTIGPT_FAVICON_URL
from jyotigpt.env import SRC_LOG_LEVELS, VERSION

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["WEBHOOK"])

# Discord enforces a 2000-character limit on message content.
_DISCORD_CONTENT_LIMIT = 2000
_DISCORD_TRUNCATION_SUFFIX = "... (truncated)"


def _build_teams_payload(name: str, message: str, event_data: dict) -> dict:
    """Assemble a Microsoft Teams MessageCard from the event data."""
    action = event_data.get("action", "undefined")
    user_fields = json.loads(event_data.get("user", {}))
    facts = [{"name": key, "value": value} for key, value in user_fields.items()]

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary": message,
        "sections": [
            {
                "activityTitle": message,
                "activitySubtitle": f"{name} ({VERSION}) - {action}",
                "activityImage": JYOTIGPT_FAVICON_URL,
                "facts": facts,
                "markdown": True,
            }
        ],
    }


def post_webhook(name: str, url: str, message: str, event_data: dict) -> bool:
    """POST a formatted notification to ``url``.

    The payload shape is chosen from the URL host. Returns ``True`` on a
    successful (2xx) response and ``False`` if the request raises.
    """
    try:
        log.debug(f"post_webhook: {url}, {message}, {event_data}")

        if "https://hooks.slack.com" in url or "https://chat.googleapis.com" in url:
            payload = {"text": message}
        elif "https://discord.com/api/webhooks" in url:
            if len(message) < _DISCORD_CONTENT_LIMIT:
                content = message
            else:
                cutoff = _DISCORD_CONTENT_LIMIT - len(_DISCORD_TRUNCATION_SUFFIX)
                content = f"{message[:cutoff]}{_DISCORD_TRUNCATION_SUFFIX}"
            payload = {"content": content}
        elif "webhook.office.com" in url:
            payload = _build_teams_payload(name, message, event_data)
        else:
            payload = {**event_data}

        log.debug(f"payload: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        log.debug(f"r.text: {response.text}")
        return True
    except Exception as e:
        log.exception(e)
        return False
