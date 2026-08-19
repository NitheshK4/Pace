#!/usr/bin/env python3
"""
Pace Workspace Sanity Check Script
Validates directory structure, required config files, and core dependencies.
"""
import sys
import os
from pathlib import Path

REQUIRED_PATHS = [
    ".env.example",
    "Makefile",
    "README.md",
    "CONTRIBUTING.md",
    "apps/api/app/main.py",
    "apps/api/pyproject.toml",
    "apps/web/package.json",
    "apps/web/src/app/layout.tsx",
    "packages/python-sdk/pace/__init__.py",
    "packages/typescript-sdk/package.json",
    "packages/php-sdk/src/PaceClient.php",
    "packages/proxy/pace_proxy/server.py",
]

def estimate_payload_bytes(event_count: int, avg_event_bytes: int = 256) -> int:
    """Estimates network payload size in bytes for a given event count."""
    if event_count <= 0:
        return 0
    return event_count * avg_event_bytes

from check_env import validate_pace_env_vars

def main():
    root = Path(__file__).resolve().parent.parent
    print(f"Running Pace workspace sanity check in: {root}")
    
    missing = []
    for rel_path in REQUIRED_PATHS:
        full_path = root / rel_path
        if not full_path.exists():
            missing.append(rel_path)
            print(f"  ❌ Missing: {rel_path}")
        else:
            print(f"  ✅ Verified: {rel_path}")

    if missing:
        print(f"\nSanity check failed: {len(missing)} required path(s) missing.")
        sys.exit(1)

    # Validate env vars helper function sanity
    env_res = validate_pace_env_vars({"PACE_ENDPOINT": "http://localhost:8000"})
    assert env_res["PACE_ENDPOINT"] == "http://localhost:8000"
    assert env_res["has_api_key"] is False

    print("\n✨ Workspace sanity check passed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()
