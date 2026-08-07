"""Web page loaders and the loader factory used for RAG web search.

``get_web_loader`` picks a safe loader based on the configured
``WEB_LOADER_ENGINE``: the built-in ``SafeWebBaseLoader`` (default), or
Playwright, FireCrawl, or Tavily. The Safe* wrappers add URL validation,
SSL certificate verification, rate limiting, and per-URL error tolerance
on top of the underlying langchain loaders.
"""

import asyncio
import logging
import socket
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
)

import aiohttp
import certifi
import validators
from langchain_community.document_loaders import PlaywrightURLLoader, WebBaseLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.firecrawl import FireCrawlLoader
from langchain_core.documents import Document

from jyotigpt.config import (
    ENABLE_RAG_LOCAL_WEB_FETCH,
    FIRECRAWL_API_BASE_URL,
    FIRECRAWL_API_KEY,
    PLAYWRIGHT_TIMEOUT,
    PLAYWRIGHT_WS_URL,
    TAVILY_API_KEY,
    TAVILY_EXTRACT_DEPTH,
    WEB_LOADER_ENGINE,
)
from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.retrieval.loaders.tavily import TavilyLoader

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


# --- URL safety -----------------------------------------------------------


def validate_url(url: Union[str, Sequence[str]]):
    """Check the URL is well-formed and (when local fetch is disabled) public."""
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)
        if not ENABLE_RAG_LOCAL_WEB_FETCH:
            # Local fetch disabled: reject URLs pointing at private addresses.
            # (Still theoretically vulnerable to DNS rebinding — the upstream
            # loader does its own resolution too.)
            parsed_url = urllib.parse.urlparse(url)
            ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
            for ip in ipv4_addresses:
                if validators.ipv4(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
            for ip in ipv6_addresses:
                if validators.ipv6(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
        return True
    elif isinstance(url, Sequence):
        return all(validate_url(u) for u in url)
    else:
        return False


def safe_validate_urls(url: Sequence[str]) -> Sequence[str]:
    """Drop URLs that fail validation instead of raising."""
    valid_urls = []
    for u in url:
        try:
            if validate_url(u):
                valid_urls.append(u)
        except ValueError:
            continue
    return valid_urls


def resolve_hostname(hostname):
    """Resolve a hostname to its IPv4 and IPv6 address lists."""
    addr_info = socket.getaddrinfo(hostname, None)

    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


def extract_metadata(soup, url):
    """Build the standard metadata dict (title, description, language)."""
    metadata = {"source": url}
    if title := soup.find("title"):
        metadata["title"] = title.get_text()
    if description := soup.find("meta", attrs={"name": "description"}):
        metadata["description"] = description.get("content", "No description found.")
    if html := soup.find("html"):
        metadata["language"] = html.get("lang", "No language found.")
    return metadata


def verify_ssl_cert(url: str) -> bool:
    """Check the site's certificate against the system CA store."""
    if not url.startswith("https://"):
        return True

    try:
        hostname = url.split("://")[-1].split("/")[0]
        context = ssl.create_default_context(cafile=certifi.where())
        with context.wrap_socket(ssl.socket(), server_hostname=hostname) as s:
            s.connect((hostname, 443))
        return True
    except ssl.SSLError:
        return False
    except Exception as e:
        log.warning(f"SSL verification failed for {url}: {str(e)}")
        return False


# --- shared safety mixins --------------------------------------------------


class RateLimitMixin:
    """Throttle requests to ``requests_per_second`` (async and sync)."""

    async def _wait_for_rate_limit(self):
        if self.requests_per_second and self.last_request_time:
            min_interval = timedelta(seconds=1.0 / self.requests_per_second)
            time_since_last = datetime.now() - self.last_request_time
            if time_since_last < min_interval:
                await asyncio.sleep((min_interval - time_since_last).total_seconds())
        self.last_request_time = datetime.now()

    def _sync_wait_for_rate_limit(self):
        if self.requests_per_second and self.last_request_time:
            min_interval = timedelta(seconds=1.0 / self.requests_per_second)
            time_since_last = datetime.now() - self.last_request_time
            if time_since_last < min_interval:
                time.sleep((min_interval - time_since_last).total_seconds())
        self.last_request_time = datetime.now()


class URLProcessingMixin:
    """SSL check + rate-limit gate for both sync and async load paths."""

    def _verify_ssl_cert(self, url: str) -> bool:
        return verify_ssl_cert(url)

    async def _safe_process_url(self, url: str) -> bool:
        if self.verify_ssl and not self._verify_ssl_cert(url):
            raise ValueError(f"SSL certificate verification failed for {url}")
        await self._wait_for_rate_limit()
        return True

    def _safe_process_url_sync(self, url: str) -> bool:
        if self.verify_ssl and not self._verify_ssl_cert(url):
            raise ValueError(f"SSL certificate verification failed for {url}")
        self._sync_wait_for_rate_limit()
        return True


def _env_proxy_server(proxy: Optional[Dict[str, str]], trust_env: bool):
    """Fill ``proxy["server"]`` from environment variables when asked to."""
    proxy_server = proxy.get("server") if proxy else None
    if trust_env and not proxy_server:
        env_proxies = urllib.request.getproxies()
        env_proxy_server = env_proxies.get("https") or env_proxies.get("http")
        if env_proxy_server:
            if proxy:
                proxy["server"] = env_proxy_server
            else:
                proxy = {"server": env_proxy_server}
    return proxy


# --- safe loader wrappers ---------------------------------------------------


class SafeFireCrawlLoader(BaseLoader, RateLimitMixin, URLProcessingMixin):
    """Concurrent loader for FireCrawl ``crawl``/``scrape``/``map`` modes."""

    def __init__(
        self,
        web_paths,
        verify_ssl: bool = True,
        trust_env: bool = False,
        requests_per_second: Optional[float] = None,
        continue_on_failure: bool = True,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        mode: Literal["crawl", "scrape", "map"] = "crawl",
        proxy: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ):
        proxy = _env_proxy_server(proxy, trust_env)
        self.web_paths = web_paths
        self.verify_ssl = verify_ssl
        self.requests_per_second = requests_per_second
        self.last_request_time = None
        self.trust_env = trust_env
        self.continue_on_failure = continue_on_failure
        self.api_key = api_key
        self.api_url = api_url
        self.mode = mode
        self.params = params

    def _make_loader(self, url: str):
        return FireCrawlLoader(
            url=url,
            api_key=self.api_key,
            api_url=self.api_url,
            mode=self.mode,
            params=self.params,
        )

    def lazy_load(self) -> Iterator[Document]:
        for url in self.web_paths:
            try:
                self._safe_process_url_sync(url)
                yield from self._make_loader(url).lazy_load()
            except Exception as e:
                if self.continue_on_failure:
                    log.exception(f"Error loading {url}: {e}")
                    continue
                raise e

    async def alazy_load(self) -> AsyncIterator[Document]:
        for url in self.web_paths:
            try:
                await self._safe_process_url(url)
                async for document in self._make_loader(url).alazy_load():
                    yield document
            except Exception as e:
                if self.continue_on_failure:
                    log.exception(f"Error loading {url}: {e}")
                    continue
                raise e


class SafeTavilyLoader(BaseLoader, RateLimitMixin, URLProcessingMixin):
    """Rate-limited, SSL-checked wrapper around ``TavilyLoader``."""

    def __init__(
        self,
        web_paths: Union[str, List[str]],
        api_key: str,
        extract_depth: Literal["basic", "advanced"] = "basic",
        continue_on_failure: bool = True,
        requests_per_second: Optional[float] = None,
        verify_ssl: bool = True,
        trust_env: bool = False,
        proxy: Optional[Dict[str, str]] = None,
    ):
        proxy = _env_proxy_server(proxy, trust_env)
        self.web_paths = web_paths if isinstance(web_paths, list) else [web_paths]
        self.api_key = api_key
        self.extract_depth = extract_depth
        self.continue_on_failure = continue_on_failure
        self.verify_ssl = verify_ssl
        self.trust_env = trust_env
        self.proxy = proxy
        self.requests_per_second = requests_per_second
        self.last_request_time = None

    def _validated_urls(self, paths) -> List[str]:
        valid_urls = []
        for url in paths:
            try:
                self._safe_process_url_sync(url)
                valid_urls.append(url)
            except Exception as e:
                log.warning(f"SSL verification failed for {url}: {str(e)}")
                if not self.continue_on_failure:
                    raise e
        if not valid_urls:
            if self.continue_on_failure:
                log.warning("No valid URLs to process after SSL verification")
                return []
            raise ValueError("No valid URLs to process after SSL verification")
        return valid_urls

    def _make_loader(self, urls):
        return TavilyLoader(
            urls=urls,
            api_key=self.api_key,
            extract_depth=self.extract_depth,
            continue_on_failure=self.continue_on_failure,
        )

    def lazy_load(self) -> Iterator[Document]:
        valid_urls = self._validated_urls(self.web_paths)
        if not valid_urls:
            return
        try:
            yield from self._make_loader(valid_urls).lazy_load()
        except Exception as e:
            if self.continue_on_failure:
                log.exception(f"Error extracting content from URLs: {e}")
            else:
                raise e

    async def alazy_load(self) -> AsyncIterator[Document]:
        valid_urls = []
        for url in self.web_paths:
            try:
                await self._safe_process_url(url)
                valid_urls.append(url)
            except Exception as e:
                log.warning(f"SSL verification failed for {url}: {str(e)}")
                if not self.continue_on_failure:
                    raise e
        if not valid_urls:
            if self.continue_on_failure:
                log.warning("No valid URLs to process after SSL verification")
                return
            raise ValueError("No valid URLs to process after SSL verification")

        try:
            async for document in self._make_loader(valid_urls).alazy_load():
                yield document
        except Exception as e:
            if self.continue_on_failure:
                log.exception(f"Error loading URLs: {e}")
            else:
                raise e


class SafePlaywrightURLLoader(PlaywrightURLLoader, RateLimitMixin, URLProcessingMixin):
    """Playwright loader with SSL checks, rate limiting, and remote browser.

    When ``playwright_ws_url`` is given the browser is attached to the
    remote endpoint; otherwise a local headless Chromium is launched.
    """

    def __init__(
        self,
        web_paths: List[str],
        verify_ssl: bool = True,
        trust_env: bool = False,
        requests_per_second: Optional[float] = None,
        continue_on_failure: bool = True,
        headless: bool = True,
        remove_selectors: Optional[List[str]] = None,
        proxy: Optional[Dict[str, str]] = None,
        playwright_ws_url: Optional[str] = None,
        playwright_timeout: Optional[int] = 10000,
    ):
        proxy = _env_proxy_server(proxy, trust_env)

        # Remote browsers already manage their own rendering context.
        super().__init__(
            urls=web_paths,
            continue_on_failure=continue_on_failure,
            headless=headless if playwright_ws_url is None else False,
            remove_selectors=remove_selectors,
            proxy=proxy,
        )
        self.verify_ssl = verify_ssl
        self.requests_per_second = requests_per_second
        self.last_request_time = None
        self.playwright_ws_url = playwright_ws_url
        self.trust_env = trust_env
        self.playwright_timeout = playwright_timeout

    def _browser_for(self, p):
        if self.playwright_ws_url:
            return p.chromium.connect(self.playwright_ws_url)
        return p.chromium.launch(headless=self.headless, proxy=self.proxy)

    def lazy_load(self) -> Iterator[Document]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = self._browser_for(p)
            try:
                for url in self.urls:
                    try:
                        self._safe_process_url_sync(url)
                        page = browser.new_page()
                        response = page.goto(url, timeout=self.playwright_timeout)
                        if response is None:
                            raise ValueError(f"page.goto() returned None for url {url}")

                        text = self.evaluator.evaluate(page, browser, response)
                        yield Document(
                            page_content=text, metadata={"source": url}
                        )
                    except Exception as e:
                        if self.continue_on_failure:
                            log.exception(f"Error loading {url}: {e}")
                            continue
                        raise e
            finally:
                browser.close()

    async def alazy_load(self) -> AsyncIterator[Document]:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            if self.playwright_ws_url:
                browser = await p.chromium.connect(self.playwright_ws_url)
            else:
                browser = await p.chromium.launch(
                    headless=self.headless, proxy=self.proxy
                )
            try:
                for url in self.urls:
                    try:
                        await self._safe_process_url(url)
                        page = await browser.new_page()
                        response = await page.goto(url, timeout=self.playwright_timeout)
                        if response is None:
                            raise ValueError(f"page.goto() returned None for url {url}")

                        text = await self.evaluator.evaluate_async(
                            page, browser, response
                        )
                        yield Document(page_content=text, metadata={"source": url})
                    except Exception as e:
                        if self.continue_on_failure:
                            log.exception(f"Error loading {url}: {e}")
                            continue
                        raise e
            finally:
                await browser.close()


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with trust-env support and per-URL error tolerance."""

    def __init__(self, trust_env: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trust_env = trust_env

    async def _fetch(
        self, url: str, retries: int = 3, cooldown: int = 2, backoff: float = 1.5
    ) -> str:
        async with aiohttp.ClientSession(trust_env=self.trust_env) as session:
            for i in range(retries):
                try:
                    kwargs: Dict = dict(
                        headers=self.session.headers,
                        cookies=self.session.cookies.get_dict(),
                    )
                    if not self.session.verify:
                        kwargs["ssl"] = False

                    async with session.get(
                        url, **(self.requests_kwargs | kwargs)
                    ) as response:
                        if self.raise_for_status:
                            response.raise_for_status()
                        return await response.text()
                except aiohttp.ClientConnectionError as e:
                    if i == retries - 1:
                        raise
                    else:
                        log.warning(
                            f"Error fetching {url} with attempt "
                            f"{i + 1}/{retries}: {e}. Retrying..."
                        )
                        await asyncio.sleep(cooldown * backoff**i)
        raise ValueError("retry count exceeded")

    def _unpack_fetch_results(
        self, results: Any, urls: List[str], parser: Union[str, None] = None
    ) -> List[Any]:
        from bs4 import BeautifulSoup

        final_results = []
        for i, result in enumerate(results):
            url = urls[i]
            if parser is None:
                if url.endswith(".xml"):
                    parser = "xml"
                else:
                    parser = self.default_parser
                self._check_parser(parser)
            final_results.append(BeautifulSoup(result, parser, **self.bs_kwargs))
        return final_results

    async def ascrape_all(
        self, urls: List[str], parser: Union[str, None] = None
    ) -> List[Any]:
        results = await self.fetch_all(urls)
        return self._unpack_fetch_results(results, urls, parser=parser)

    def lazy_load(self) -> Iterator[Document]:
        for path in self.web_paths:
            try:
                soup = self._scrape(path, bs_kwargs=self.bs_kwargs)
                text = soup.get_text(**self.bs_get_text_kwargs)
                yield Document(
                    page_content=text, metadata=extract_metadata(soup, path)
                )
            except Exception as e:
                log.exception(f"Error loading {path}: {e}")

    async def alazy_load(self) -> AsyncIterator[Document]:
        results = await self.ascrape_all(self.web_paths)
        for path, soup in zip(self.web_paths, results):
            text = soup.get_text(**self.bs_get_text_kwargs)
            yield Document(page_content=text, metadata=extract_metadata(soup, path))

    async def aload(self) -> list[Document]:
        return [document async for document in self.alazy_load()]


# --- loader factory --------------------------------------------------------


def get_web_loader(
    urls: Union[str, Sequence[str]],
    verify_ssl: bool = True,
    requests_per_second: int = 2,
    trust_env: bool = False,
):
    safe_urls = safe_validate_urls([urls] if isinstance(urls, str) else urls)

    web_loader_args = {
        "web_paths": safe_urls,
        "verify_ssl": verify_ssl,
        "requests_per_second": requests_per_second,
        "continue_on_failure": True,
        "trust_env": trust_env,
    }

    WebLoaderClass = None
    if WEB_LOADER_ENGINE.value in ("", "safe_web"):
        WebLoaderClass = SafeWebBaseLoader
    if WEB_LOADER_ENGINE.value == "playwright":
        WebLoaderClass = SafePlaywrightURLLoader
        web_loader_args["playwright_timeout"] = PLAYWRIGHT_TIMEOUT.value * 1000
        if PLAYWRIGHT_WS_URL.value:
            web_loader_args["playwright_ws_url"] = PLAYWRIGHT_WS_URL.value
    if WEB_LOADER_ENGINE.value == "firecrawl":
        WebLoaderClass = SafeFireCrawlLoader
        web_loader_args["api_key"] = FIRECRAWL_API_KEY.value
        web_loader_args["api_url"] = FIRECRAWL_API_BASE_URL.value
    if WEB_LOADER_ENGINE.value == "tavily":
        WebLoaderClass = SafeTavilyLoader
        web_loader_args["api_key"] = TAVILY_API_KEY.value
        web_loader_args["extract_depth"] = TAVILY_EXTRACT_DEPTH.value

    if WebLoaderClass is None:
        raise ValueError(
            f"Invalid WEB_LOADER_ENGINE: {WEB_LOADER_ENGINE.value}. "
            "Please set it to 'safe_web', 'playwright', 'firecrawl', or 'tavily'."
        )

    web_loader = WebLoaderClass(**web_loader_args)

    log.debug(
        "Using WEB_LOADER_ENGINE %s for %s URLs",
        web_loader.__class__.__name__,
        len(safe_urls),
    )

    return web_loader
