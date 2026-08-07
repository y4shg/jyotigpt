"""searchapi.io search provider."""

import logging
from typing import List, Optional
from urllib.parse import urlencode

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"


def search_searchapi(
    api_key: str,
    engine: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Search using searchapi.io's API and return SearchResult objects."""
    engine = engine or "google"

    payload = {"engine": engine, "q": query, "api_key": api_key}
    url = f"{SEARCHAPI_URL}?{urlencode(payload)}"
    response = requests.request("GET", url)

    json_response = response.json()
    log.info(f"results from searchapi search: {json_response}")

    results = sorted(
        json_response.get("organic_results", []), key=lambda x: x.get("position", 0)
    )
    if filter_list:
        results = get_filtered_results(results, filter_list)
    return [
        SearchResult(
            link=result["link"], title=result["title"], snippet=result["snippet"]
        )
        for result in results[:count]
    ]
