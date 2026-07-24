#!/bin/bash
# Build Docker image locally and optionally push to registry
# Usage: ./build.sh [--push]

set -euo pipefail

IMAGE="ghcr.io/byrn-baker/network-guardian-web"
TAG="latest"

echo "=== Building Network Guardian Web ==="
docker build -t "${IMAGE}:${TAG}" .

echo ""
echo "Image built: ${IMAGE}:${TAG}"
echo "  Size: $(docker image inspect ${IMAGE}:${TAG} --format='{{.Size}}' | numfmt --to=iec 2>/dev/null || docker image inspect ${IMAGE}:${TAG} --format='{{.Size}}')"

# Test the image
echo ""
echo "Running quick health check..."
CID=$(docker run -d --rm -p 3099:3000 \
  -e JWT_SECRET=test \
  -e "USERS=[]" \
  -e 'SITES_CONFIG={"home":{"name":"Home"}}' \
  -e PROMETHEUS_URL=http://localhost:9090 \
  -e LOKI_URL=http://localhost:3100 \
  -e ALERTMANAGER_URL=http://localhost:9093 \
  "${IMAGE}:${TAG}")

sleep 2

if curl -sf http://localhost:3099/healthz > /dev/null 2>&1; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed"
fi

docker stop "${CID}" > /dev/null 2>&1 || true

if [ "${1:-}" = "--push" ]; then
  echo ""
  echo "Pushing to registry..."
  docker push "${IMAGE}:${TAG}"
  echo "✅ Pushed ${IMAGE}:${TAG}"
fi
