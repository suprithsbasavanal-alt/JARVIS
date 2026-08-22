# JARVIS Phase 4.1: Secure Web Research Foundation

## 1. Executive Summary & Security Posture
Phase 4.1 establishes the secure, sandboxed foundation for Web Research in JARVIS. It introduces:
- Strict URL validation (schemes, userinfo rejection, port validation)
- Comprehensive SSRF (Server-Side Request Forgery) protection against private IPv4/IPv6 ranges, loopbacks, carrier-grade NAT, and cloud metadata services (`169.254.169.254`)
- Dynamic DNS resolution validation (DNS rebinding defense)
- Redirect validation and hop limits
- Safe read-only HTTP fetching engine with streaming response size and connection/read timeout bounds
- HTML-to-Markdown extraction and script/style stripping
- Untrusted web content isolation wrappers (`<untrusted_web_content>`) to prevent indirect prompt injection
- Typed research tool contracts (`web_search`, `web_fetch`) registered into the Phase 3 `ToolRegistry`
- SHA-256 chained audit logging for all web research events

---

## 2. Architecture & Request Pipeline

```mermaid
graph TD
    UserQuery[User Query / Tool Call] --> Registry[ToolRegistry Lookup: web_search / web_fetch]
    Registry --> SchemaCheck[Parameter Schema Validation]
    SchemaCheck --> URLVal[URLValidator: Scheme & Credential Check]
    URLVal -->|Invalid Scheme/Userinfo| BlockURL[Raise URLValidationError]
    URLVal --> SSRFCheck[SSRFGuard: Host & Resolved IP Check]
    SSRFCheck -->|Private/Metadata/Loopback IP| BlockSSRF[Raise SSRFBlockedError]
    SSRFCheck --> Fetcher[SafeWebFetcher / Stream Reader]
    Fetcher --> RedirectCheck[Redirect Target URL & SSRF Validation]
    Fetcher --> SizeTimeout[Streaming Byte Counter & Timeout Abort]
    Fetcher --> Normalizer[HTMLNormalizer: Script Stripping & Markdown]
    Normalizer --> Isolator[Untrusted Tag Encapsulation <untrusted_web_content>]
    Isolator --> Audit[AuditLogger SHA-256 Chained Entry]
    Audit --> Synthesis[Model Dialogue Synthesis]
```

---

## 3. Security Controls & Invariants

### A. URL Validation (`research/url_validator.py`)
- **Allowed Schemes**: `http://` and `https://`.
- **Forbidden Schemes**: `file://`, `ftp://`, `data:`, `javascript:`, `vbscript:`, `gopher:`, `blob:`, `ldap:`, `tftp:`.
- **Credential Stripping**: Embedded credentials (userinfo e.g. `http://user:pass@host`) are strictly rejected.
- **Port Whitelist**: Enforces standard web ports (80, 443, 8080, 8443) and blocks internal service ports (SSH 22, MySQL 3306, Redis 6379, etc.).

### B. SSRF Protection (`research/ssrf.py`)
- **Loopback**: `127.0.0.0/8`, `::1`
- **Private IPv4**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **Cloud Metadata & Link-Local**: `169.254.0.0/16` (including `169.254.169.254`, `metadata.google.internal`, `instance-data`)
- **Carrier-Grade NAT & Test Networks**: `100.64.0.0/10`, `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`
- **IPv6 Private Ranges**: `fc00::/7` (ULA), `fe80::/10` (Link-local), `::ffff:0:0/96` (IPv4-mapped IPv6)
- **Domain Suffixes**: Blocks `.localhost`, `.local`, `.internal`, `.lan`, `.home`, `.corp`.
- **DNS Rebinding Defense**: Every host is resolved to IP addresses via DNS, and *all* returned IPs are validated against the denylist before initiating any socket connection.

### C. Redirect Inspection & Safe Streaming (`research/fetcher.py`)
- Max redirects: 3 hops.
- Every redirect destination is validated through the full URL and SSRF pipeline prior to following.
- Hard size limits: Max 512 KB (524,288 bytes). Response is read chunk-by-chunk in a stream and aborted immediately with `PayloadSizeExceededError` if exceeded.
- Timeout limits: Max 5.0 seconds. Aborts with `WebFetchTimeoutError` if response hangs.

### D. HTML Normalization & Untrusted Content Isolation (`research/normalizer.py`, `agents/verifier.py`)
- Active elements (`<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<svg>`, `<nav>`, `<footer>`, `<form>`) are stripped.
- Content is converted to clean Markdown.
- Fetched data is wrapped in XML isolation tags:
  ```xml
  <untrusted_web_content url="https://example.com/article" title="Example Article" status="200">
  # Example Article
  Clean text extracted from webpage.
  </untrusted_web_content>
  ```
- Instructions found inside web pages (e.g. prompt injection attempts) are treated as inert data and cannot override system prompts.

---

## 4. Typed Research Tools

| Tool ID | Capability | Permission Tier | Risk Level | Side-Effect Level | Description |
|---|---|---|---|---|---|
| `web_search` | `RESEARCH` | `NORMAL` | `LOW` | `READ` | Queries search index/fixtures and returns structured results (title, snippet, url). |
| `web_fetch` | `RESEARCH` | `NORMAL` | `LOW` | `READ` | Fetches and converts an HTTP/HTTPS URL into clean Markdown. |

---

## 5. Audit Logging Events
The following events are recorded with SHA-256 hash chaining:
- `WEB_SEARCH_REQUESTED`
- `WEB_SEARCH_COMPLETED`
- `WEB_FETCH_REQUESTED`
- `WEB_FETCH_COMPLETED`
- `SSRF_BLOCKED`
- `REDIRECT_BLOCKED`
- `PAYLOAD_SIZE_EXCEEDED`
- `FETCH_TIMEOUT`
