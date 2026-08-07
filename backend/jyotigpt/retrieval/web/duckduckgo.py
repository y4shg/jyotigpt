"""DuckDuckGo search provider (via duckduckgo_search)."""

import logging
from typing import List, Optional

from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_duckduckgo(
    query: str, count: int, filter_list: Optional[List[str]] = None
) -> List[SearchResult]:
    """Search using DuckDuckGo and return SearchResult objects."""
    search_results = []
    with DDGS() as ddgs:
        try:
            search_results = ddgs.text(
                query, safesearch="moderate", max_results=count, backend="lite"
            )
        except RatelimitException as e:
            log.error(f"RatelimitException: {e}")
    if filter_list:
        search_results = get_filtered_results(search_results, filter_list)

    return [
        SearchResult(
            link=result["href"],
            title=result.get("title"),
            snippet=result.get("body"),
        )
        for result in search_results
    ]
