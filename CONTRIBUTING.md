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

## Conventional Commit Standards

Pace follows the Conventional Commits specification. All commit messages must follow the format:

`<type>(<scope>): <short description>`

### Allowed Types
- `feat`: A new feature or API capability
- `fix`: A bug fix or error edge-case resolution
- `test`: Adding or updating unit/integration tests
- `docs`: Documentation updates or OpenAPI changes
- `refactor`: Code refactoring without behavioral changes
- `chore`: Maintenance tasks, scripts, dependencies, or build tool updates

### Allowed Scopes
- `api`, `web`, `python-sdk`, `typescript-sdk`, `php-sdk`, `proxy`, `scripts`, `dev`

## Troubleshooting & Common Issues

- **Database Migration Warnings**: When running `make test-api`, SQLite in-memory test database is created dynamically. Ensure `alembic` migrations match model declarations. To generate a new migration, run `PYTHONPATH=apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "description"`.
- **Node Module Dependencies**: If TypeScript SDK or Web build fails, execute `npm install` inside `packages/typescript-sdk` or `apps/web`.
- **Sanity Checks**: Run `python3 scripts/workspace_sanity.py` to verify workspace directory integrity.

