#!/usr/bin/env bash
# Alert readiness + scenario map for human-in-the-loop agent testing.
# Does NOT inject failures — checks prerequisites and lists how to fire each rule.
set -euo pipefail

VM="${VICTORIA_METRICS_URL:-http://localhost:8428}"
GRAFANA="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USERNAME:-admin}"
GRAFANA_PASS="${GRAFANA_PASSWORD:-netclaw}"
LOKI="${LOKI_URL:-http://localhost:3100}"
TESTBED="${PYATS_TESTBED_PATH:-testbed/testbed.yaml}"
CLAB_TOPO="${CLAB_TOPO:-$HOME/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml}"

vm_count() {
  curl -sf "$VM/api/v1/query" --data-urlencode "query=$1" | python3 -c "
import sys,json
r=json.load(sys.stdin).get('data',{}).get('result',[])
print(r[0]['value'][1] if r else '0')
" 2>/dev/null || echo 0
}

vm_fires() {
  curl -sf "$VM/api/v1/query" --data-urlencode "query=$1" | python3 -c "
import sys,json
r=json.load(sys.stdin).get('data',{}).get('result',[])
print('YES' if r else 'no')
" 2>/dev/null || echo "?"
}

grafana_firing() {
  local uid="$1"
  curl -sf -u "$GRAFANA_USER:$GRAFANA_PASS" \
    "$GRAFANA/api/alertmanager/grafana/api/v2/alerts" | python3 -c "
import sys,json
uid='$uid'
for a in json.load(sys.stdin):
    if a.get('labels',{}).get('rule_uid')==uid or uid in str(a.get('labels',{})):
        pass
" 2>/dev/null
  curl -sf -u "$GRAFANA_USER:$GRAFANA_PASS" \
    "$GRAFANA/api/alertmanager/grafana/api/v2/alerts" | python3 -c "
import sys,json
name='$1'
for a in json.load(sys.stdin):
    if a.get('labels',{}).get('alertname','')==name:
        print('FIRING', a.get('labels',{}).get('device_name',''), a.get('labels',{}).get('interface',''))
" 2>/dev/null | head -3
}

echo "================================================================"
echo " NetClaw Alert Validation — environment + scenario map"
echo "================================================================"
echo ""
echo "HOST:     $(hostname) ($(uname -r))"
echo "NETCLAW:  $(cd "$(dirname "$0")/.." && pwd)"
echo "CLAB:     $CLAB_TOPO"
echo "TESTBED:  $TESTBED"
echo ""
echo "Observability (host 192.168.3.252):"
echo "  VictoriaMetrics  $VM"
echo "  Grafana          $GRAFANA  (alerts folder: Lab Network)"
echo "  Loki             $LOKI"
echo "  OTEL collector   192.168.3.252 (syslog + Arista SNMP)"
echo "  bgp-snmp-exp     192.168.3.252 (Cisco interface_status + BGP + IP SLA)"
echo "  bgp-bmp-cons     192.168.3.252 (BMP withdrawals)"
echo "  bgp-gnmi-exp     192.168.3.252 (Arista BGP)"
echo ""
echo "Lab devices (CSR IOS-XE via SSH admin@192.168.220.x):"
echo "  PE1=192.168.220.6  RR1=192.168.220.11  P1=192.168.220.2"
echo "  Scenario driver:  bash scripts/observability/run-scenario-b.sh"
echo "                    PYATS_TESTBED_PATH=$TESTBED python3 scripts/run_scenario_b.py"
echo ""

echo "--- Metric prerequisites ---"
echo "  interface_status (bgp-snmp):     $(vm_count 'count(interface_status{job="netclaw-bgp-snmp"})') series"
echo "  netclaw_bgp_peer_state (snmp):   $(vm_count 'count(netclaw_bgp_peer_state{job="netclaw-bgp-snmp"})') series"
echo "  netclaw_bgp_prefix_withdrawals:  $(vm_count 'count(netclaw_bgp_prefix_withdrawals_total)') series"
echo "  netclaw_path_jitter_ms (max):    $(vm_count 'max(netclaw_path_jitter_ms)')"
echo "  Loki device_name streams:        $(curl -sf "$LOKI/loki/api/v1/label/device_name/values" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo 0) devices"
RULES=$(curl -sf -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA/api/v1/provisioning/alert-rules" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
echo "  Grafana provisioned rules:       $RULES"
echo ""

echo "--- PromQL would-fire NOW (instant) ---"
printf "  %-36s %s\n" "Lab Interface Down" "$(vm_fires 'count(interface_status{job="netclaw-bgp-snmp"} == 2)')"
printf "  %-36s %s\n" "ALERT-001 peer down" "$(vm_fires 'count(netclaw_bgp_peer_state{job="netclaw-bgp-snmp",device_name=~"rr1|pe.*"} != 6)')"
printf "  %-36s %s\n" "ALERT-002 prefix drop" "$(vm_fires '(netclaw_bgp_peer_prefixes_received < 0.8 * avg_over_time(netclaw_bgp_peer_prefixes_received[1h])) and netclaw_bgp_peer_prefixes_received > 0')"
printf "  %-36s %s\n" "ALERT-003 session flap" "$(vm_fires 'increase(netclaw_bgp_peer_established_transitions_total[15m]) > 0')"
printf "  %-36s %s\n" "ALERT-004 BMP withdraw burst" "$(vm_fires 'sum by (device_name, prefix) (increase(netclaw_bgp_prefix_withdrawals_total[2m])) > 10')"
printf "  %-36s %s\n" "ALERT-005 UPDATE storm" "$(vm_fires 'rate(netclaw_bgp_peer_in_updates_total{job="netclaw-bgp-snmp"}[5m]) > 3 * avg_over_time(rate(netclaw_bgp_peer_in_updates_total{job="netclaw-bgp-snmp"}[5m])[1d:])')"
printf "  %-36s %s\n" "ALERT-006 path jitter" "$(vm_fires '(max(netclaw_path_jitter_ms{device_name=~"pe.*|ce.*"}) > 20) or (max(netclaw_path_rtt_ms{device_name=~"pe.*"}) > 60)')"
printf "  %-36s %s\n" "ALERT-007 iface+BGP" "$(vm_fires 'changes(interface_status{device_role=~"pe|p",job="netclaw-bgp-snmp"}[5m]) > 0 and on(device_name) rate(netclaw_bgp_peer_in_updates_total{job="netclaw-bgp-snmp"}[5m]) > 0')"
echo ""

echo "--- Grafana FIRING now ---"
curl -sf -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA/api/alertmanager/grafana/api/v2/alerts" 2>/dev/null | python3 -c "
import sys,json
alerts=json.load(sys.stdin)
if not alerts:
    print('  (none)')
for a in alerts:
    l=a.get('labels',{})
    print(f\"  {l.get('alertname','?')}  device={l.get('device_name','')}  iface={l.get('interface','')}  severity={l.get('severity','')}\")
" 2>/dev/null || echo "  (Grafana API unavailable)"
echo ""

cat <<'MATRIX'

--- Scenario → Alert → Agent skill (human-in-the-loop) ---

| Scenario | Trigger | Expected alert(s) | Wait | Agent skill chain |
|----------|---------|-------------------|------|-------------------|
| A Port down | PE1: `shutdown Gi2` | Lab Interface Down, ALERT-007 | ~3 min | lab-alert-triage → lab-troubleshoot |
| B Link flap | PE1: shutdown Gi2 (dual-homed) | ALERT-007, maybe ALERT-005 | ~3 min | bgp-route-stability-watch → lab-troubleshoot |
| C BGP peer loss | PE1: shutdown Gi2 + Gi3 | ALERT-001, ALERT-002, ALERT-003 | ~5 min | bgp-route-stability-watch → lab-alert-triage |
| D BMP withdraw | RR1 path flap or inject | ALERT-004 | ~5 min | bgp-route-stability-watch (BMP step) |
| E Iface errors | Repeated flap / error port | Lab Interface Errors | ~5 min | lab-alert-triage |
| F Packet loss | Blackhole PE probe target | ALERT-006 | ~10 min | bgp-route-stability-watch (path step) |

Investigation data sources (use these PromQL labels):
  interface_status{device_name="pe1",interface="GigabitEthernet2",job="netclaw-bgp-snmp"}
  netclaw_bgp_peer_state{device_name="pe1",job="netclaw-bgp-snmp"}
  rate(netclaw_bgp_prefix_withdrawals_total{device_name="rr1"}[5m])
  {device_name="pe1"} |~ "UPDOWN|ADJCHANGE"   (Loki)

Run all scenarios (pyATS + Grafana gates):
  bash scripts/observability/run-all-scenarios.sh --all

Run single scenario:
  bash scripts/observability/run-scenario-a.sh   # port down
  bash scripts/observability/run-scenario-b.sh   # link flap
  bash scripts/observability/run-scenario-c.sh   # BGP peer loss (~7 min)
  bash scripts/observability/run-scenario-e.sh   # rapid flaps (~12 min)
  bash scripts/observability/run-scenario-f.sh   # path jitter (~15 min)

Watch Grafana alert state during test:
  curl -s -u admin:netclaw http://localhost:3000/api/alertmanager/grafana/api/v2/alerts | python3 -m json.tool

Known baseline noise:
  Arista cEOS leaves report interface 7000001 down → Lab Interface Down fires on
  east-leaf01/west-leaf01 (OTEL/gNMI). Filter triage to device_name=~"pe|p|rr|ce"
  or job=netclaw-bgp-snmp for CSR scenario tests.

MATRIX

echo "=== Next: run one scenario, wait for 'for:' duration, re-run this script ==="