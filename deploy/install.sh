#!/usr/bin/env bash
# Bootstrap em-spapi-celery on Ubuntu VPS (legacy layout: Admin + ~/.em_celery).
# Code is managed by git at /home/Admin/em-spapi-celery — this script does not copy sources.
#
# Usage:
#   sudo -u Admin git clone <url> /home/Admin/em-spapi-celery
#   sudo /home/Admin/em-spapi-celery/deploy/install.sh
#   # or, from inside that checkout:
#   sudo ./deploy/install.sh

set -euo pipefail

SCRIPT_REPO="$(cd "$(dirname "$0")/.." && pwd)"
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

if [[ ! -d "$APP_ROOT/.git" ]]; then
  echo "Expected a git checkout at ${APP_ROOT}." >&2
  echo "Clone first, then re-run this script:" >&2
  echo "  sudo -u ${APP_USER} git clone <repo-url> ${APP_ROOT}" >&2
  echo "  sudo ${APP_ROOT}/deploy/install.sh" >&2
  exit 1
fi

# Allow running from the checkout itself; refuse a different tree (no rsync).
if [[ "$(realpath "$SCRIPT_REPO")" != "$(realpath "$APP_ROOT")" ]]; then
  echo "install.sh must be run from ${APP_ROOT} (git-managed), not from ${SCRIPT_REPO}." >&2
  echo "  sudo ${APP_ROOT}/deploy/install.sh" >&2
  exit 1
fi

echo "==> Using git checkout at ${APP_ROOT}"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT"
chmod +x "$APP_ROOT/deploy/bin/run-worker.sh"
mkdir -p "$CONFIG_DIR"

echo "==> Installing Python dependencies (uv) as ${APP_USER}"
UV_BIN="${APP_HOME}/.local/bin/uv"
if [[ ! -x "$UV_BIN" ]]; then
  if command -v uv &>/dev/null; then
    UV_BIN="$(command -v uv)"
  else
    echo "==> uv not found; installing for ${APP_USER}"
    if ! command -v curl &>/dev/null; then
      apt-get update -qq
      apt-get install -y -qq curl
    fi
    sudo -u "$APP_USER" bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    UV_BIN="${APP_HOME}/.local/bin/uv"
    if [[ ! -x "$UV_BIN" ]]; then
      echo "uv install failed (expected ${UV_BIN})." >&2
      exit 1
    fi
  fi
fi
sudo -u "$APP_USER" bash -lc "export PATH='${APP_HOME}/.local/bin:\$PATH'; cd '$APP_ROOT' && '$UV_BIN' sync --no-dev"

if [[ ! -f "$CONFIG_DIR/config.ini" ]]; then
  install -m 0640 -o "$APP_USER" -g "$APP_USER" \
    "$APP_ROOT/deploy/config.ini.example" "$CONFIG_DIR/config.ini"
  echo "Created $CONFIG_DIR/config.ini — edit SP-API/ES credentials before start."
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
echo "  2. Edit ${CONFIG_DIR}/config.ini (SP-API, ES credentials)"
echo "  3. systemctl enable --now em-spapi-celery-catalog-worker em-spapi-celery-offer-worker"
echo "  4. journalctl -u em-spapi-celery-catalog-worker -f"
echo "     journalctl -u em-spapi-celery-offer-worker -f"
echo
echo "Upgrade later:"
echo "  sudo -u ${APP_USER} bash -lc 'cd ${APP_ROOT} && git pull && export PATH=\$HOME/.local/bin:\$PATH && uv sync --no-dev'"
echo "  sudo systemctl restart em-spapi-celery-catalog-worker em-spapi-celery-offer-worker"
echo
echo "Config/logs/data: ${CONFIG_DIR}/"
echo "EnvironmentFile:  /etc/conf.d/em_celery"
