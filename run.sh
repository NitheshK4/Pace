#!/usr/bin/env bash
set -e

# Change to project root directory
cd "$(dirname "$0")"

echo "🚀 Starting Pace LLM Observability Platform..."

# Function to kill child processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping Pace services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend API
echo "▶️  Starting Backend API on http://localhost:8000..."
PYTHONPATH=apps/api ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# 2. Start Frontend Web
echo "▶️  Starting Frontend Web Dashboard on http://localhost:3000..."
(cd apps/web && npm run dev) &

echo "=================================================="
echo "  Pace is running!"
echo "  Dashboard:  http://localhost:3000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Health:     http://localhost:8000/healthz"
echo "=================================================="
echo "Press Ctrl+C to stop all services."

wait
