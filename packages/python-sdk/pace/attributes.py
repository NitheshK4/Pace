"""
Span and metadata attribute helpers for Python Pace SDK.
"""

from typing import Dict, Any, Optional

class AttributeBuilder:
    def __init__(self, base: Optional[Dict[str, Any]] = None):
        self._attrs = dict(base or {})

    def set_environment(self, env: str) -> "AttributeBuilder":
        self._attrs["environment"] = env
        return self

    def set_user_id(self, user_id: str) -> "AttributeBuilder":
        self._attrs["user_id"] = user_id
        return self

    def set_session_id(self, session_id: str) -> "AttributeBuilder":
        self._attrs["session_id"] = session_id
        return self

    def build(self) -> Dict[str, Any]:
        return self._attrs
