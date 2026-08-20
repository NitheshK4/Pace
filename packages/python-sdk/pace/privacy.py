import re
from typing import Dict, Any, Optional

FORBIDDEN_KEYS = {"prompt", "completion", "messages", "content", "authorization", "api_key", "secret", "bearer", "password"}

def sanitize_metadata(
    metadata: Optional[Dict[str, Any]],
    max_bytes: int = 4096,
    denylist: Optional[set] = None
) -> Dict[str, Any]:
    if not metadata:
        return {}

    active_denylist = FORBIDDEN_KEYS.union(denylist or set())
    sanitized: Dict[str, Any] = {}

    for k, v in metadata.items():
        if k.lower() in active_denylist:
            continue
        # Convert values to strings or primitives, avoid storing large objects
        if isinstance(v, (str, int, float, bool)) or v is None:
            sanitized[k] = v
        else:
            sanitized[k] = str(v)[:200]

    return sanitized

def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """Masks a secret string leaving only the prefix visible."""
    if not value or not isinstance(value, str):
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
