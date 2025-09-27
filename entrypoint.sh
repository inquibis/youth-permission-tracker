#!/bin/bash
set -e

echo "Running DB migrations..."
alembic upgrade head

echo "Initializing test DB (if needed)..."
python init_db.py

echo "Starting server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
