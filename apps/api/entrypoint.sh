#!/bin/sh
set -e
echo "Running database migrations via Alembic..."
alembic upgrade head
exec "$@"
