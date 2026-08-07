"""Jina Search API provider."""

import logging

import requests
from yarl import URL

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

JINA_SEARCH_ENDPOINT = "https://s.jina.ai/"


def search_jina(api_key: str, query: str, count: int) -> list[SearchResult]:
    """Search using Jina's Search API and return SearchResult objects.

    Args:
        query (str): The query to search for
        count (int): The number of results to return
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": api_key,
        "X-Retain-Images": "none",
    }

    payload = {"q": query, "count": count if count <= 10 else 10}

    url = str(URL(JINA_SEARCH_ENDPOINT))
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    return [
        SearchResult(
            link=result["url"],
            title=result.get("title"),
            snippet=result.get("content"),
        )
        for result in data["data"]
    ]
