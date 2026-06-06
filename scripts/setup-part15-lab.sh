#!/usr/bin/env bash
# Part 15 lab prerequisites: GRE to RR1, BGP peer, IP SLA, OTEL regen, observability restart.
set -euo pipefail

NETCLAW_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANSIBLE_LAB="${ANSIBLE_LAB:-$HOME/Nautobot-Workshop/ansible-lab}"
GRE_LOCAL="${GRE_LOCAL:-192.168.220.1}"
GRE_REMOTE="${GRE_REMOTE:-192.168.220.11}"
TUNNEL_INNER_LOCAL="${TUNNEL_INNER_LOCAL:-10.255.255.1}"
TUNNEL_INNER_REMOTE="${TUNNEL_INNER_REMOTE:-10.255.255.2}"

echo "=== Part 15 Lab Setup ==="

# 1. GRE tunnel (host → RR1)
if ! ip link show gre-rr1 &>/dev/null; then
  echo "[1/6] Creating GRE tunnel gre-rr1..."
  sudo ip tunnel add gre-rr1 mode gre remote "$GRE_REMOTE" local "$GRE_LOCAL" ttl 255
else
  echo "[1/6] GRE tunnel gre-rr1 exists"
fi
sudo ip addr replace "${TUNNEL_INNER_LOCAL}/30" dev gre-rr1 2>/dev/null || \
  sudo ip addr add "${TUNNEL_INNER_LOCAL}/30" dev gre-rr1
sudo ip link set gre-rr1 up

if ping -c 2 -W 2 "$TUNNEL_INNER_REMOTE" &>/dev/null; then
  echo "  GRE OK: $TUNNEL_INNER_LOCAL → $TUNNEL_INNER_REMOTE"
else
  echo "  WARN: GRE ping to $TUNNEL_INNER_REMOTE failed (RR1 Tunnel0 may need deploy)"
fi

# 2. RR1 BGP neighbor to NetClaw (if missing)
if [[ -d "$ANSIBLE_LAB" ]]; then
  echo "[2/6] Configuring RR1 BGP neighbor 10.255.255.1..."
  cd "$ANSIBLE_LAB" && . .venv/bin/activate
  ansible RR1 -m ios_config -a 'lines=" neighbor 10.255.255.1 peer-group NETCLAW-MGMT-PEERS\n neighbor 10.255.255.1 description NetClaw-Protocol-MCP\n neighbor 10.255.255.1 update-source Tunnel0\n neighbor 10.255.255.1 activate" parents="router bgp 65000\n address-family ipv4"' -o || true
else
  echo "[2/6] SKIP: ansible-lab not found at $ANSIBLE_LAB"
fi

# 3. IP SLA on PE routers (recreate jitter probes — IOL needs frequency at create time)
echo "[3/6] Fixing IP SLA on PE1-PE3..."
bash "$NETCLAW_ROOT/scripts/fix-pe-ip-sla.sh" || echo "  WARN: IP SLA fix had errors"

# 4. Regenerate OTEL config
echo "[4/6] Regenerating OTEL collector config..."
python3 "$NETCLAW_ROOT/observability/otel-collector/generate-config.py"

# 5. Restart observability stack
echo "[5/6] Restarting observability stack..."
docker compose -f "$NETCLAW_ROOT/observability/docker-compose.observability.yml" restart otel-collector grafana 2>/dev/null || \
  docker compose -f "$NETCLAW_ROOT/observability/docker-compose.observability.yml" up -d

# 6. Verification hints
echo "[6/6] Verification:"
echo "  curl -s http://localhost:9179/metrics | grep bgp_rib_size"
echo "  curl -s 'http://localhost:8428/api/v1/query?query=ip_sla_rtt'"
echo "  Restart OpenClaw gateway to reload protocol-mcp (AS 65099)"
echo ""
echo "Protocol MCP must run with cap_net_raw. After gateway restart:"
echo "  bgp_get_peers → Established with 10.255.255.2"
echo "  bgp_rib_size > 0 when RR1 reflects lab routes"
echo ""
echo "Done. Run: bash $NETCLAW_ROOT/scripts/validate-part15-chain.sh"