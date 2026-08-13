#!/usr/bin/env bash
set -e

echo "=== 1. API Unit & Integration Tests ==="
PYTHONPATH=apps/api:packages/python-sdk:packages/proxy ./.venv/bin/pytest apps/api/tests

echo "=== 2. Proxy Tests ==="
PYTHONPATH=packages/proxy:packages/python-sdk ./.venv/bin/pytest packages/proxy/tests

echo "=== 3. Python SDK Tests ==="
PYTHONPATH=packages/python-sdk ./.venv/bin/pytest packages/python-sdk/tests

echo "=== 4. TypeScript SDK Tests ==="
(cd packages/typescript-sdk && npm run build && npm test)

echo "=== 5. PHP SDK Tests ==="
php packages/php-sdk/run_tests.php

echo "=== 6. Web Typecheck & Build ==="
(cd apps/web && npm run typecheck && npm run build)

echo "=== 7. Docker Compose Validation ==="
if command -v docker >/dev/null 2>&1; then
  docker compose config
else
  echo "Docker binary not found, skipping docker compose config check."
fi

echo "=================================================="
echo "  All local verification checks passed! ✨"
echo "=================================================="
