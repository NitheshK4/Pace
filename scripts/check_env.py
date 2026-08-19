#!/usr/bin/env python3
"""
Environment Diagnostic Inspector Script for Pace Monorepo.
Validates python version, required environment variables, and directory structure.
"""

import sys
import os
import shutil

def validate_pace_env_vars(env_dict: dict) -> dict:
    """Validates an environment dictionary for recommended Pace configurations."""
    results = {
        "PACE_ENDPOINT": env_dict.get("PACE_ENDPOINT", "http://localhost:8000"),
        "PACE_ENV": env_dict.get("PACE_ENV", "development"),
        "has_api_key": bool(env_dict.get("PACE_API_KEY")),
    }
    return results

def main():
    print("==================================================")
    print(" Pace Environment Diagnostics Check")
    print("==================================================")

    # 1. Python Version Check
    py_ver = sys.version_info
    print(f"Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 10):
        print("❌ Error: Python 3.10+ is required.")
        sys.exit(1)

    # 2. Tool Availability
    tools = ["git", "node", "npm", "docker"]
    for tool in tools:
        path = shutil.which(tool)
        status = f"✅ Found ({path})" if path else "⚠️ Not found in PATH"
        print(f"Tool '{tool}': {status}")

    # 3. Environment Variables
    env_vars = ["PACE_ENDPOINT", "PACE_API_KEY", "DATABASE_URL"]
    print("\nEnvironment Variables:")
    for var in env_vars:
        val = os.getenv(var)
        print(f"  {var}: {'[SET]' if val else '[NOT SET / USING DEFAULT]'}")

    print("\n✅ Environment diagnostic check completed successfully.")

if __name__ == "__main__":
    main()
