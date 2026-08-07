"""serpstack.com search provider."""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_serpstack(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    https_enabled: bool = True,
) -> List[SearchResult]:
    """Search using serpstack.com's API and return SearchResult objects.

    Args:
        https_enabled: Whether to call the HTTPS or HTTP endpoint.
    """
    url = f"{'https' if https_enabled else 'http'}://api.serpstack.com/search"

    headers = {"Content-Type": "application/json"}
    params = {
        "access_key": api_key,
        "query": query,
    }

    response = requests.request("POST", url, headers=headers, params=params)
    response.raise_for_status()

    json_response = response.json()
    results = sorted(
        json_response.get("organic_results", []), key=lambda x: x.get("position", 0)
    )
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("snippet")
        )
        for result in results[:count]
    ]
