#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if docker compose version >/dev/null 2>&1; then
  docker compose exec -e REACT_APP_BACKEND_URL=http://127.0.0.1:8000 backend pytest -v
else
  docker-compose exec -e REACT_APP_BACKEND_URL=http://127.0.0.1:8000 backend pytest -v
fi
