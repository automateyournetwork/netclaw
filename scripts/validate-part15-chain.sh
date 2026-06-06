#!/usr/bin/env bash
# Validate Part 15 four-source correlation chain.
set -euo pipefail

VM_URL="${VM_URL:-http://localhost:8428}"
LOKI_URL="${LOKI_URL:-http://localhost:3100}"
METRICS_URL="${METRICS_URL:-http://localhost:9179/metrics}"
PASS=0
FAIL=0

check() {
  local name="$1" cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Part 15 Chain Validation ==="
echo ""

echo "1. Protocol MCP → VictoriaMetrics"
check "GRE tunnel up" "ip link show gre-rr1 | grep -q UP"
check "GRE peer reachable" "ping -c 1 -W 2 10.255.255.2"
check "protocol-mcp scrape up" "curl -sf '$VM_URL/api/v1/query' --data-urlencode 'query=up{job=\"protocol-mcp\"}' | grep -q '\"value\":\[.*,\"1\"]'"
RIB=$(curl -sf "$VM_URL/api/v1/query" --data-urlencode 'query=bgp_rib_size' | python3 -c "import sys,json; r=json.load(sys.stdin)['data']['result']; print(r[0]['value'][1] if r else 0)" 2>/dev/null || echo 0)
echo "       bgp_rib_size = $RIB"
if [[ "$RIB" != "0" ]]; then PASS=$((PASS + 1)); echo "  PASS  bgp_rib_size > 0"; else FAIL=$((FAIL + 1)); echo "  FAIL  bgp_rib_size > 0 (restart gateway after setup-part15-lab.sh)"; fi

echo ""
echo "2. SNMP → VictoriaMetrics (interface + IP SLA)"
DEVICES=$(curl -sf "$VM_URL/api/v1/label/device_name/values" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo 0)
echo "       devices reporting = $DEVICES"
check "18+ devices" "[[ $DEVICES -ge 18 ]]"
IFACE=$(curl -sf "$VM_URL/api/v1/query" --data-urlencode 'query=count(interface_status)' | python3 -c "import sys,json; r=json.load(sys.stdin)['data']['result']; print(r[0]['value'][1] if r else 0)" 2>/dev/null || echo 0)
echo "       interface_status series = $IFACE"
check "interface metrics present" "[[ $IFACE -gt 100 ]]"
IPSLA=$(curl -sf "$VM_URL/api/v1/query" --data-urlencode 'query=ip_sla_rtt_milliseconds' | python3 -c "import sys,json; r=json.load(sys.stdin).get('data',{}).get('result',[]); print(len(r))" 2>/dev/null || echo 0)
echo "       ip_sla_rtt_milliseconds series = $IPSLA"
check "IP SLA metrics in VM" "[[ $IPSLA -gt 0 ]]"

echo ""
echo "3. Syslog → Loki"
LOKI_LABELS=$(curl -sf "$LOKI_URL/loki/api/v1/labels" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo 0)
echo "       loki labels = $LOKI_LABELS"
check "Loki has streams (labels)" "[[ $LOKI_LABELS -gt 0 ]]"

echo ""
echo "4. Grafana alerts"
ALERTS=$(curl -sf -u admin:netclaw 'http://localhost:3000/api/v1/provisioning/alert-rules' | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
echo "       provisioned rules = $ALERTS"
check "Grafana alert rules provisioned" "[[ $ALERTS -ge 3 ]]"

echo ""
echo "=== Summary: $PASS passed, $FAIL failed ==="
if [[ $FAIL -gt 0 ]]; then
  echo "Run: bash scripts/setup-part15-lab.sh"
  echo "Then restart OpenClaw gateway and re-run this script."
  exit 1
fi
exit 0