"""Perplexity API search provider.

Turns a chat-completion call against the ``sonar`` model into a list of
search results built from the returned citations.
"""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


def search_perplexity(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Search using the Perplexity API and return SearchResult objects."""
    # Handle PersistentConfig objects passed by callers.
    if hasattr(api_key, "__str__"):
        api_key = str(api_key)

    try:
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a search assistant. Provide factual information with citations.",
                },
                {"role": "user", "content": query},
            ],
            "temperature": 0.2,  # lower temperature for more factual responses
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        response = requests.request("POST", PERPLEXITY_URL, json=payload, headers=headers)
        json_response = response.json()

        citations = json_response.get("citations", [])

        results = []
        for i, citation in enumerate(citations[:count]):
            content = ""
            if "choices" in json_response and json_response["choices"]:
                if i == 0:
                    content = json_response["choices"][0]["message"]["content"]

            results.append({"link": citation, "title": f"Source {i+1}", "snippet": content})

        if filter_list:
            results = get_filtered_results(results, filter_list)

        return [
            SearchResult(
                link=result["link"], title=result["title"], snippet=result["snippet"]
            )
            for result in results[:count]
        ]

    except Exception as e:
        log.error(f"Error searching with Perplexity API: {e}")
        return []
