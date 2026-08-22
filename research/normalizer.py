"""Safe HTML to Markdown / Clean Text Normalizer for Phase 4.1."""

from html import unescape
from html.parser import HTMLParser
import re


class _HTMLToMarkdownParser(HTMLParser):
    """Internal streaming HTML parser converting DOM elements into clean Markdown."""

    IGNORED_TAGS: set[str] = {
        "script",
        "style",
        "noscript",
        "iframe",
        "object",
        "embed",
        "svg",
        "canvas",
        "form",
        "nav",
        "footer",
        "header",
        "aside",
        "button",
        "input",
        "select",
        "textarea",
    }

    BLOCK_TAGS: set[str] = {
        "p",
        "div",
        "section",
        "article",
        "main",
        "blockquote",
        "pre",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__()
        self.output_chunks: list[str] = []
        self.title: str = ""
        self.first_h1: str = ""
        self.in_title: bool = False
        self.in_h1: bool = False
        self.ignored_stack: list[str] = []
        self.current_heading_level: int = 0
        self.in_list_item: bool = False
        self.in_code_block: bool = False
        self.in_table: bool = False
        self.table_row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()

        if tag_lower in self.IGNORED_TAGS:
            self.ignored_stack.append(tag_lower)
            return

        if self.ignored_stack:
            return

        if tag_lower == "title":
            self.in_title = True
            return

        if tag_lower == "h1":
            self.in_h1 = True

        if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.current_heading_level = int(tag_lower[1])
            self.output_chunks.append(f"\n\n{'#' * self.current_heading_level} ")
            return

        if tag_lower in self.BLOCK_TAGS:
            self.output_chunks.append("\n\n")
            return

        if tag_lower == "br":
            self.output_chunks.append("\n")
            return

        if tag_lower == "li":
            self.in_list_item = True
            self.output_chunks.append("\n- ")
            return

        if tag_lower == "blockquote":
            self.output_chunks.append("\n> ")
            return

        if tag_lower in ("pre", "code"):
            self.in_code_block = True
            self.output_chunks.append(" `")
            return

        if tag_lower == "tr":
            self.table_row = []

        if tag_lower in ("td", "th"):
            self.output_chunks.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        if tag_lower in self.IGNORED_TAGS and self.ignored_stack and self.ignored_stack[-1] == tag_lower:
            self.ignored_stack.pop()
            return

        if self.ignored_stack:
            return

        if tag_lower == "title":
            self.in_title = False
            return

        if tag_lower == "h1":
            self.in_h1 = False

        if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.current_heading_level = 0
            self.output_chunks.append("\n")
            return

        if tag_lower == "li":
            self.in_list_item = False
            return

        if tag_lower in ("pre", "code"):
            self.in_code_block = False
            self.output_chunks.append("` ")
            return

        if tag_lower == "tr":
            self.output_chunks.append(" |\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_stack:
            return

        clean_text = unescape(data)

        if self.in_title:
            self.title += clean_text.strip() + " "
            return

        if self.in_h1 and not self.first_h1:
            self.first_h1 += clean_text.strip() + " "

        if clean_text:
            self.output_chunks.append(clean_text)


class HTMLNormalizer:
    """Sanitizes raw HTML content and extracts clean, safe Markdown text."""

    @classmethod
    def normalize_html(cls, raw_html: str) -> tuple[str, str]:
        """Convert HTML string into (title, markdown_content).

        Strips active scripts, style tags, and dangerous markup deterministically.
        """
        if not raw_html or not isinstance(raw_html, str):
            return ("", "")

        parser = _HTMLToMarkdownParser()
        try:
            parser.feed(raw_html)
            parser.close()
        except Exception:
            clean_fallback = re.sub(r"<[^>]+>", " ", raw_html)
            return ("Untitled", unescape(clean_fallback).strip())

        title = parser.title.strip() or parser.first_h1.strip() or "Untitled Webpage"
        raw_markdown = "".join(parser.output_chunks)

        clean_lines: list[str] = []
        for line in raw_markdown.splitlines():
            stripped = line.strip()
            if stripped:
                clean_lines.append(stripped)
            elif clean_lines and clean_lines[-1] != "":
                clean_lines.append("")

        markdown_content = "\n".join(clean_lines).strip()
        return (title, markdown_content)
