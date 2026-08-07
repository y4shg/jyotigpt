"""Bing Web Search API provider.

See the API docs at https://docs.microsoft.com/en-us/bing/search-apis/bing-web-search/overview
"""

import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_bing(
    subscription_key: str,
    endpoint: str,
    locale: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    mkt = locale
    params = {"q": query, "mkt": mkt, "count": count}
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        json_response = response.json()
        results = json_response.get("webPages", {}).get("value", [])
        if filter_list:
            results = get_filtered_results(results, filter_list)
        return [
            SearchResult(
                link=result["url"],
                title=result.get("name"),
                snippet=result.get("snippet"),
            )
            for result in results
        ]
    except Exception as ex:
        log.error(f"Error: {ex}")
        raise ex
