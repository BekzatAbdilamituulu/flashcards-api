#!/usr/bin/env bash
set -e

echo "Waiting for database..."

# optional small wait (useful for postgres in docker-compose)
sleep 2

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
