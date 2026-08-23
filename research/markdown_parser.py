"""Secure Markdown Document Parser and Section Extractor for Phase 4 Research."""

import re
from typing import Any
from core.exceptions import DocumentFormatError, DocumentSizeExceededError
from research.normalizer import TextNormalizer


class SecureMarkdownParser:
    """Safely extracts structured text, sections, headings, and metadata from Markdown documents."""

    MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

    # Dangerous inline HTML tags to strip completely
    _DANGEROUS_HTML_REGEX = re.compile(
        r"<(?:script|style|iframe|object|embed|svg|canvas|form|button|input|textarea)[^>]*>.*?</(?:script|style|iframe|object|embed|svg|canvas|form|button|input|textarea)>|"
        r"<(?:script|style|iframe|object|embed|svg|canvas|form|button|input|textarea)[^>]*/>|"
        r"<\?[^>]*\?>|"
        r"<!--.*?-->",
        re.IGNORECASE | re.DOTALL,
    )

    _EVENT_HANDLER_REGEX = re.compile(r"""\s+on\w+\s*=\s*(?:'[^']*'|"[^"]*"|[^\s>]+)""", re.IGNORECASE)
    _FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    _HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    _LINK_CITATION_REGEX = re.compile(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)")

    @classmethod
    def parse_markdown_text(
        cls,
        raw_markdown: str,
        source_name: str = "document.md",
    ) -> dict[str, Any]:
        """Parse raw markdown text into structured sections, links, and sanitized content."""
        if raw_markdown is None or not isinstance(raw_markdown, str):
            raise DocumentFormatError(f"Markdown content for '{source_name}' is empty or invalid.")

        raw_bytes = raw_markdown.encode("utf-8")
        if len(raw_bytes) > cls.MAX_FILE_SIZE_BYTES:
            raise DocumentSizeExceededError(
                f"Markdown file size ({len(raw_bytes)} bytes) exceeds maximum limit of {cls.MAX_FILE_SIZE_BYTES} bytes."
            )

        # 1. Strip Dangerous HTML and Script Tags
        sanitized = cls._DANGEROUS_HTML_REGEX.sub("", raw_markdown)
        sanitized = cls._EVENT_HANDLER_REGEX.sub("", sanitized)

        # 2. Extract YAML Frontmatter if present
        title: str = source_name
        author: str | None = None
        fm_match = cls._FRONTMATTER_REGEX.match(sanitized)
        body_text = sanitized
        if fm_match:
            frontmatter_raw = fm_match.group(1)
            body_text = sanitized[fm_match.end():]
            # Simple safe key-value extraction
            for line in frontmatter_raw.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip().strip("'\"")
                    if key == "title" and val:
                        title = val
                    elif key == "author" and val:
                        author = val

        # 3. Extract Headings and Structure Sections
        lines = body_text.splitlines()
        sections: list[dict[str, Any]] = []
        current_section_title = "Overview"
        current_section_lines: list[str] = []
        first_h1: str | None = None

        for line in lines:
            h_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if h_match:
                # Save previous section if it has content
                if current_section_lines:
                    sec_text = "\n".join(current_section_lines).strip()
                    if sec_text:
                        sections.append({
                            "title": current_section_title,
                            "text": TextNormalizer.normalize_text(sec_text),
                            "page_number": None,
                        })
                    current_section_lines = []

                heading_text = h_match.group(2).strip()
                if h_match.group(1) == "#" and not first_h1:
                    first_h1 = heading_text

                current_section_title = heading_text
            else:
                current_section_lines.append(line)

        # Append final section
        if current_section_lines:
            sec_text = "\n".join(current_section_lines).strip()
            if sec_text:
                sections.append({
                    "title": current_section_title,
                    "text": TextNormalizer.normalize_text(sec_text),
                    "page_number": None,
                })

        if not title or title == source_name:
            if first_h1:
                title = first_h1

        # 4. Extract Embedded Markdown Link Citations
        extracted_links: list[dict[str, str]] = []
        for l_match in cls._LINK_CITATION_REGEX.finditer(body_text):
            extracted_links.append({
                "text": l_match.group(1).strip(),
                "url": l_match.group(2).strip(),
            })

        # 5. Full Normalized Text
        full_text = TextNormalizer.normalize_text(body_text)

        return {
            "title": title,
            "author": author,
            "section_count": len(sections),
            "sections": sections,
            "full_text": full_text,
            "embedded_links": extracted_links,
        }
