"""Kagi Search API provider."""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_kagi(
    api_key: str, query: str, count: int, filter_list: Optional[List[str]] = None
) -> List[SearchResult]:
    """Search using Kagi's Search API and return SearchResult objects.

    The Search API inherits the settings from your account, including
    results personalization and snippet length.
    """
    url = "https://kagi.com/api/v0/search"
    headers = {
        "Authorization": f"Bot {api_key}",
    }
    params = {"q": query, "limit": count}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    json_response = response.json()
    search_results = json_response.get("data", [])

    results = [
        SearchResult(
            link=result["url"], title=result["title"], snippet=result.get("snippet")
        )
        for result in search_results
        if result["t"] == 0  # only plain web results, not images/news etc.
    ]

    if filter_list:
        results = get_filtered_results(results, filter_list)

    return results
