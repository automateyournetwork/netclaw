#!/usr/bin/env bash
# Render alertmanager.yml from template using ALERT_RECEIVER_URL (T031).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export ALERT_RECEIVER_URL="${ALERT_RECEIVER_URL:-http://host.docker.internal:8099/webhook}"

if command -v envsubst >/dev/null 2>&1; then
  envsubst < alertmanager/alertmanager.yml.tmpl > alertmanager/alertmanager.yml
else
  # Pure bash fallback
  sed "s|\${ALERT_RECEIVER_URL}|${ALERT_RECEIVER_URL//|/\\|}|g" \
    alertmanager/alertmanager.yml.tmpl > alertmanager/alertmanager.yml
fi

echo "Rendered alertmanager/alertmanager.yml"
echo "  ALERT_RECEIVER_URL=${ALERT_RECEIVER_URL}"
