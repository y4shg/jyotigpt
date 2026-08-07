"""PDF generation for chat transcripts.

Transforms a chat's title and markdown messages into an HTML document and
renders it to a PDF via fpdf2. Fonts include Latin plus Korean/Japanese/
Simplified-Chinese fallbacks and an emoji font.
"""

from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from fpdf import FPDF

from jyotigpt.env import FONTS_DIR, STATIC_DIR
from jyotigpt.models.chats import ChatTitleMessagesForm


class PDFGenerator:
    """Build a PDF document from chat title and messages."""

    def __init__(self, form_data: ChatTitleMessagesForm):
        self.html_body = None
        self.messages_html = None
        self.form_data = form_data

        self.css = Path(STATIC_DIR / "assets" / "pdf-style.css").read_text()

    def format_timestamp(self, timestamp: float) -> str:
        """Convert a UNIX timestamp to ``YYYY-MM-DD, HH:MM:SS``, else empty."""
        try:
            date_time = datetime.fromtimestamp(timestamp)
            return date_time.strftime("%Y-%m-%d, %H:%M:%S")
        except (ValueError, TypeError):
            return ""

    def _build_html_message(self, message: Dict[str, Any]) -> str:
        """Build the HTML fragment for a single chat message."""
        role = escape(message.get("role", "user"))
        content = escape(message.get("content", ""))
        timestamp = message.get("timestamp")

        model = escape(message.get("model") if role == "assistant" else "")

        date_str = escape(self.format_timestamp(timestamp) if timestamp else "")

        content = content.replace("\n", "<br/>")
        return f"""
            <div>
                <div>
                    <h4>
                        <strong>{role.title()}</strong>
                        <span style="font-size: 12px;">{model}</span>
                    </h4>
                    <div> {date_str} </div>
                </div>
                <br/>
                <br/>

                <div>
                    {content}
                </div>
            </div>
            <br/>
          """

    def _generate_html_body(self) -> str:
        """Wrap the assembled messages HTML in a full document body."""
        escaped_title = escape(self.form_data.title)
        return f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            </head>
            <body>
            <div>
                <div>
                    <h2>{escaped_title}</h2>
                    {self.messages_html}
                </div>
            </div>
            </body>
        </html>
        """

    def _resolve_fonts_dir(self) -> Path:
        """Locate the bundled fonts directory across deployment layouts."""
        global FONTS_DIR

        # `pip install jyotigpt` installs static assets into site-packages.
        if not FONTS_DIR.exists():
            import site

            FONTS_DIR = Path(site.getsitepackages()[0]) / "static" / "fonts"
        # `pip install -e .` / running from the repo root.
        if not FONTS_DIR.exists():
            FONTS_DIR = Path(".") / "backend" / "static" / "fonts"

        return FONTS_DIR

    def generate_chat_pdf(self) -> bytes:
        """Generate and return the PDF bytes for the chat transcript."""
        try:
            fonts_dir = self._resolve_fonts_dir()

            pdf = FPDF()
            pdf.add_page()

            pdf.add_font("NotoSans", "", f"{fonts_dir}/NotoSans-Regular.ttf")
            pdf.add_font("NotoSans", "b", f"{fonts_dir}/NotoSans-Bold.ttf")
            pdf.add_font("NotoSans", "i", f"{fonts_dir}/NotoSans-Italic.ttf")
            pdf.add_font("NotoSansKR", "", f"{fonts_dir}/NotoSansKR-Regular.ttf")
            pdf.add_font("NotoSansJP", "", f"{fonts_dir}/NotoSansJP-Regular.ttf")
            pdf.add_font("NotoSansSC", "", f"{fonts_dir}/NotoSansSC-Regular.ttf")
            pdf.add_font("Twemoji", "", f"{fonts_dir}/Twemoji.ttf")

            pdf.set_font("NotoSans", size=12)
            pdf.set_fallback_fonts(
                ["NotoSansKR", "NotoSansJP", "NotoSansSC", "Twemoji"]
            )

            pdf.set_auto_page_break(auto=True, margin=15)

            messages_html_list: List[str] = [
                self._build_html_message(msg) for msg in self.form_data.messages
            ]
            self.messages_html = "<div>" + "".join(messages_html_list) + "</div>"

            self.html_body = self._generate_html_body()

            pdf.write_html(self.html_body)

            return bytes(pdf.output())
        except Exception as e:
            raise e
