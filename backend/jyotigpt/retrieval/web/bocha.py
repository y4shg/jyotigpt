"""Bocha (Bocha AI) web search provider."""

import json
import logging
from typing import List, Optional

import requests

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def _parse_response(response):
    """Map the Bocha response shape onto a flat ``webpage`` list."""
    result = {}
    if "data" in response:
        data = response["data"]
        if "webPages" in data:
            web_pages = data["webPages"]
            if "value" in web_pages:
                result["webpage"] = [
                    {
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "summary": item.get("summary", ""),
                        "siteName": item.get("siteName", ""),
                        "siteIcon": item.get("siteIcon", ""),
                        "datePublished": item.get("datePublished", "")
                        or item.get("dateLastCrawled", ""),
                    }
                    for item in web_pages["value"]
                ]
    return result


def search_bocha(
    api_key: str, query: str, count: int, filter_list: Optional[List[str]] = None
) -> List[SearchResult]:
    """Search using Bocha's Search API and return SearchResult objects."""
    url = "https://api.bochaai.com/v1/web-search?utm_source=ollama"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = json.dumps(
        {"query": query, "summary": True, "freshness": "noLimit", "count": count}
    )

    response = requests.post(url, headers=headers, data=payload, timeout=5)
    response.raise_for_status()
    results = _parse_response(response.json()).get("webpage", [])
    if filter_list:
        results = get_filtered_results(results, filter_list)

    return [
        SearchResult(
            link=result["url"], title=result.get("name"), snippet=result.get("summary")
        )
        for result in results[:count]
    ]
