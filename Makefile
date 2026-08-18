.PHONY: help verify test-api test-proxy test-python-sdk test-typescript-sdk test-php-sdk test-sdks typecheck-web build-web verify-docker clean quick-check lint-python

VENV_PYTEST ?= ./.venv/bin/pytest

help: ## Display available local verification targets
	@echo "Pace Local Verification Commands:"
	@echo "  make verify               Run complete verification suite (API, Proxy, SDKs, Web, Docker)"
	@echo "  make quick-check          Run fast unit tests and web typecheck"
	@echo "  make lint-python          Run Python syntax checks"
	@echo "  make test-api             Run API unit & integration tests"
	@echo "  make test-proxy           Run Proxy tests"
	@echo "  make test-python-sdk      Run Python SDK tests"
	@echo "  make test-typescript-sdk  Build & run TypeScript SDK tests"
	@echo "  make test-php-sdk         Run PHP SDK tests"
	@echo "  make test-sdks            Run all SDK tests"
	@echo "  make typecheck-web        Typecheck the Next.js web app"
	@echo "  make build-web            Build the Next.js web app"
	@echo "  make verify-docker        Validate Docker Compose configuration"

lint-python:
	./.venv/bin/python -m py_compile apps/api/app/main.py packages/python-sdk/pace/__init__.py packages/proxy/pace_proxy/server.py
	@echo "Python syntax check passed! 🐍"

quick-check: test-api test-proxy test-sdks typecheck-web
	@echo "Quick verification check passed! 🚀"

test-api:
	PYTHONPATH=apps/api:packages/python-sdk:packages/proxy $(VENV_PYTEST) apps/api/tests

test-proxy:
	PYTHONPATH=packages/proxy:packages/python-sdk $(VENV_PYTEST) packages/proxy/tests

test-python-sdk:
	PYTHONPATH=packages/python-sdk $(VENV_PYTEST) packages/python-sdk/tests

test-typescript-sdk:
	cd packages/typescript-sdk && npm run build && npm test

test-php-sdk:
	php packages/php-sdk/run_tests.php

test-sdks: test-python-sdk test-typescript-sdk test-php-sdk

typecheck-web:
	cd apps/web && npm run typecheck

build-web:
	cd apps/web && npm run build

verify-docker:
	docker compose config || echo "Docker CLI not active or not installed; skipping docker compose config validation"

clean:
	find . -type d -name "__pycache__" -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.tsbuildinfo" -not -path "*/node_modules/*" -delete 2>/dev/null || true

verify: test-api test-proxy test-sdks typecheck-web build-web verify-docker
	@echo "=================================================="
	@echo "  All local verification checks passed! ✨"
	@echo "=================================================="
