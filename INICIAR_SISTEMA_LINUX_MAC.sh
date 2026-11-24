#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERRO] Docker nao encontrado. Instale o Docker Desktop ou Docker Engine."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[ERRO] O motor do Docker nao esta em execucao. Inicie o Docker e tente novamente."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  docker compose up --build -d
else
  docker-compose up --build -d
fi

echo "Aguardando http://localhost:3000/api/health ..."
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:3000/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ""
echo "SISTEMA NO AR!"
echo "- Aplicacao Web: http://localhost:3000"
echo "- Swagger UI:    http://localhost:8000/docs"
echo "- Healthcheck:   http://localhost:3000/api/health"
echo ""

if command -v open >/dev/null 2>&1; then
  open "http://localhost:3000"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:3000" >/dev/null 2>&1 &
fi
