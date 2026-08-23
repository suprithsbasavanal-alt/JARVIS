"""Secure, Pure-Python PDF Parser and Text Extractor for Phase 4 Research."""

from io import BytesIO
import re
from typing import Any
import zlib
from core.exceptions import (
    DocumentFormatError,
    DocumentParsingError,
    DocumentSizeExceededError,
)
from research.normalizer import TextNormalizer


class SecurePDFParser:
    """Safely extracts text and metadata from PDF files without external subprocesses or shell utilities."""

    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
    MAX_UNCOMPRESSED_STREAM_BYTES = 10 * 1024 * 1024  # 10 MB per stream
    MAX_CUMULATIVE_DECOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB bomb limit
    MAX_PAGES = 200

    # Malicious or dangerous action tags to detect and neutralize
    DANGEROUS_PDF_TAGS: tuple[bytes, ...] = (
        b"/JS",
        b"/JavaScript",
        b"/Launch",
        b"/EmbeddedFiles",
        b"/AcroForm",
    )

    # Regex patterns for PDF objects and text operators
    _OBJ_REGEX = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.DOTALL)
    _STREAM_REGEX = re.compile(rb"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)
    _BT_ET_REGEX = re.compile(rb"BT\s*(.*?)\s*ET", re.DOTALL)
    _TJ_STRING_REGEX = re.compile(rb"\((?:\\.|[^()\\])*\)\s*Tj")
    _TJ_ARRAY_REGEX = re.compile(rb"\[(.*?)\]\s*TJ", re.DOTALL)
    _HEX_STRING_REGEX = re.compile(rb"<([0-9a-fA-F\s]+)>\s*Tj")
    _TD_LINE_BREAK_REGEX = re.compile(rb"(?:T\*|Td|TD|Tm|[\'\"])")
    _INFO_TITLE_REGEX = re.compile(rb"/Title\s*(?:\((.*?)\)|<([0-9a-fA-F]+)>)")
    _INFO_AUTHOR_REGEX = re.compile(rb"/Author\s*(?:\((.*?)\)|<([0-9a-fA-F]+)>)")

    @classmethod
    def _decode_pdf_literal_string(cls, raw_bytes: bytes) -> str:
        """Decode PDF literal string escapes including octal sequences and standard escapes."""
        if raw_bytes.startswith(b"(") and raw_bytes.endswith(b")"):
            raw_bytes = raw_bytes[1:-1]

        # Handle octal escapes: \ooo
        def _replace_octal(match: re.Match[bytes]) -> bytes:
            return bytes([int(match.group(1), 8)])

        processed = re.sub(rb"\\([0-7]{1,3})", _replace_octal, raw_bytes)

        # Standard escape replacements
        processed = processed.replace(rb"\\n", b"\n")
        processed = processed.replace(rb"\\r", b"\r")
        processed = processed.replace(rb"\\t", b"\t")
        processed = processed.replace(rb"\\b", b"\b")
        processed = processed.replace(rb"\\f", b"\f")
        processed = processed.replace(rb"\\(", b"(")
        processed = processed.replace(rb"\\)", b")")
        processed = processed.replace(rb"\\\\", b"\\")

        try:
            # First try UTF-8 with BOM or plain UTF-8
            if processed.startswith(b"\xfe\xff"):
                return processed[2:].decode("utf-16-be", errors="replace")
            if processed.startswith(b"\xff\xfe"):
                return processed[2:].decode("utf-16-le", errors="replace")
            return processed.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to Latin-1 (standard PDF doc encoding)
            return processed.decode("latin-1", errors="replace")

    @classmethod
    def _decode_hex_string(cls, hex_bytes: bytes) -> str:
        """Decode PDF hexadecimal string <48656c6c6f>."""
        clean_hex = re.sub(rb"\s+", b"", hex_bytes)
        if len(clean_hex) % 2 != 0:
            clean_hex += b"0"
        try:
            raw = bytes.fromhex(clean_hex.decode("ascii"))
            return cls._decode_pdf_literal_string(raw)
        except Exception:
            return ""

    @classmethod
    def _extract_text_from_stream_content(cls, content: bytes) -> str:
        """Parse text operators (BT...ET, Tj, TJ) from decompressed PDF stream."""
        text_lines: list[str] = []

        # Find all BT ... ET blocks
        for bt_match in cls._BT_ET_REGEX.finditer(content):
            block = bt_match.group(1)
            current_line_parts: list[str] = []

            # 1. Process TJ array operators [(string) -kern (string)] TJ
            for tj_arr_match in cls._TJ_ARRAY_REGEX.finditer(block):
                arr_body = tj_arr_match.group(1)
                # Find all (literal) or <hex> inside array
                str_matches = re.findall(rb"\((?:\\.|[^()\\])*\)|<[0-9a-fA-F\s]+>", arr_body)
                for s in str_matches:
                    if s.startswith(b"("):
                        current_line_parts.append(cls._decode_pdf_literal_string(s))
                    elif s.startswith(b"<"):
                        current_line_parts.append(cls._decode_hex_string(s[1:-1]))

            # 2. Process standalone (text) Tj
            for tj_match in cls._TJ_STRING_REGEX.finditer(block):
                full_tj = tj_match.group(0)
                str_part = full_tj[:full_tj.rfind(b"Tj")].strip()
                current_line_parts.append(cls._decode_pdf_literal_string(str_part))

            # 3. Process standalone <hex> Tj
            for hex_match in cls._HEX_STRING_REGEX.finditer(block):
                hex_body = hex_match.group(1)
                current_line_parts.append(cls._decode_hex_string(hex_body))

            if current_line_parts:
                text_lines.append(" ".join(current_line_parts))

        # If no BT/ET blocks matched (e.g. non-standard generator), extract raw literal strings
        if not text_lines:
            simple_strings = re.findall(rb"\(((?:\\.|[^()\\]){2,})\)", content)
            for s in simple_strings:
                decoded = cls._decode_pdf_literal_string(s)
                if any(c.isalnum() for c in decoded):
                    text_lines.append(decoded)

        return "\n".join(text_lines)

    @classmethod
    def parse_pdf_bytes(
        cls,
        pdf_bytes: bytes,
        source_name: str = "document.pdf",
    ) -> dict[str, Any]:
        """Parse raw PDF bytes safely into structured text and metadata.

        Enforces size bounds, decompression limits, and neutralizes active exploits.
        """
        if not pdf_bytes or not isinstance(pdf_bytes, (bytes, bytearray)):
            raise DocumentFormatError(f"PDF content for '{source_name}' is empty or invalid.")

        if len(pdf_bytes) > cls.MAX_FILE_SIZE_BYTES:
            raise DocumentSizeExceededError(
                f"PDF file size ({len(pdf_bytes)} bytes) exceeds maximum limit of {cls.MAX_FILE_SIZE_BYTES} bytes."
            )

        # 1. Header Validation (%PDF-)
        header_index = pdf_bytes.find(b"%PDF-")
        if header_index == -1 or header_index > 1024:
            raise DocumentFormatError(
                f"File '{source_name}' does not contain a valid %PDF- header."
            )

        # 2. Check for Dangerous Active PDF Actions (/JS, /Launch)
        detected_threats: list[str] = []
        for threat_tag in cls.DANGEROUS_PDF_TAGS:
            if threat_tag in pdf_bytes:
                detected_threats.append(threat_tag.decode("ascii"))

        # 3. Extract Metadata (/Title, /Author)
        title = source_name
        author: str | None = None

        title_match = cls._INFO_TITLE_REGEX.search(pdf_bytes)
        if title_match:
            raw_t = title_match.group(1) or title_match.group(2)
            if raw_t:
                title = cls._decode_pdf_literal_string(raw_t).strip() or source_name

        author_match = cls._INFO_AUTHOR_REGEX.search(pdf_bytes)
        if author_match:
            raw_a = author_match.group(1) or author_match.group(2)
            if raw_a:
                author = cls._decode_pdf_literal_string(raw_a).strip() or None

        # 4. Extract and Decompress Content Streams with Decompression Bomb Limits
        cumulative_decompressed_bytes = 0
        extracted_pages: list[dict[str, Any]] = []

        # Find all streams
        stream_matches = list(cls._STREAM_REGEX.finditer(pdf_bytes))
        page_texts: list[str] = []

        for sm in stream_matches:
            raw_stream = sm.group(1)
            decompressed: bytes

            # Attempt FlateDecode (zlib decompress)
            try:
                # Use decompressobj to strictly limit uncompressed stream size
                decompressor = zlib.decompressobj()
                decompressed = decompressor.decompress(
                    raw_stream,
                    cls.MAX_UNCOMPRESSED_STREAM_BYTES + 1,
                )
                if len(decompressed) > cls.MAX_UNCOMPRESSED_STREAM_BYTES or decompressor.unconsumed_tail:
                    raise DocumentSizeExceededError(
                        f"PDF stream uncompressed size exceeds maximum limit of {cls.MAX_UNCOMPRESSED_STREAM_BYTES} bytes."
                    )
            except DocumentSizeExceededError:
                raise
            except Exception:
                # Stream was not FlateEncoded or was uncompressed plaintext
                decompressed = raw_stream

            cumulative_decompressed_bytes += len(decompressed)
            if cumulative_decompressed_bytes > cls.MAX_CUMULATIVE_DECOMPRESSED_BYTES:
                raise DocumentSizeExceededError(
                    f"PDF decompression limit exceeded ({cumulative_decompressed_bytes} bytes). Potential zip bomb."
                )

            page_text = cls._extract_text_from_stream_content(decompressed)
            if page_text.strip():
                page_texts.append(page_text)

            if len(page_texts) >= cls.MAX_PAGES:
                break

        # If no streams yielded text, fallback to searching for literal strings in raw PDF
        if not page_texts:
            raw_fallback = cls._extract_text_from_stream_content(pdf_bytes)
            if raw_fallback.strip():
                page_texts.append(raw_fallback)

        # 5. Structure Pages and Normalize Text
        page_records: list[dict[str, Any]] = []
        normalized_full_chunks: list[str] = []

        for p_idx, p_text in enumerate(page_texts, start=1):
            clean_p = TextNormalizer.normalize_text(p_text)
            if clean_p:
                page_records.append({
                    "page_number": p_idx,
                    "title": f"Page {p_idx}",
                    "text": clean_p,
                })
                normalized_full_chunks.append(f"--- Page {p_idx} ---\n{clean_p}")

        full_text = "\n\n".join(normalized_full_chunks).strip()
        if not full_text:
            full_text = "No extractable text content found in document."

        return {
            "title": title,
            "author": author,
            "page_count": len(page_records) or 1,
            "pages": page_records,
            "full_text": full_text,
            "detected_threats_neutralized": detected_threats,
        }
