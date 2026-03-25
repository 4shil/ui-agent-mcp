#!/usr/bin/env bash
set -euo pipefail

cd /app

if [[ -z "${DEVICE:-}" ]]; then
  if python -c "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)"; then
    export DEVICE=cuda
  else
    export DEVICE=cpu
  fi
fi

echo "[entrypoint] DEVICE=${DEVICE}"

if [[ "${DOWNLOAD_MODELS_ON_START:-1}" == "1" ]]; then
  echo "[entrypoint] Ensuring models are cached in /app/models"
  python scripts/download_models.py
fi

rest_pid=""
if [[ "${ENABLE_REST_API:-1}" == "1" ]]; then
  rest_port="${REST_API_PORT:-8080}"
  echo "[entrypoint] Starting REST API on 0.0.0.0:${rest_port}"
  uvicorn api_server:app --host 0.0.0.0 --port "${rest_port}" &
  rest_pid="$!"
fi

cleanup() {
  if [[ -n "${rest_pid}" ]] && kill -0 "${rest_pid}" >/dev/null 2>&1; then
    kill "${rest_pid}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "[entrypoint] Starting MCP stdio server"
exec python server.py
