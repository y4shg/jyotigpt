"""Google Programmable Search Engine API provider."""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

MAX_PAGE_SIZE = 10  # Google PSE caps results per query at 10


def search_google_pse(
    api_key: str,
    search_engine_id: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    """Search Google PSE, paging through results for counts over 10.

    Args:
        api_key: Programmable Search Engine API key.
        search_engine_id: Programmable Search Engine ID.
        query: The search query.
        count: How many results to return (max 100).
        filter_list: Optional domains to keep.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    headers = {"Content-Type": "application/json"}
    all_results = []
    start_index = 1  # Google PSE start is 1-based

    while count > 0:
        num_results_this_page = min(count, MAX_PAGE_SIZE)
        params = {
            "cx": search_engine_id,
            "q": query,
            "key": api_key,
            "num": num_results_this_page,
            "start": start_index,
        }
        response = requests.request("GET", url, headers=headers, params=params)
        response.raise_for_status()
        json_response = response.json()
        results = json_response.get("items", [])
        if not results:
            break  # No more pages available.
        all_results.extend(results)
        count -= len(results)
        start_index += MAX_PAGE_SIZE

    if filter_list:
        all_results = get_filtered_results(all_results, filter_list)

    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("snippet"),
        )
        for result in all_results
    ]
