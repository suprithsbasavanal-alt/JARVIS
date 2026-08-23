"""Unified Secure Document Engine and Dispatcher for Phase 4 Research."""

import asyncio
from pathlib import Path
from typing import Any
from core.compat import BaseModel, Field
from core.exceptions import (
    DocumentFormatError,
    DocumentParsingError,
    DocumentSizeExceededError,
    DocumentTimeoutError,
    SandboxViolationError,
)
from research.citation import CitationManager, CitationSource
from research.markdown_parser import SecureMarkdownParser
from research.normalizer import TextNormalizer
from research.pdf_parser import SecurePDFParser


class ParsedDocument(BaseModel):
    """Container for parsed document text, metadata, content hash, and citations."""
    source_uri: str
    document_type: str  # "pdf", "markdown", "text"
    title: str
    author: str | None = None
    content_hash: str
    byte_size: int
    page_or_section_count: int
    sections: list[dict[str, Any]] = Field(default_factory=list)
    full_text: str
    citations: list[CitationSource] = Field(default_factory=list)
    detected_threats: list[str] = Field(default_factory=list)

    def format_untrusted_block(self) -> str:
        """Wrap document content in untrusted XML tags for safe context isolation."""
        return (
            f"<untrusted_document_content source=\"{self.source_uri}\" "
            f"title=\"{self.title}\" hash=\"{self.content_hash[:16]}\" type=\"{self.document_type}\">\n"
            f"{self.full_text}\n"
            f"</untrusted_document_content>"
        )


class DocumentEngine:
    """Safe document ingestion and parsing engine enforcing sandbox boundaries and resource limits."""

    DEFAULT_TIMEOUT_SECONDS = 5.0
    MAX_EXTRACTED_CHARACTERS = 500000  # 500k chars limit

    def __init__(self, sandbox_root: str | None = None) -> None:
        self.sandbox_root = Path(sandbox_root or "sandbox").resolve()

    def validate_sandbox_path(self, target_path_str: str, allowed_dirs: list[str] | None = None) -> Path:
        """Ensure file path is strictly within the sandbox or declared allowed paths."""
        if not target_path_str or not isinstance(target_path_str, str):
            raise SandboxViolationError("File path must be a non-empty string.")

        clean_path_str = target_path_str.strip()

        # Reject path traversals and home directory escapes explicitly
        if ".." in clean_path_str or clean_path_str.startswith("~") or clean_path_str.startswith("$HOME"):
            raise SandboxViolationError(
                f"Path traversal or home directory escape attempt blocked: '{clean_path_str}'"
            )

        # Check explicit sensitive host directories
        sensitive_roots = ("/etc", "/usr", "/bin", "/sbin", "/System", "/Library")
        if clean_path_str.startswith(sensitive_roots):
            raise SandboxViolationError(
                f"Access to sensitive system path '{clean_path_str}' is strictly prohibited."
            )

        path_obj = Path(clean_path_str)
        if not path_obj.is_absolute():
            resolved_path = (self.sandbox_root / path_obj).resolve()
        else:
            resolved_path = path_obj.resolve()

        # Allowed roots are self.sandbox_root + any extra allowed_dirs
        allowed_roots = [self.sandbox_root]
        if allowed_dirs:
            for ad in allowed_dirs:
                allowed_roots.append(Path(ad).resolve())

        is_allowed = False
        for root in allowed_roots:
            try:
                resolved_path.relative_to(root)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            raise SandboxViolationError(
                f"File path '{clean_path_str}' resolves outside sandbox boundary ('{resolved_path}')."
            )

        return resolved_path

    async def parse_document(
        self,
        file_path: str,
        raw_bytes: bytes | None = None,
        extract_citations: bool = True,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        allowed_dirs: list[str] | None = None,
    ) -> ParsedDocument:
        """Parse PDF or Markdown file safely with timeout and resource limits."""
        try:
            return await asyncio.wait_for(
                self._parse_internal(
                    file_path=file_path,
                    raw_bytes=raw_bytes,
                    extract_citations=extract_citations,
                    allowed_dirs=allowed_dirs,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as err:
            raise DocumentTimeoutError(
                f"Document parsing for '{file_path}' timed out after {timeout_seconds}s."
            ) from err

    async def _parse_internal(
        self,
        file_path: str,
        raw_bytes: bytes | None = None,
        extract_citations: bool = True,
        allowed_dirs: list[str] | None = None,
    ) -> ParsedDocument:
        """Internal synchronous parsing dispatcher wrapped for async execution."""
        doc_bytes = raw_bytes
        source_name = Path(file_path).name

        if doc_bytes is None:
            # Validate sandbox path and read file
            resolved = self.validate_sandbox_path(file_path, allowed_dirs)
            if not resolved.exists() or not resolved.is_file():
                raise DocumentFormatError(f"Document file '{file_path}' does not exist.")
            doc_bytes = resolved.read_bytes()

        byte_size = len(doc_bytes)
        content_hash = CitationManager.compute_sha256(doc_bytes)

        # Detect format by file extension or magic header
        is_pdf = (
            file_path.lower().endswith(".pdf")
            or doc_bytes.startswith(b"%PDF-")
            or b"%PDF-" in doc_bytes[:1024]
        )
        is_md = file_path.lower().endswith((".md", ".markdown", ".txt"))

        if is_pdf:
            parsed_data = SecurePDFParser.parse_pdf_bytes(doc_bytes, source_name=source_name)
            doc_type = "pdf"
            sections = parsed_data.get("pages", [])
            page_count = parsed_data.get("page_count", len(sections))
            title = parsed_data.get("title", source_name)
            author = parsed_data.get("author")
            full_text = parsed_data.get("full_text", "")
            detected_threats = parsed_data.get("detected_threats_neutralized", [])
        elif is_md or True:  # Default fallback to text / markdown parser
            text_content = doc_bytes.decode("utf-8", errors="replace")
            parsed_data = SecureMarkdownParser.parse_markdown_text(text_content, source_name=source_name)
            doc_type = "markdown" if is_md else "text"
            sections = parsed_data.get("sections", [])
            page_count = parsed_data.get("section_count", len(sections))
            title = parsed_data.get("title", source_name)
            author = parsed_data.get("author")
            full_text = parsed_data.get("full_text", "")
            detected_threats = []

        # Bound max extracted characters
        if len(full_text) > self.MAX_EXTRACTED_CHARACTERS:
            full_text = full_text[:self.MAX_EXTRACTED_CHARACTERS] + "\n\n[TRUNCATED: Max extraction limit reached]"

        # Extract citations if requested
        citations: list[CitationSource] = []
        if extract_citations:
            citations = CitationManager.extract_citations_from_sections(
                source_uri=file_path,
                source_type=doc_type,
                title=title,
                raw_bytes=doc_bytes,
                sections=sections,
                author=author,
            )

        return ParsedDocument(
            source_uri=file_path,
            document_type=doc_type,
            title=title,
            author=author,
            content_hash=content_hash,
            byte_size=byte_size,
            page_or_section_count=page_count,
            sections=sections,
            full_text=full_text,
            citations=citations,
            detected_threats=detected_threats,
        )
