#!/usr/bin/env bash
set -euo pipefail
NETCLAW_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Scenario D runner ==="

# One BGP speaker at a time
if ss -tlnp 2>/dev/null | grep -q 18789; then
  echo "Pausing OpenClaw gateway..."
  for pid in $(ss -tlnp 2>/dev/null | grep 18789 | grep -oP 'pid=\K[0-9]+' | sort -u); do
    kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 4
fi

pkill -f 'mcp-servers/protocol-mcp/server.py' 2>/dev/null || true
sleep 2

python3 "$NETCLAW_ROOT/scripts/scenario-d-flap.py" | tee /tmp/scenario-d-transcript.txt

echo ""
echo "=== VictoriaMetrics correlation ==="
VM=http://localhost:8428
echo "Withdrawal rate:"
curl -sf "$VM/api/v1/query" --data-urlencode 'query=sum(rate(bgp_route_withdrawals_total[10m]))' | python3 -m json.tool 2>/dev/null || true
echo "Interface flaps (should be 0 for injection-only):"
curl -sf "$VM/api/v1/query" --data-urlencode 'query=sum(changes(interface_status[10m])>0)' | python3 -m json.tool 2>/dev/null || true
echo "IP SLA RTT (path quality unchanged):"
curl -sf "$VM/api/v1/query" --data-urlencode 'query=ip_sla_rtt_milliseconds{device_name=~"pe.*"}' | python3 -c "
import sys,json
for x in json.load(sys.stdin).get('data',{}).get('result',[]):
    print(' ', x['metric'].get('device_name'), x['value'][1])
" 2>/dev/null || true

echo ""
echo "Restarting OpenClaw gateway..."
openclaw gateway
echo "Transcript saved: /tmp/scenario-d-transcript.txt"