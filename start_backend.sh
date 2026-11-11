#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/backend"

echo "=== GuardSLM LMS: Starting Backend ==="

# Activate virtual environment if present
if [ -d "venv" ]; then
    echo "Activating virtual environment (backend/venv)..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment (../venv)..."
    source ../venv/bin/activate
fi

# Initialize and seed database if guardslm.db does not exist
if [ ! -f "guardslm.db" ]; then
    echo "Initializing and seeding database..."
    python3 -m app.seed
fi

echo "Starting FastAPI server on http://localhost:8000 (API docs at http://localhost:8000/docs)..."
exec python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
