"""Citation and Source Metadata Tracking Engine for Phase 4 Research."""

from datetime import datetime, timezone
import hashlib
from typing import Any
from core.compat import BaseModel, Field


class CitationSource(BaseModel):
    """Strongly typed citation record binding factual claims to source documents."""
    source_id: str
    source_type: str  # "pdf", "markdown", "web_page", "search_result"
    source_uri: str
    title: str
    author: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    snippet: str
    content_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def format_reference(self) -> str:
        """Format human-readable citation footnote."""
        parts = [f"[{self.source_id}] {self.title}"]
        if self.author:
            parts.append(f"by {self.author}")
        if self.page_number is not None:
            parts.append(f"p. {self.page_number}")
        if self.section_title:
            parts.append(f"Section: {self.section_title}")
        parts.append(f"URI: {self.source_uri}")
        parts.append(f"SHA-256: {self.content_hash[:12]}...")
        return ", ".join(parts)


class CitationManager:
    """Manages creation, verification, and extraction of verifiable citations."""

    @staticmethod
    def compute_sha256(content: str | bytes) -> str:
        """Compute SHA-256 hex digest of raw content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def create_citation(
        cls,
        source_uri: str,
        source_type: str,
        title: str,
        snippet: str,
        raw_document_bytes: bytes | None = None,
        author: str | None = None,
        page_number: int | None = None,
        section_title: str | None = None,
        source_id: str | None = None,
    ) -> CitationSource:
        """Create a verifiable CitationSource record."""
        clean_snippet = snippet.strip()
        doc_hash = (
            cls.compute_sha256(raw_document_bytes)
            if raw_document_bytes is not None
            else cls.compute_sha256(clean_snippet)
        )
        
        cid = source_id or f"cite_{doc_hash[:8]}_{page_number or 1}"

        return CitationSource(
            source_id=cid,
            source_type=source_type,
            source_uri=source_uri,
            title=title.strip() or "Untitled Document",
            author=author.strip() if author else None,
            page_number=page_number,
            section_title=section_title.strip() if section_title else None,
            snippet=clean_snippet,
            content_hash=doc_hash,
        )

    @classmethod
    def extract_citations_from_sections(
        cls,
        source_uri: str,
        source_type: str,
        title: str,
        raw_bytes: bytes,
        sections: list[dict[str, Any]],
        author: str | None = None,
    ) -> list[CitationSource]:
        """Extract citations across structured sections or pages."""
        citations: list[CitationSource] = []
        doc_hash = cls.compute_sha256(raw_bytes)

        for idx, sec in enumerate(sections, start=1):
            text = sec.get("text", "").strip()
            if not text:
                continue

            page_num = sec.get("page_number")
            sec_title = sec.get("title")
            # Extract first ~200 characters as citation excerpt
            excerpt = text[:250].replace("\n", " ").strip()
            if len(text) > 250:
                excerpt += "..."

            cid = f"cite_{doc_hash[:6]}_{idx}"
            citations.append(
                CitationSource(
                    source_id=cid,
                    source_type=source_type,
                    source_uri=source_uri,
                    title=title,
                    author=author,
                    page_number=page_num,
                    section_title=sec_title,
                    snippet=excerpt,
                    content_hash=doc_hash,
                )
            )

        return citations
