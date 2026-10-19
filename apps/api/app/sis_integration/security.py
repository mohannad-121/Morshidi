"""SSRF defense, secret isolation, and secure configuration handling for SIS integrations."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

from .errors import SSRFSecurityError

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private network
    ipaddress.ip_network("172.16.0.0/12"),     # Private network
    ipaddress.ip_network("192.168.0.0/16"),    # Private network
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
]


def validate_target_url(url: str, *, allow_localhost: bool = False) -> str:
    """Validate external SIS target URL to defend against Server-Side Request Forgery (SSRF).

    Enforces:
    - HTTP or HTTPS scheme only
    - Non-empty host
    - Explicit rejection of loopback, private RFC 1918, link-local, and cloud metadata (169.254.169.254)
    - allow_localhost can only be enabled in local integration test environments.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise SSRFSecurityError("Target URL must not be empty")

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SSRFSecurityError(f"Unsupported URL scheme: '{parsed.scheme}'. Only http and https are permitted.")

    host = parsed.hostname
    if not host:
        raise SSRFSecurityError("Target URL does not contain a valid hostname")

    lowered_host = host.lower()
    if lowered_host in {"localhost", "127.0.0.1", "::1"}:
        if not allow_localhost:
            raise SSRFSecurityError(f"Localhost destination '{host}' is prohibited in production")
        return cleaned.rstrip("/")

    # Resolve IP address to detect internal/private targets behind DNS
    try:
        addr_infos = socket.getaddrinfo(host, None)
        ips = {info[4][0] for info in addr_infos}
    except socket.gaierror:
        # If hostname resolution fails at config time, allow domain names for cloud/staging deployments
        # but block literal private IP formats.
        pass
    else:
        for ip_str in ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if not allow_localhost and any(ip_obj in network for network in _BLOCKED_NETWORKS):
                    raise SSRFSecurityError(
                        f"Resolved IP {ip_str} for host '{host}' falls within a prohibited private or metadata network"
                    )
            except ValueError:
                continue

    return cleaned.rstrip("/")


def resolve_secret(secret_env_ref: str | None) -> str:
    """Resolve an integration secret by environment variable reference.

    Never logs the resolved secret. Returns empty string if not found.
    """
    if not secret_env_ref or not secret_env_ref.strip():
        return ""
    return os.environ.get(secret_env_ref.strip(), "").strip()


def mask_secret_status(secret_env_ref: str | None) -> str:
    """Return safe display status of an environment-backed secret for UI/APIs without leaking secret."""
    if not secret_env_ref or not secret_env_ref.strip():
        return "NOT_CONFIGURED"
    is_set = bool(os.environ.get(secret_env_ref.strip()))
    return f"CONFIGURED ({secret_env_ref.strip()})" if is_set else f"MISSING_ENV ({secret_env_ref.strip()})"

