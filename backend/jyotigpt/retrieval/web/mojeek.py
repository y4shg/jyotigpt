"""Mojeek Search API provider."""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_mojeek(
    api_key: str, query: str, count: int, filter_list: Optional[List[str]] = None
) -> List[SearchResult]:
    """Search using Mojeek's Search API and return SearchResult objects."""
    url = "https://api.mojeek.com/search"
    headers = {
        "Accept": "application/json",
    }
    params = {"q": query, "api_key": api_key, "fmt": "json", "t": count}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    json_response = response.json()
    results = json_response.get("response", {}).get("results", [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("desc")
        )
        for result in results
    ]
