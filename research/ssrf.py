"""Comprehensive SSRF Protection Engine for Phase 4.1."""

from collections.abc import Callable
import ipaddress
import socket
from urllib.parse import urlparse
from core.exceptions import SSRFBlockedError


class SSRFGuard:
    """Validates destination hostnames and IP addresses against private, loopback, and metadata ranges."""

    # Disallowed Hostnames and TLDs
    FORBIDDEN_HOSTNAMES: tuple[str, ...] = (
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
        "metadata.internal",
        "metadata.azure.com",
        "instance-data",
        "169.254.169.254",
        "kubernetes.default",
        "kubernetes.default.svc",
    )

    FORBIDDEN_SUFFIXES: tuple[str, ...] = (
        ".localhost",
        ".local",
        ".internal",
        ".lan",
        ".corp",
        ".home",
        ".arpa",
    )

    # Disallowed IPv4 CIDR Ranges
    FORBIDDEN_IPV4_NETWORKS: tuple[ipaddress.IPv4Network, ...] = (
        ipaddress.IPv4Network("0.0.0.0/8"),         # Current network
        ipaddress.IPv4Network("10.0.0.0/8"),        # RFC 1918 Private
        ipaddress.IPv4Network("100.64.0.0/10"),     # RFC 6598 Shared Carrier NAT
        ipaddress.IPv4Network("127.0.0.0/8"),       # RFC 1122 Loopback
        ipaddress.IPv4Network("169.254.0.0/16"),    # RFC 3927 Link-Local & Cloud Metadata (169.254.169.254)
        ipaddress.IPv4Network("172.16.0.0/12"),     # RFC 1918 Private
        ipaddress.IPv4Network("192.0.0.0/24"),      # RFC 6890 IETF Protocol Assignments
        ipaddress.IPv4Network("192.0.2.0/24"),      # RFC 5737 Documentation (TEST-NET-1)
        ipaddress.IPv4Network("192.168.0.0/16"),    # RFC 1918 Private
        ipaddress.IPv4Network("198.18.0.0/15"),     # RFC 2544 Benchmarking
        ipaddress.IPv4Network("198.51.100.0/24"),   # RFC 5737 Documentation (TEST-NET-2)
        ipaddress.IPv4Network("203.0.113.0/24"),    # RFC 5737 Documentation (TEST-NET-3)
        ipaddress.IPv4Network("224.0.0.0/4"),       # RFC 5771 Multicast
        ipaddress.IPv4Network("240.0.0.0/4"),       # RFC 1112 Reserved / Future use
        ipaddress.IPv4Network("255.255.255.255/32"),# RFC 919 Limited Broadcast
    )

    # Disallowed IPv6 CIDR Ranges
    FORBIDDEN_IPV6_NETWORKS: tuple[ipaddress.IPv6Network, ...] = (
        ipaddress.IPv6Network("::/128"),            # Unspecified address
        ipaddress.IPv6Network("::1/128"),           # Loopback
        ipaddress.IPv6Network("::ffff:0:0/96"),     # IPv4-mapped IPv6
        ipaddress.IPv6Network("64:ff9b::/96"),      # IPv4/IPv6 translation
        ipaddress.IPv6Network("100::/64"),          # Discard-only prefix
        ipaddress.IPv6Network("2001:db8::/32"),     # Documentation
        ipaddress.IPv6Network("fc00::/7"),          # Unique Local (ULA) Private
        ipaddress.IPv6Network("fe80::/10"),         # Link-Local Unicast
        ipaddress.IPv6Network("ff00::/8"),          # Multicast
    )

    @classmethod
    def is_forbidden_ip(cls, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if an IP address falls within any forbidden/private/loopback range."""
        # Built-in attributes check
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True

        if isinstance(ip, ipaddress.IPv4Address):
            return any(ip in net for net in cls.FORBIDDEN_IPV4_NETWORKS)

        if isinstance(ip, ipaddress.IPv6Address):
            # Check IPv4-mapped IPv6 explicitly
            if ip.ipv4_mapped:
                return cls.is_forbidden_ip(ip.ipv4_mapped)
            return any(ip in net for net in cls.FORBIDDEN_IPV6_NETWORKS)

        return True

    @classmethod
    def validate_ip_address(cls, ip_str: str) -> None:
        """Validate a direct IP address string. Fails closed with SSRFBlockedError."""
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
        except ValueError as err:
            raise SSRFBlockedError(f"Invalid IP address format: '{ip_str}'") from err

        if cls.is_forbidden_ip(ip_obj):
            raise SSRFBlockedError(
                f"SSRF Protection: Access to private/loopback/metadata IP '{ip_str}' is blocked."
            )

    @classmethod
    def validate_host_and_dns(
        cls,
        hostname: str,
        custom_resolver: Callable[[str], list[str]] | None = None,
    ) -> list[str]:
        """Validate hostname and resolve DNS, validating all resolved IP addresses.

        Returns list of validated public IP strings. Fails closed with SSRFBlockedError.
        """
        clean_host = hostname.strip().lower()

        # 1. Check exact forbidden hostnames
        if clean_host in cls.FORBIDDEN_HOSTNAMES:
            raise SSRFBlockedError(
                f"SSRF Protection: Hostname '{clean_host}' is explicitly prohibited."
            )

        # 2. Check forbidden domain suffixes
        if any(clean_host.endswith(suffix) for suffix in cls.FORBIDDEN_SUFFIXES):
            raise SSRFBlockedError(
                f"SSRF Protection: Domain suffix in '{clean_host}' is prohibited."
            )

        # 3. If hostname is directly an IP literal, validate immediately
        try:
            ip_obj = ipaddress.ip_address(clean_host)
            if cls.is_forbidden_ip(ip_obj):
                raise SSRFBlockedError(
                    f"SSRF Protection: Access to IP literal '{clean_host}' is blocked."
                )
            return [clean_host]
        except ValueError:
            pass  # Hostname is a domain name, proceed to DNS resolution

        # 4. Resolve DNS to verify all destination IPs
        resolved_ips: list[str] = []
        if custom_resolver:
            resolved_ips = custom_resolver(clean_host)
        else:
            try:
                addr_info = socket.getaddrinfo(clean_host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                resolved_ips = list({info[4][0] for info in addr_info})
            except socket.gaierror as err:
                raise SSRFBlockedError(f"DNS resolution failed for '{clean_host}': {err}") from err

        if not resolved_ips:
            raise SSRFBlockedError(f"DNS resolution returned no addresses for '{clean_host}'.")

        # 5. Validate EVERY resolved IP address against the SSRF denylist
        for ip_str in resolved_ips:
            cls.validate_ip_address(ip_str)

        return resolved_ips

    @classmethod
    def validate_url_for_ssrf(
        cls,
        url: str,
        custom_resolver: Callable[[str], list[str]] | None = None,
    ) -> list[str]:
        """Convenience method to parse URL hostname and execute complete SSRF validation."""
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise SSRFBlockedError(f"Could not extract hostname from URL: '{url}'")
        return cls.validate_host_and_dns(hostname, custom_resolver)
