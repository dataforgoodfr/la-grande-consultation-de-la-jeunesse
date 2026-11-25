#!/usr/bin/env bash
set -euo pipefail

export PORT="${PORT:-8080}"
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

uvicorn main:app --host 127.0.0.1 --port 8000 --root-path /api &
UVICORN_PID=$!

nginx -g 'daemon off;' &
NGINX_PID=$!

cleanup() {
  trap - SIGTERM SIGINT
  kill -TERM "$UVICORN_PID" "$NGINX_PID" 2>/dev/null || true
  wait "$UVICORN_PID" "$NGINX_PID" 2>/dev/null || true
}

trap cleanup SIGTERM SIGINT

wait -n "$UVICORN_PID" "$NGINX_PID"
EXIT_CODE=$?

cleanup
exit "${EXIT_CODE:-1}"