"""Serply search provider."""

import logging
from typing import List, Optional
from urllib.parse import urlencode

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

SERPLY_URL = "https://api.serply.io/v1/search/"


def search_serply(
    api_key: str,
    query: str,
    count: int,
    hl: str = "us",
    limit: int = 10,
    device_type: str = "desktop",
    proxy_location: str = "US",
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Search using Serply's API and return SearchResult objects.

    Args:
        api_key: A Serply API key.
        query: The search query.
        hl: Host language code for result display.
        limit: Max results the API may return [10-100, default 10].
    """
    log.info("Searching with Serply")

    query_payload = {
        "q": query,
        "language": "en",
        "num": limit,
        "gl": proxy_location.upper(),
        "hl": hl.lower(),
    }

    url = f"{SERPLY_URL}{urlencode(query_payload)}"
    headers = {
        "X-API-KEY": api_key,
        "X-User-Agent": device_type,
        "User-Agent": "jyotigpt",
        "X-Proxy-Location": proxy_location,
    }

    response = requests.request("GET", url, headers=headers)
    response.raise_for_status()

    json_response = response.json()
    log.info(f"results from serply search: {json_response}")

    results = sorted(
        json_response.get("results", []), key=lambda x: x.get("realPosition", 0)
    )
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in results[:count]
    ]
