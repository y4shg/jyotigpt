"""Tavily search API provider."""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def search_tavily(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Search using Tavily's Search API and return SearchResult objects."""
    data = {"query": query, "api_key": api_key}
    response = requests.post(TAVILY_SEARCH_URL, json=data)
    response.raise_for_status()

    json_response = response.json()
    raw_search_results = json_response.get("results", [])

    return [
        SearchResult(
            link=result["url"],
            title=result.get("title", ""),
            snippet=result.get("content"),
        )
        for result in raw_search_results[:count]
    ]
