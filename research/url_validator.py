"""Strict URL and Scheme Validator for Phase 4.1 Web Research."""

from urllib.parse import urlparse, urlunparse
from core.exceptions import URLValidationError


class URLValidator:
    """Validates URLs against protocol, scheme, credential, and syntax policies."""

    ALLOWED_SCHEMES: tuple[str, ...] = ("http", "https")
    FORBIDDEN_SCHEMES: tuple[str, ...] = (
        "file",
        "ftp",
        "ftps",
        "data",
        "javascript",
        "vbscript",
        "gopher",
        "blob",
        "dict",
        "ldap",
        "tftp",
        "smtp",
        "pop3",
        "imap",
    )
    ALLOWED_PORTS: tuple[int, ...] = (80, 443, 8080, 8443)

    @classmethod
    def validate_and_normalize(cls, raw_url: str) -> str:
        """Validate URL syntax, scheme, and userinfo, returning normalized URL string.

        Fails closed with URLValidationError if URL violates safety policy.
        """
        if not raw_url or not isinstance(raw_url, str):
            raise URLValidationError("URL must be a non-empty string.")

        clean_url = raw_url.strip()
        if not clean_url:
            raise URLValidationError("URL cannot be whitespace only.")

        try:
            parsed = urlparse(clean_url)
        except Exception as err:
            raise URLValidationError(f"Malformed URL syntax: '{clean_url}'") from err

        # 1. Scheme Validation
        scheme = (parsed.scheme or "").lower()
        if not scheme:
            raise URLValidationError(f"Missing URL scheme in '{clean_url}'. Must start with http:// or https://")

        if scheme in cls.FORBIDDEN_SCHEMES or scheme not in cls.ALLOWED_SCHEMES:
            raise URLValidationError(
                f"Forbidden URL scheme '{scheme}'. Only {cls.ALLOWED_SCHEMES} are permitted."
            )

        # 2. Hostname Validation
        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            raise URLValidationError(f"Missing or invalid hostname in URL '{clean_url}'.")

        # 3. Userinfo / Credential Embedding Check
        if parsed.username or parsed.password:
            raise URLValidationError(
                f"Embedded credentials (userinfo) in URL are strictly prohibited: '{clean_url}'"
            )

        # 4. Port Validation (if non-standard port specified)
        if parsed.port is not None and parsed.port not in cls.ALLOWED_PORTS:
            raise URLValidationError(
                f"Non-standard port '{parsed.port}' rejected. Allowed ports: {cls.ALLOWED_PORTS}"
            )

        # 5. Normalization: strip fragment, standardize casing
        normalized = urlunparse((
            scheme,
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",  # Strip fragment
        ))

        return normalized
