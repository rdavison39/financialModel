#!/usr/bin/env bash
set -euo pipefail

# Install the Financial Model FastAPI backend as a systemd service.
# Usage:
#   sudo ./deploy/install_pi.sh /home/ron/financialModel ron
#
# The application directory must already contain the project, including
# database/financial_model.db. This script deliberately does NOT run Alembic
# migrations and does not modify the database schema.

APP_DIR="${1:-}"
SERVICE_USER="${2:-}"

if [[ -z "$APP_DIR" || -z "$SERVICE_USER" ]]; then
    echo "Usage: sudo $0 <application-directory> <service-user>"
    exit 2
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this installer with sudo/root."
    exit 1
fi

if [[ ! -d "$APP_DIR" ]]; then
    echo "Application directory not found: $APP_DIR"
    exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    echo "Service user does not exist: $SERVICE_USER"
    exit 1
fi

if [[ ! -f "$APP_DIR/database/financial_model.db" ]]; then
    echo "Database not found: $APP_DIR/database/financial_model.db"
    echo "Copy the existing Windows database to the Pi before installing."
    exit 1
fi

if [[ ! -f "$APP_DIR/requirements.txt" || ! -f "$APP_DIR/requirements-web.txt" ]]; then
    echo "requirements.txt and requirements-web.txt must exist in $APP_DIR"
    exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-web.txt"

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/.venv"
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/database"

sed \
    -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
    -e "s|__APP_DIR__|$APP_DIR|g" \
    "$APP_DIR/deploy/financial-model.service.template" \
    > /etc/systemd/system/financial-model.service

systemctl daemon-reload
systemctl enable financial-model.service
systemctl restart financial-model.service

sleep 2
if ! systemctl is-active --quiet financial-model.service; then
    echo "Financial Model service failed to start."
    systemctl --no-pager --full status financial-model.service || true
    exit 1
fi

if command -v curl >/dev/null 2>&1; then
    curl --fail --silent --show-error http://127.0.0.1:8000/api/health
    echo
else
    echo "Service is running. Install curl if you want the automatic health check."
fi

echo "Financial Model is running on port 8000."
echo "From another device on the LAN: http://<pi-ip>:8000/"
