#!/bin/sh
set -e

PORT="${PORT:-8000}"
RUN_MIGRATIONS_ON_START="${RUN_MIGRATIONS_ON_START:-1}"

if [ "$RUN_MIGRATIONS_ON_START" = "1" ] || [ "$RUN_MIGRATIONS_ON_START" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips="*"
