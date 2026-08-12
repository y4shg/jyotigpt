"""Document text handling: extraction from common file types + chunking.

Extraction supports plain text, markdown, PDF (via pypdf) and Word (via
python-docx). Anything else is stored but not parsed. Chunking is
character-based with overlap, preferring paragraph boundaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".xml", ".log"}


def extract_text(path: Path, content_type: str = "") -> str:
    """Return extracted text for a stored upload, or "" when unsupported."""
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    if suffix in {".docx", ".doc"}:
        try:
            import docx

            document = docx.Document(str(path))
            return "\n".join(p.text for p in document.paragraphs)
        except Exception:
            return ""
    return ""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """Split text into overlapping character chunks at paragraph boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    step = max(chunk_size - overlap, 200)
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # back up to the nearest paragraph/line break within 20% of the chunk
            cut = max(
                text.rfind("\n\n", start + step, end),
                text.rfind("\n", start + step, end),
            )
            if cut != -1:
                end = cut
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + step)
    return chunks


def split_source_ref(filename: str, chunk_index: int) -> str:
    return f"{filename}#{chunk_index}"
