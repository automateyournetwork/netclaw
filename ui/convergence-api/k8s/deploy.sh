#!/bin/bash
# Deploy Network Guardian Web to K3s
# Prerequisites: kubectl configured, secret.yml created from secret.yml.example

set -euo pipefail

NAMESPACE="observability"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Deploying Network Guardian Web to ${NAMESPACE} ==="

# Check secret exists
if [ ! -f "${SCRIPT_DIR}/secret.yml" ]; then
  echo "ERROR: k8s/secret.yml not found."
  echo "  Copy secret.yml.example to secret.yml and fill in real values."
  exit 1
fi

# Apply manifests
echo "Applying ConfigMap..."
kubectl apply -f "${SCRIPT_DIR}/configmap.yml"

# Optional: events.js ConfigMap overlay if still using an old image without Stage 6.
# Current deployment.yml uses docker.io/library/network-guardian-web:stage6-baked
# (baked locally into node containerd; ghcr push needs packages:write).
EVENTS_JS="${SCRIPT_DIR}/../src/routes/events.js"
if [ -f "${EVENTS_JS}" ] && [ "${NGW_EVENTS_CM_OVERLAY:-0}" = "1" ]; then
  echo "Applying events.js ConfigMap overlay (NGW_EVENTS_CM_OVERLAY=1)..."
  kubectl -n "${NAMESPACE}" create configmap network-guardian-events-js \
    --from-file=events.js="${EVENTS_JS}" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

echo "Applying Secret..."
kubectl apply -f "${SCRIPT_DIR}/secret.yml"

echo "Applying Service..."
kubectl apply -f "${SCRIPT_DIR}/service.yml"

echo "Applying Deployment..."
kubectl apply -f "${SCRIPT_DIR}/deployment.yml"

# Wait for rollout
echo "Waiting for rollout..."
kubectl -n ${NAMESPACE} rollout status deployment/network-guardian-web --timeout=120s

echo ""
echo "=== Deploy complete ==="
echo "  Service: network-guardian-web.${NAMESPACE}.svc:80"
echo "  Health:  kubectl -n ${NAMESPACE} exec deploy/network-guardian-web -- wget -qO- http://localhost:3000/healthz"
echo ""
echo "Next steps:"
echo "  1. Add cloudflared tunnel route for guardian.byrnbaker.me"
echo "  2. Add CNAME DNS record in Cloudflare"
