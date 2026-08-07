"""Shared web-search primitives: result model and domain filtering."""

from typing import Optional
from urllib.parse import urlparse

import validators
from pydantic import BaseModel


def get_filtered_results(results, filter_list):
    """Keep only results whose URL belongs to one of ``filter_list`` domains."""
    if not filter_list:
        return results

    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "")
        if not validators.url(url):
            continue
        domain = urlparse(url).netloc
        if any(domain.endswith(filtered_domain) for filtered_domain in filter_list):
            filtered_results.append(result)
    return filtered_results


class SearchResult(BaseModel):
    """One web-search hit: the link plus optional title and snippet."""

    link: str
    title: Optional[str]
    snippet: Optional[str]
