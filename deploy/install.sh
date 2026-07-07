#!/usr/bin/env bash
# Bootstrap em-spapi-celery on Ubuntu VPS (legacy layout: Admin + ~/.em_celery).
# Usage: sudo ./deploy/install.sh [/path/to/repo]

set -euo pipefail

REPO_SRC="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="Admin"
APP_HOME="/home/${APP_USER}"
APP_ROOT="${APP_HOME}/em-spapi-celery"
CONFIG_DIR="${APP_HOME}/.em_celery"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if ! id "$APP_USER" &>/dev/null; then
  echo "User ${APP_USER} does not exist. Create it first or adjust APP_USER in install.sh." >&2
  exit 1
fi

echo "==> Syncing application to ${APP_ROOT}"
mkdir -p "$APP_ROOT" "$CONFIG_DIR"
rsync -a --delete \
  --exclude '.venv' --exclude '.git' --exclude '__pycache__' --exclude '*.egg-info' \
  "$REPO_SRC/" "$APP_ROOT/"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT" "$CONFIG_DIR"
chmod +x "$APP_ROOT/deploy/bin/run-worker.sh"

echo "==> Installing Python dependencies (uv) as ${APP_USER}"
UV_BIN="${APP_HOME}/.local/bin/uv"
if [[ ! -x "$UV_BIN" ]]; then
  if ! command -v uv &>/dev/null; then
    echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
  fi
  UV_BIN="$(command -v uv)"
fi
sudo -u "$APP_USER" bash -lc "export PATH='${APP_HOME}/.local/bin:\$PATH'; cd '$APP_ROOT' && '$UV_BIN' sync --no-dev"

if [[ ! -f "$CONFIG_DIR/config.ini" ]]; then
  install -m 0640 -o "$APP_USER" -g "$APP_USER" \
    "$APP_ROOT/deploy/config.ini.example" "$CONFIG_DIR/config.ini"
  echo "Created $CONFIG_DIR/config.ini — edit broker/queues and credentials before start."
fi

mkdir -p /etc/conf.d "$CONFIG_DIR/logs" "$CONFIG_DIR/data"
if [[ ! -f /etc/conf.d/em_celery ]]; then
  install -m 0644 "$APP_ROOT/deploy/conf.d/em_celery.example" /etc/conf.d/em_celery
  echo "Created /etc/conf.d/em_celery — review paths and env overrides."
fi

chown -R "$APP_USER:$APP_USER" "$CONFIG_DIR"

echo "==> Installing systemd units (catalog + offer workers, consume only)"
install -m 0644 "$APP_ROOT/deploy/systemd/em-spapi-celery-catalog-worker.service" /etc/systemd/system/
install -m 0644 "$APP_ROOT/deploy/systemd/em-spapi-celery-offer-worker.service" /etc/systemd/system/
for old_unit in em-spapi-celery-worker em-spapi-celery-worker@; do
  systemctl disable --now "${old_unit}" 2>/dev/null || true
done
rm -f /etc/systemd/system/em-spapi-celery-worker.service \
      /etc/systemd/system/em-spapi-celery-worker@.service
systemctl daemon-reload

echo
echo "Done. Next steps (as ${APP_USER} or root):"
echo "  1. Edit /etc/conf.d/em_celery"
echo "     - CELERY_CATALOG_QUEUES / CELERY_OFFER_QUEUES"
echo "     - CELERY_CATALOG_CONCURRENCY / CELERY_OFFER_CONCURRENCY"
echo "  2. Edit ${CONFIG_DIR}/config.ini (broker, SP-API, ES credentials)"
echo "  3. systemctl enable --now em-spapi-celery-catalog-worker em-spapi-celery-offer-worker"
echo "  4. journalctl -u em-spapi-celery-catalog-worker -f"
echo "     journalctl -u em-spapi-celery-offer-worker -f"
echo
echo "Config/logs/data: ${CONFIG_DIR}/"
echo "EnvironmentFile:  /etc/conf.d/em_celery"
