"""SearXNG instance search provider."""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

USER_AGENT = "JyotiGPT (https://github.com/y4shg/jyotigpt) RAG Bot"


def search_searxng(
    query_url: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    **kwargs,
) -> List[SearchResult]:
    """Search a SearXNG instance for a query.

    Args:
        query_url: Base URL of the SearXNG server.
        query: The search term or question.
        count: Maximum number of results.

    Keyword Args:
        language: Language filter, e.g. "en-US" (default).
        safesearch: 0 = off, 1 = moderate (default), 2 = strict.
        time_range: Date filter, e.g. "2023-04-05..today" or "".
        categories: Optional list of search categories.

    Returns:
        Results sorted by relevance score, highest first.
    """
    language = kwargs.get("language", "en-US")
    safesearch = kwargs.get("safesearch", "1")
    time_range = kwargs.get("time_range", "")
    categories = "".join(kwargs.get("categories", []))

    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
        "safesearch": safesearch,
        "language": language,
        "time_range": time_range,
        "categories": categories,
        "theme": "simple",
        "image_proxy": 0,
    }

    # Legacy query format: ignore any query params on the instance URL.
    if "<query>" in query_url:
        query_url = query_url.split("?")[0]

    log.debug(f"searching {query_url}")

    response = requests.get(
        query_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        },
        params=params,
    )

    response.raise_for_status()

    json_response = response.json()
    results = json_response.get("results", [])
    sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    if filter_list:
        sorted_results = get_filtered_results(sorted_results, filter_list)
    return [
        SearchResult(
            link=result["url"], title=result.get("title"), snippet=result.get("content")
        )
        for result in sorted_results[:count]
    ]
