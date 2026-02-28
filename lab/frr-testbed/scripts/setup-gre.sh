#!/usr/bin/env bash
# Setup GRE tunnel from host (WSL/Linux) to Edge1 container
# Requires: sudo, Docker running, edge1 container on 10.0.100.1
set -euo pipefail

HOST_PEERING_IP="${HOST_PEERING_IP:-10.0.100.100}"
EDGE1_PEERING_IP="${EDGE1_PEERING_IP:-10.0.100.1}"
TUNNEL_LOCAL="${TUNNEL_LOCAL:-172.16.0.2}"
TUNNEL_REMOTE="${TUNNEL_REMOTE:-172.16.0.1}"

echo "=== NetClaw GRE Tunnel Setup ==="
echo "  Host peering IP:  $HOST_PEERING_IP"
echo "  Edge1 peering IP: $EDGE1_PEERING_IP"
echo "  Tunnel local:     $TUNNEL_LOCAL/30"
echo "  Tunnel remote:    $TUNNEL_REMOTE/30"
echo ""

# --- Host side ---
echo "[1/4] Adding host IP to peering network..."
# Find the Docker bridge for the peering network
# Find the Docker bridge for the peering network by ID (br-<short-id>)
PEERING_NET_ID=$(docker network inspect frr-testbed_peering -f '{{.Id}}' 2>/dev/null | cut -c1-12 || echo "")
if [ -n "$PEERING_NET_ID" ]; then
  PEERING_BRIDGE="br-${PEERING_NET_ID}"
fi

if [ -z "$PEERING_BRIDGE" ] || ! ip link show "$PEERING_BRIDGE" &>/dev/null; then
  # Fallback: find bridge by subnet
  PEERING_BRIDGE=$(ip route show 10.0.100.0/24 2>/dev/null | awk '{print $3}' || echo "")
fi

if [ -z "$PEERING_BRIDGE" ]; then
  echo "ERROR: Cannot find peering network bridge. Is docker compose up?"
  exit 1
fi

echo "  Found bridge: $PEERING_BRIDGE"
ip addr add "$HOST_PEERING_IP/24" dev "$PEERING_BRIDGE" 2>/dev/null || \
  echo "  (IP already assigned)"

echo "[2/4] Creating GRE tunnel on host..."
ip tunnel del gre-netclaw 2>/dev/null || true
ip tunnel add gre-netclaw mode gre \
  local "$HOST_PEERING_IP" \
  remote "$EDGE1_PEERING_IP" \
  ttl 255
ip addr add "$TUNNEL_LOCAL/30" dev gre-netclaw
ip link set gre-netclaw up

echo "[3/4] Creating GRE tunnel inside Edge1 container..."
docker exec netclaw-edge1 ip tunnel del gre-netclaw 2>/dev/null || true
docker exec netclaw-edge1 ip tunnel add gre-netclaw mode gre \
  local "$EDGE1_PEERING_IP" \
  remote "$HOST_PEERING_IP" \
  ttl 255
# FRR zebra assigns the address from frr.conf once the interface exists;
# only add it manually if zebra hasn't already done so.
docker exec netclaw-edge1 ip addr add "$TUNNEL_REMOTE/30" dev gre-netclaw 2>/dev/null || \
  echo "  (address already assigned by FRR — OK)"
docker exec netclaw-edge1 ip link set gre-netclaw up

echo "[4/4] Adding host route to lab networks via GRE..."
ip route add 10.0.12.0/24 via "$TUNNEL_REMOTE" dev gre-netclaw 2>/dev/null || true
ip route add 10.0.23.0/24 via "$TUNNEL_REMOTE" dev gre-netclaw 2>/dev/null || true
ip route add 1.1.1.1/32 via "$TUNNEL_REMOTE" dev gre-netclaw 2>/dev/null || true
ip route add 2.2.2.2/32 via "$TUNNEL_REMOTE" dev gre-netclaw 2>/dev/null || true
ip route add 3.3.3.3/32 via "$TUNNEL_REMOTE" dev gre-netclaw 2>/dev/null || true

echo ""
echo "=== GRE Tunnel Ready ==="
echo "  ping $TUNNEL_REMOTE  (Edge1 tunnel endpoint)"
echo "  ping 1.1.1.1         (Edge1 loopback via GRE)"
echo ""
echo "  NetClaw can now peer BGP with Edge1 at $TUNNEL_REMOTE (AS 65000)"
