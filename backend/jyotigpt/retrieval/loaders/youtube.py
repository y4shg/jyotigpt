"""YouTube transcript loader.

Resolves a YouTube watch URL (or video ID) to its transcript text via the
``youtube-transcript-api`` package. The video is identified locally first
by parsing the URL; lookups go through the optional proxy when set.
"""

import logging
from typing import Any, Dict, Generator, List, Optional, Sequence, Union
from urllib.parse import parse_qs, urlparse

from langchain_core.documents import Document
from jyotigpt.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_NETLOCS = {
    "youtu.be",
    "m.youtube.com",
    "youtube.com",
    "www.youtube.com",
    "www.youtube-nocookie.com",
    "vid.plus",
}


def _parse_video_id(url: str) -> Optional[str]:
    """Extract the 11-character video ID from a YouTube URL, if valid."""
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ALLOWED_SCHEMES:
        return None

    if parsed_url.netloc not in ALLOWED_NETLOCS:
        return None

    path = parsed_url.path

    if path.endswith("/watch"):
        parsed_query = parse_qs(parsed_url.query)
        if "v" not in parsed_query:
            return None
        video_id = parsed_query["v"][0]
    else:
        path = parsed_url.path.lstrip("/")
        video_id = path.split("/")[-1]

    # Video IDs are 11 characters long.
    if len(video_id) != 11:
        return None

    return video_id


class YoutubeLoader:
    """Load YouTube video transcripts as Documents."""

    def __init__(
        self,
        video_id: str,
        language: Union[str, Sequence[str]] = "en",
        proxy_url: Optional[str] = None,
    ):
        _video_id = _parse_video_id(video_id)
        self.video_id = _video_id if _video_id is not None else video_id
        self._metadata = {"source": video_id}
        self.language = [language] if isinstance(language, str) else list(language)
        self.proxy_url = proxy_url

    def load(self) -> List[Document]:
        """Fetch the transcript and wrap it in a single Document."""
        try:
            from youtube_transcript_api import (
                NoTranscriptFound,
                TranscriptsDisabled,
                YouTubeTranscriptApi,
            )
        except ImportError:
            raise ImportError(
                'Could not import "youtube_transcript_api" Python package. '
                "Please install it with `pip install youtube-transcript-api`."
            )

        if self.proxy_url:
            youtube_proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }
            # Don't log the full URL — it may contain credentials.
            log.debug(f"Using proxy URL: {self.proxy_url[:14]}...")
        else:
            youtube_proxies = None

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(
                self.video_id, proxies=youtube_proxies
            )
        except Exception as e:
            log.exception("Loading YouTube transcript failed")
            return []

        try:
            transcript = transcript_list.find_transcript(self.language)
        except NoTranscriptFound:
            transcript = transcript_list.find_transcript(["en"])

        transcript_pieces: List[Dict[str, Any]] = transcript.fetch()
        transcript = " ".join(
            piece.text.strip(" ") for piece in transcript_pieces
        )
        return [Document(page_content=transcript, metadata=self._metadata)]
