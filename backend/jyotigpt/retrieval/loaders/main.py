"""Document loaders: pick the right extractor for a file.

The ``Loader`` dispatches on the configured engine (tika, docling,
document_intelligence, mistral_ocr) and then on file extension / MIME
type, delegating to the appropriate langchain-community loader or to the
custom HTTP loaders below. All returned documents are run through
``ftfy.fix_text`` to repair mojibake.
"""

import logging
import sys

import ftfy
import requests

from langchain_community.document_loaders import (
    AzureAIDocumentIntelligenceLoader,
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    OutlookMessageLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredRSTLoader,
    UnstructuredXMLLoader,
    YoutubeLoader,
)
from langchain_core.documents import Document

from jyotigpt.env import GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS
from jyotigpt.retrieval.loaders.mistral import MistralLoader

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

# Extensions treated as plain source code / text files.
known_source_ext = [
    "go",
    "py",
    "java",
    "sh",
    "bat",
    "ps1",
    "cmd",
    "js",
    "ts",
    "css",
    "cpp",
    "hpp",
    "h",
    "c",
    "cs",
    "sql",
    "log",
    "ini",
    "pl",
    "pm",
    "r",
    "dart",
    "dockerfile",
    "env",
    "php",
    "hs",
    "hsc",
    "lua",
    "nginxconf",
    "conf",
    "m",
    "mm",
    "plsql",
    "perl",
    "rb",
    "rs",
    "db2",
    "scala",
    "bash",
    "swift",
    "vue",
    "svelte",
    "msg",
    "ex",
    "exs",
    "erl",
    "tsx",
    "jsx",
    "hs",
    "lhs",
    "json",
]


class TikaLoader:
    """Extract text from a file via the Apache Tika server's REST API."""

    def __init__(self, url, file_path, mime_type=None):
        self.url = url
        self.file_path = file_path
        self.mime_type = mime_type

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            data = f.read()

        headers = {"Content-Type": self.mime_type} if self.mime_type is not None else {}

        endpoint = self.url.rstrip("/") + "/tika/text"
        r = requests.put(endpoint, data=data, headers=headers)

        if not r.ok:
            raise Exception(f"Error calling Tika: {r.reason}")

        raw_metadata = r.json()
        text = raw_metadata.get("X-TIKA:content", "<No text content found>").strip()

        if "Content-Type" in raw_metadata:
            headers["Content-Type"] = raw_metadata["Content-Type"]

        log.debug("Tika extracted text: %s", text)
        return [Document(page_content=text, metadata=headers)]


class DoclingLoader:
    """Extract text from a file via a Docling server's convert API."""

    def __init__(self, url, file_path=None, mime_type=None):
        self.url = url.rstrip("/")
        self.file_path = file_path
        self.mime_type = mime_type

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            files = {
                "files": (
                    self.file_path,
                    f,
                    self.mime_type or "application/octet-stream",
                )
            }
            params = {
                "image_export_mode": "placeholder",
                "table_mode": "accurate",
            }
            endpoint = f"{self.url}/v1alpha/convert/file"
            r = requests.post(endpoint, files=files, data=params)

        if not r.ok:
            error_msg = f"Error calling Docling API: {r.reason}"
            if r.text:
                try:
                    error_data = r.json()
                    if "detail" in error_data:
                        error_msg += f" - {error_data['detail']}"
                except Exception:
                    error_msg += f" - {r.text}"
            raise Exception(f"Error calling Docling: {error_msg}")

        result = r.json()
        document_data = result.get("document", {})
        text = document_data.get("md_content", "<No text content found>")

        metadata = {"Content-Type": self.mime_type} if self.mime_type else {}
        log.debug("Docling extracted text: %s", text)
        return [Document(page_content=text, metadata=metadata)]


class Loader:
    """Pick a loader for ``filename``/``file_content_type`` and run it."""

    def __init__(self, engine: str = "", **kwargs):
        self.engine = engine
        self.kwargs = kwargs

    def load(
        self, filename: str, file_content_type: str, file_path: str
    ) -> list[Document]:
        loader = self._get_loader(filename, file_content_type, file_path)
        docs = loader.load()

        return [
            Document(
                page_content=ftfy.fix_text(doc.page_content), metadata=doc.metadata
            )
            for doc in docs
        ]

    # --- dispatch helpers ------------------------------------------------

    def _is_text_file(self, file_ext: str, file_content_type: str) -> bool:
        return file_ext in known_source_ext or (
            file_content_type and file_content_type.find("text/") >= 0
        )

    def _engine_loader(self, file_ext: str, file_content_type: str, file_path: str):
        """Loader chosen by the configured extraction engine, if any."""
        if self.engine == "tika" and self.kwargs.get("TIKA_SERVER_URL"):
            if self._is_text_file(file_ext, file_content_type):
                return TextLoader(file_path, autodetect_encoding=True)
            return TikaLoader(
                url=self.kwargs.get("TIKA_SERVER_URL"),
                file_path=file_path,
                mime_type=file_content_type,
            )

        if self.engine == "docling" and self.kwargs.get("DOCLING_SERVER_URL"):
            if self._is_text_file(file_ext, file_content_type):
                return TextLoader(file_path, autodetect_encoding=True)
            return DoclingLoader(
                url=self.kwargs.get("DOCLING_SERVER_URL"),
                file_path=file_path,
                mime_type=file_content_type,
            )

        if (
            self.engine == "document_intelligence"
            and self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT") != ""
            and self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY") != ""
            and (
                file_ext in ["pdf", "xls", "xlsx", "docx", "ppt", "pptx"]
                or file_content_type
                in [
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.ms-powerpoint",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ]
            )
        ):
            return AzureAIDocumentIntelligenceLoader(
                file_path=file_path,
                api_endpoint=self.kwargs.get("DOCUMENT_INTELLIGENCE_ENDPOINT"),
                api_key=self.kwargs.get("DOCUMENT_INTELLIGENCE_KEY"),
            )

        if (
            self.engine == "mistral_ocr"
            and self.kwargs.get("MISTRAL_OCR_API_KEY") != ""
            and file_ext in ["pdf"]  # Mistral OCR supports PDFs (and images)
        ):
            return MistralLoader(
                api_key=self.kwargs.get("MISTRAL_OCR_API_KEY"), file_path=file_path
            )

        return None

    def _get_loader(self, filename: str, file_content_type: str, file_path: str):
        file_ext = filename.split(".")[-1].lower()

        engine_loader = self._engine_loader(file_ext, file_content_type, file_path)
        if engine_loader is not None:
            return engine_loader

        # Fall back to extension / MIME type matching.
        if file_ext == "pdf":
            return PyPDFLoader(
                file_path, extract_images=self.kwargs.get("PDF_EXTRACT_IMAGES")
            )
        if file_ext == "csv":
            return CSVLoader(file_path, autodetect_encoding=True)
        if file_ext == "rst":
            return UnstructuredRSTLoader(file_path, mode="elements")
        if file_ext == "xml":
            return UnstructuredXMLLoader(file_path)
        if file_ext in ["htm", "html"]:
            return BSHTMLLoader(file_path, open_encoding="unicode_escape")
        if file_ext == "md":
            return TextLoader(file_path, autodetect_encoding=True)
        if file_content_type == "application/epub+zip":
            return UnstructuredEPubLoader(file_path)
        if (
            file_content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or file_ext == "docx"
        ):
            return Docx2txtLoader(file_path)
        if file_content_type in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ] or file_ext in ["xls", "xlsx"]:
            return UnstructuredExcelLoader(file_path)
        if file_content_type in [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ] or file_ext in ["ppt", "pptx"]:
            return UnstructuredPowerPointLoader(file_path)
        if file_ext == "msg":
            return OutlookMessageLoader(file_path)
        return TextLoader(file_path, autodetect_encoding=True)
