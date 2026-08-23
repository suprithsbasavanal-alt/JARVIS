"""Static and Runtime Security Vulnerability Scanner (Phase 10)."""

from dataclasses import dataclass, field
import ipaddress
import re
from typing import Any
import urllib.parse


@dataclass
class VulnerabilityFinding:
    """Security vulnerability or secret exposure finding."""
    category: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    title: str
    details: str
    target: str | None = None


@dataclass
class ScanReport:
    """Consolidated report from static/runtime security scanner."""
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[VulnerabilityFinding] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return (self.critical_count == 0 and self.high_count == 0)


class SecurityVulnerabilityScanner:
    """Scans payloads, strings, URLs, and runtime state for vulnerabilities and leaks."""

    SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
        "GITHUB_PAT": re.compile(r"ghp_[A-Za-z0-9]{36}"),
        "SLACK_BOT_TOKEN": re.compile(r"xoxb-[0-9]{11,13}-[0-9]{11,13}-[A-Za-z0-9]{24}"),
        "SLACK_USER_TOKEN": re.compile(r"xoxp-[0-9]{11,13}-[0-9]{11,13}-[A-Za-z0-9]{24}"),
        "AWS_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
        "OPENAI_KEY": re.compile(r"sk-[A-Za-z0-9]{32,}"),
        "PRIVATE_KEY_HEADER": re.compile(r"-----BEGIN ([A-Z0-9_-]+\s+)?PRIVATE KEY-----"),
        "BEARER_TOKEN": re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{20,}="),
    }

    PRIVATE_IP_NETWORKS = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),  # AWS/Cloud metadata
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
    ]

    def scan_for_secrets(self, text: str, context: str = "general") -> list[VulnerabilityFinding]:
        """Scan a string or serialized structure for exposed tokens/credentials."""
        findings = []
        for name, pattern in self.SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(VulnerabilityFinding(
                    category="CREDENTIAL_EXPOSURE",
                    severity="CRITICAL",
                    title=f"Exposed {name} detected",
                    details=f"Plaintext credential matching signature {name} was found in {context}.",
                    target=context,
                ))
        return findings

    def check_url_for_ssrf(self, url: str) -> list[VulnerabilityFinding]:
        """Check URL for cleartext HTTP or private network SSRF targets."""
        findings = []
        parsed = urllib.parse.urlparse(url)

        # 1. Cleartext check
        if parsed.scheme.lower() == "http":
            findings.append(VulnerabilityFinding(
                category="INSECURE_TRANSPORT",
                severity="HIGH",
                title="Cleartext HTTP URL",
                details=f"Insecure cleartext scheme 'http' used in URL: {url}",
                target=url,
            ))

        hostname = parsed.hostname or ""

        # 2. Localhost check
        if hostname.lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}:
            findings.append(VulnerabilityFinding(
                category="SSRF",
                severity="CRITICAL",
                title="Localhost/Loopback SSRF target",
                details=f"URL targets loopback/metadata host '{hostname}': {url}",
                target=url,
            ))
            return findings

        # 3. IP address check
        try:
            ip_obj = ipaddress.ip_address(hostname)
            for net in self.PRIVATE_IP_NETWORKS:
                if ip_obj in net:
                    findings.append(VulnerabilityFinding(
                        category="SSRF",
                        severity="CRITICAL",
                        title="Private Subnet SSRF target",
                        details=f"URL targets private network address '{ip_obj}': {url}",
                        target=url,
                    ))
                    break
        except ValueError:
            # Not a numeric IP address, hostname resolution would occur at network layer
            pass

        return findings

    def scan_runtime_state(self, state_dict: dict[str, Any], context: str = "runtime_state") -> ScanReport:
        """Scan a nested runtime dictionary (audit records, DTOs, configs) for security findings."""
        report = ScanReport()
        serialized = str(state_dict)

        # 1. Check for plaintext secrets
        secret_findings = self.scan_for_secrets(serialized, context=context)
        for f in secret_findings:
            self._add_finding(report, f)

        return report

    def _add_finding(self, report: ScanReport, finding: VulnerabilityFinding) -> None:
        report.findings.append(finding)
        report.total_findings += 1
        if finding.severity == "CRITICAL":
            report.critical_count += 1
        elif finding.severity == "HIGH":
            report.high_count += 1
        elif finding.severity == "MEDIUM":
            report.medium_count += 1
        else:
            report.low_count += 1
