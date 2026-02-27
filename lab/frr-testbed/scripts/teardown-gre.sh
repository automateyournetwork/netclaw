#!/usr/bin/env bash
# Teardown GRE tunnel between host and Edge1
set -euo pipefail

HOST_PEERING_IP="${HOST_PEERING_IP:-10.0.100.100}"

echo "=== Tearing Down GRE Tunnel ==="

echo "[1/3] Removing host routes..."
ip route del 10.0.12.0/24 2>/dev/null || true
ip route del 10.0.23.0/24 2>/dev/null || true
ip route del 1.1.1.1/32 2>/dev/null || true
ip route del 2.2.2.2/32 2>/dev/null || true
ip route del 3.3.3.3/32 2>/dev/null || true

echo "[2/3] Removing host GRE tunnel..."
ip tunnel del gre-netclaw 2>/dev/null || true

echo "[3/3] Removing Edge1 GRE tunnel..."
docker exec netclaw-edge1 ip tunnel del gre-netclaw 2>/dev/null || true

# Remove host IP from peering bridge
PEERING_BRIDGE=$(ip route show 10.0.100.0/24 2>/dev/null | awk '{print $3}' || echo "")
if [ -n "$PEERING_BRIDGE" ]; then
  ip addr del "$HOST_PEERING_IP/24" dev "$PEERING_BRIDGE" 2>/dev/null || true
fi

echo ""
echo "=== GRE Tunnel Removed ==="
