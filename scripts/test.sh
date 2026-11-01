#!/usr/bin/env bash
# One-command test run: unit + integration tests and the retrieval eval.
# Uses DATABASE_URL/DATABASE_ADMIN_URL when set; otherwise starts a throwaway pgvector container.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python
elif [[ -x .venv/Scripts/python.exe ]]; then PYTHON=.venv/Scripts/python.exe
else PYTHON=python
fi

CONTAINER=brisamar-test-pg
if [[ -z "${DATABASE_URL:-}" ]]; then
  if command -v docker >/dev/null 2>&1; then
    if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
      docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
      docker run -d --name "$CONTAINER" -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=brisamar \
        -p 55432:5432 pgvector/pgvector:pg16 >/dev/null
      until docker exec "$CONTAINER" pg_isready -U postgres -d brisamar >/dev/null 2>&1; do sleep 1; done
      sleep 2
    fi
    export DATABASE_URL="postgresql://brisamar_app:brisamar_app@localhost:55432/brisamar"
    export DATABASE_ADMIN_URL="postgresql://postgres:postgres@localhost:55432/brisamar"
  else
    echo "Docker not found and DATABASE_URL unset: integration tests and eval will be skipped." >&2
  fi
fi

export OTEL_EXPORTER=none
"$PYTHON" -m ruff check app tests eval
"$PYTHON" -m pytest -q
if [[ -n "${DATABASE_URL:-}" ]]; then
  "$PYTHON" -m eval.run_eval
fi
