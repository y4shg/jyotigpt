"""serper.dev search provider."""

import json
import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

SERPER_URL = "https://google.serper.dev/search"


def search_serper(
    api_key: str, query: str, count: int, filter_list: Optional[List[str]] = None
) -> List[SearchResult]:
    """Search using serper.dev's API and return SearchResult objects."""
    payload = json.dumps({"q": query})
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    response = requests.request("POST", SERPER_URL, headers=headers, data=payload)
    response.raise_for_status()

    json_response = response.json()
    results = sorted(
        json_response.get("organic", []), key=lambda x: x.get("position", 0)
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
