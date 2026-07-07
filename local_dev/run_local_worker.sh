#!/usr/bin/env bash
# Start a local Celery worker for catalog + offer queues.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${BROKER_URL:=redis://127.0.0.1:6379/0}"
: "${MARKETPLACE:=US}"

export BROKER_URL

QUEUES="SpapiCatalogItemsUpdate_${MARKETPLACE},SpapiItemOffersUpdate_${MARKETPLACE}"

echo "Broker:  $BROKER_URL"
echo "Queues:  $QUEUES"
echo "Config:  ${MWS_COLLECTOR_CONFIGURATION_PATH:-~/.em_celery/config.ini}"
echo ""
echo "Start worker (Ctrl+C to stop)..."

exec celery -A em_celery.worker worker \
  -l info \
  -Q "$QUEUES" \
  --concurrency 1
