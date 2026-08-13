# Contributing to Pace

Thank you for your interest in contributing to Pace! This document outlines local development prerequisites and verification commands.

## Prerequisites

Ensure you have the following installed on your local machine:
- **Python**: 3.11+ (virtual environment created at `./.venv`)
- **Node.js**: 18+ (with `npm`)
- **PHP**: 8.0+
- **Docker**: (Optional, for running PostgreSQL and Docker Compose verification)

## Local Verification Commands

Pace provides a unified set of local verification commands via `Makefile` or `./scripts/verify.sh`.

### Full Verification Suite
Run all tests, typechecks, builds, and config validations:
```bash
make verify
# or
./scripts/verify.sh
```

### Component-Specific Verification

| Target / Command | Description |
|:---|:---|
| `make test-api` | Run FastAPI backend unit & integration tests |
| `make test-proxy` | Run Pace Local Proxy tests |
| `make test-python-sdk` | Run Python SDK tests |
| `make test-typescript-sdk` | Build & test TypeScript SDK |
| `make test-php-sdk` | Run PHP SDK tests |
| `make test-sdks` | Run all SDK tests (Python, TypeScript, PHP) |
| `make typecheck-web` | Perform TypeScript typecheck on web dashboard |
| `make build-web` | Perform Next.js production build |
| `make verify-docker` | Validate `docker-compose.yml` configuration |

Before submitting a pull request, make sure `make verify` passes cleanly.
