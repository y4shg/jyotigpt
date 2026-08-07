"""Tavily Extract document loader.

Pulls readable content out of web pages through the Tavily Extract API,
in batches of up to 20 URLs per request. Each successful extraction
becomes a ``Document`` whose metadata records the source URL.
"""

import logging
from typing import Iterator, List, Literal, Union

import requests

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from jyotigpt.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

BATCH_SIZE = 20


class TavilyLoader(BaseLoader):
    """Extract web page content from URLs using the Tavily Extract API.

    Args:
        urls: URL or list of URLs to extract content from.
        api_key: The Tavily API key.
        extract_depth: "basic" or "advanced". Advanced extraction pulls
            more data (tables, embedded content) at a higher credit cost.
        continue_on_failure: Whether to keep going when one URL fails.
    """

    def __init__(
        self,
        urls: Union[str, List[str]],
        api_key: str,
        extract_depth: Literal["basic", "advanced"] = "basic",
        continue_on_failure: bool = True,
    ) -> None:
        if not urls:
            raise ValueError("At least one URL must be provided.")

        self.api_key = api_key
        self.urls = urls if isinstance(urls, list) else [urls]
        self.extract_depth = extract_depth
        self.continue_on_failure = continue_on_failure
        self.api_url = "https://api.tavily.com/extract"

    def lazy_load(self) -> Iterator[Document]:
        """Extract and yield documents from the URLs, batch by batch."""
        for i in range(0, len(self.urls), BATCH_SIZE):
            batch_urls = self.urls[i : i + BATCH_SIZE]
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                # Single URL goes as a string, multiple as an array.
                urls_param = batch_urls[0] if len(batch_urls) == 1 else batch_urls
                payload = {"urls": urls_param, "extract_depth": self.extract_depth}

                response = requests.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()

                for result in response_data.get("results", []):
                    url = result.get("url", "")
                    content = result.get("raw_content", "")
                    if not content:
                        log.warning(f"No content extracted from {url}")
                        continue
                    yield Document(
                        page_content=content,
                        metadata={"source": url},
                    )

                for failed in response_data.get("failed_results", []):
                    url = failed.get("url", "")
                    error = failed.get("error", "Unknown error")
                    log.error(f"Failed to extract content from {url}: {error}")
            except Exception as e:
                if self.continue_on_failure:
                    log.error(f"Error extracting content from batch {batch_urls}: {e}")
                else:
                    raise e
