import re
import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional
from app.core.config import settings

def validate_webhook_url(url: str, allow_private_for_test: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validates a target webhook URL against SSRF vulnerabilities.
    Returns (is_valid, error_reason).
    """
    if not url:
        return False, "Webhook URL cannot be empty"

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return False, "Invalid URL structure or missing hostname"

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{scheme}'. Only HTTP and HTTPS are allowed."

    # Enforce HTTPS in production
    is_prod = getattr(settings, "ENVIRONMENT", "development").lower() == "production"
    if is_prod and scheme != "https":
        return False, "HTTPS is strictly required for webhooks in production environment."

    hostname = parsed.hostname

    # Disallow literal localhost strings
    if hostname.lower() in ("localhost", "localhost.localdomain", "127.0.0.1", "::1"):
        if not allow_private_for_test and not getattr(settings, "ALLOW_PRIVATE_WEBHOOKS", False):
            return False, "Loopback targets (localhost/127.0.0.1) are blocked for webhook alerts."

    # Perform DNS resolution safety check
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname '{hostname}': {str(e)}"

    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if not allow_private_for_test and not getattr(settings, "ALLOW_PRIVATE_WEBHOOKS", False):
                if ip.is_loopback:
                    return False, f"Resolved IP {ip_str} is a loopback address (SSRF blocked)."
                if ip.is_private:
                    return False, f"Resolved IP {ip_str} is a private network address (SSRF blocked)."
                if ip.is_link_local:
                    return False, f"Resolved IP {ip_str} is a link-local address (SSRF blocked)."
                if ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                    return False, f"Resolved IP {ip_str} is a reserved/restricted address (SSRF blocked)."
        except ValueError:
            return False, f"Invalid IP address format: {ip_str}"

    return True, None

def redact_sensitive_text(text: Optional[str]) -> str:
    """
    Redacts tokens, API keys, passwords, and authorization headers from error messages and logs.
    """
    if not text:
        return ""

    # Redact Authorization headers, bearer tokens, api keys, secrets
    patterns = [
        (r"(?i)(bearer\s+|token[=:]\s*|key[=:]\s*|secret[=:]\s*|password[=:]\s*|sk-[a-zA-Z0-9]+|pace_[a-zA-Z0-9]+)", r"\1[REDACTED]"),
        (r"(?i)(http[s]?://[^:]+:)[^@]+(@)", r"\1[REDACTED]\2")  # Basic auth in URL
    ]

    redacted = text
    for pattern, repl in patterns:
        redacted = re.sub(pattern, repl, redacted)
    return redacted
