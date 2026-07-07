#!/usr/bin/env bash
# Start Celery worker; queues/concurrency from /etc/conf.d/em_celery env vars.
# Usage: run-worker.sh catalog|offer
set -euo pipefail

WORKER_TYPE="${1:?Usage: $0 catalog|offer}"
if [[ "$WORKER_TYPE" != "catalog" && "$WORKER_TYPE" != "offer" ]]; then
  echo "worker type must be catalog or offer, got: $WORKER_TYPE" >&2
  exit 1
fi

APP_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="/etc/conf.d/em_celery"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

cd "$APP_ROOT"

read -r QUEUES CONCURRENCY LOGLEVEL NODE_NAME <<< "$(
  "$APP_ROOT/.venv/bin/python" - <<PY
from em_celery.runtime import get_worker_settings
s = get_worker_settings("$WORKER_TYPE")
print(s["queues"], s["concurrency"], s["loglevel"], s["node_name"])
PY
)"

exec "$APP_ROOT/.venv/bin/celery" -A em_celery.worker worker \
  --loglevel="$LOGLEVEL" \
  --concurrency="$CONCURRENCY" \
  -n "$NODE_NAME" \
  -Q "$QUEUES"
