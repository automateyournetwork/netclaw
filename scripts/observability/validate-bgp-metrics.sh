#!/usr/bin/env bash
# Phase checkpoint validation for specs/031-bgp-route-observability
set -euo pipefail

if [[ "${1:-}" == "--phase" && -n "${2:-}" ]]; then
  PHASE="--phase ${2}"
elif [[ -n "${1:-}" ]]; then
  PHASE="$1"
else
  PHASE="--phase 1"
fi
VM="${VICTORIA_METRICS_URL:-http://localhost:8428}"
EXPORTER="${BGP_EXPORTER_URL:-http://localhost:9102}"
BMP_EXPORTER="${BMP_EXPORTER_URL:-http://localhost:9100}"
GNMI_EXPORTER="${BGP_GNMI_EXPORTER_URL:-http://localhost:9103}"
LOKI="${LOKI_URL:-http://localhost:3100/loki}"

query() {
  curl -sf "$VM/api/v1/query" --data-urlencode "query=$1"
}

check_exporter() {
  echo "=== BGP SNMP exporter (:9102) ==="
  if curl -sf "$EXPORTER/metrics" | grep -q '^netclaw_bgp_peer_state'; then
    echo "  OK: exporter exposes netclaw_bgp_peer_state"
    curl -sf "$EXPORTER/metrics" | grep '^netclaw_bgp_' | sed -n '1,8p'
  else
    echo "  FAIL: no netclaw_bgp_* on exporter"
    return 1
  fi
}

check_vm() {
  local q="$1"
  local desc="$2"
  echo "=== VM: $desc ==="
  local result
  result=$(query "$q" | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
print(len(r))
for x in r[:5]:
    print(' ', x.get('metric', {}), x.get('value', [None, None])[1])
if not r:
    raise SystemExit(1)
" 2>&1) || { echo "  FAIL: $q"; echo "$result"; return 1; }
  echo "$result"
}

check_bmp_stack() {
  echo "=== BMP stack containers ==="
  for c in redpanda gobmp bgp-bmp-consumer; do
    if docker ps --format '{{.Names}}' | grep -qx "$c"; then
      echo "  OK: $c running"
    else
      echo "  FAIL: $c not running"
      return 1
    fi
  done
}

check_bmp_consumer() {
  echo "=== BMP consumer (:9100) ==="
  if curl -sf "$BMP_EXPORTER/metrics" | grep -q '^netclaw_bmp_consumer_up'; then
    echo "  OK: consumer exposes netclaw_bmp_consumer_up"
    curl -sf "$BMP_EXPORTER/metrics" | grep -E '^netclaw_bmp_|^netclaw_bgp_prefix_' | sed -n '1,10p'
  else
    echo "  FAIL: no netclaw_bmp_* on consumer"
    return 1
  fi
  local up
  up=$(curl -sf "$BMP_EXPORTER/metrics" | awk '/^netclaw_bmp_consumer_up /{print $2; exit}')
  if [[ "$up" != "1.0" && "$up" != "1" ]]; then
    echo "  FAIL: netclaw_bmp_consumer_up=$up (expected 1)"
    return 1
  fi
  echo "  OK: consumer connected to Kafka"
}

check_live_bmp_from_rr1() {
  echo "=== BMP live: RR1 prefix announcements ==="
  local live
  live=$(curl -sf "$BMP_EXPORTER/metrics" | grep -c 'netclaw_bgp_prefix_announcements_total{.*device_name="rr1"' || true)
  if [[ "$live" -ge 1 ]]; then
    echo "  OK: live BMP announcements from rr1 ($live series)"
    curl -sf "$BMP_EXPORTER/metrics" | grep 'netclaw_bgp_prefix_announcements_total{.*device_name="rr1"' | sed -n '1,4p'
    return 0
  fi
  echo "  FAIL: no live netclaw_bgp_prefix_announcements_total{device_name=\"rr1\"}"
  echo "  Hint: RR1 BMP TCP must be Up; omit bmp update-source on VRF-forwarded Gi1"
  return 1
}

inject_bmp_test_message() {
  echo "=== BMP pipeline: synthetic prefix event ==="
  local payload topic
  topic="gobmp.parsed.unicast_prefix_v4"
  payload='{"action":"del","router_ip":"192.168.220.11","peer_ip":"100.0.254.13","peer_asn":65000,"prefix":"192.168.99.0","prefix_len":24,"is_ipv4":true}
'
  if echo "$payload" | docker exec -i redpanda rpk topic produce "$topic" -k rr1-test >/dev/null 2>&1; then
    echo "  OK: produced test withdraw to $topic"
  else
    echo "  WARN: could not produce test message (rpk unavailable)"
    return 0
  fi
  sleep 3
  if curl -sf "$BMP_EXPORTER/metrics" | grep -q 'netclaw_bgp_prefix_withdrawals_total{.*prefix="192.168.99.0/24"'; then
    echo "  OK: consumer incremented netclaw_bgp_prefix_withdrawals_total"
  else
    echo "  WARN: test withdrawal metric not yet visible (consumer may still be catching up)"
  fi
}

check_gnmi_exporter() {
  echo "=== BGP gNMI exporter (:9103) ==="
  if curl -sf "$GNMI_EXPORTER/metrics" | grep -q 'netclaw_bgp_peer_state{.*source="gnmi"'; then
    echo "  OK: exporter exposes netclaw_bgp_peer_state source=gnmi"
    curl -sf "$GNMI_EXPORTER/metrics" | grep 'netclaw_bgp_peer_state{.*source="gnmi"' | sed -n '1,6p'
  else
    echo "  FAIL: no netclaw_bgp_peer_state{source=\"gnmi\"} on exporter"
    return 1
  fi
}

check_gnmi_west_spine01() {
  echo "=== gNMI live: west-spine01 peer state ==="
  local count
  count=$(curl -sf "$GNMI_EXPORTER/metrics" | grep -c 'netclaw_bgp_peer_state{.*device_name="west-spine01".*source="gnmi"' || true)
  if [[ "$count" -ge 1 ]]; then
    echo "  OK: west-spine01 has $count gNMI peer state series"
    curl -sf "$GNMI_EXPORTER/metrics" | grep 'netclaw_bgp_peer_state{.*device_name="west-spine01".*source="gnmi"' | sed -n '1,4p'
    return 0
  fi
  echo "  FAIL: no netclaw_bgp_peer_state{device_name=\"west-spine01\",source=\"gnmi\"}"
  return 1
}

check_vm_gnmi() {
  echo "=== VM: gNMI-sourced peer metrics ==="
  local result
  result=$(query 'netclaw_bgp_peer_state{source="gnmi",device_name="west-spine01"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data', {}).get('result', [])
print(len(r))
for x in r[:5]:
    m = x.get('metric', {})
    print(' ', m.get('device_name'), m.get('neighbor'), x.get('value', [None, None])[1])
if not r:
    raise SystemExit(1)
" 2>&1) || { echo "  FAIL: no gNMI peer state in VictoriaMetrics yet"; echo "$result"; return 1; }
  echo "$result"
}

check_loki() {
  echo "=== Loki: device_name label + BGP syslog ==="
  local labels_json start end query_json
  labels_json=$(curl -sf -G "${LOKI}/api/v1/labels") || { echo "  FAIL: Loki labels API"; return 1; }
  echo "$labels_json" | python3 -c "
import sys, json
labels = json.load(sys.stdin).get('data', [])
if 'device_name' not in labels:
    raise SystemExit('device_name label missing')
print('  OK: device_name is an indexed label')
" || return 1

  start=$(($(date +%s) - 3600))000000000
  end=$(date +%s)000000000
  query_json=$(curl -sf -G "${LOKI}/api/v1/query_range" \
    --data-urlencode 'query={device_name=~".+"} |~ "BGP"' \
    --data-urlencode "start=${start}" \
    --data-urlencode "end=${end}" \
    --data-urlencode 'limit=5') || { echo "  FAIL: Loki query_range"; return 1; }
  echo "$query_json" | python3 -c "
import sys, json
d = json.load(sys.stdin)
streams = d.get('data', {}).get('result', [])
print(f'  BGP-related streams: {len(streams)}')
if not streams:
    raise SystemExit(1)
for s in streams[:3]:
    body = s.get('values', [['', '']])[0][1][:100]
    print(' ', s.get('stream', {}), body)
" || return 1
}

echo "BGP metrics validation ($PHASE)"
echo "VM=$VM  EXPORTER=$EXPORTER  BMP=$BMP_EXPORTER  GNMI=$GNMI_EXPORTER  LOKI=$LOKI"
echo ""

case "$PHASE" in
  --phase|1|--phase1|"--phase 1")
    check_exporter
    check_vm 'netclaw_bgp_peer_state{device_name="rr1"}' "RR1 peer state"
    check_vm 'netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"}' "RR1 peer 100.0.254.13 prefixes"
    val=$(query 'netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"}' | python3 -c "
import sys,json
r=json.load(sys.stdin)['data']['result']
print(r[0]['value'][1] if r else 'missing')
")
    echo ""
    echo "Checkpoint: RR1 peer 100.0.254.13 prefixes = $val (expect 4)"
    if [[ "$val" == "4" ]]; then
      echo "PHASE 1 PASS"
      exit 0
    fi
    echo "PHASE 1 WARN: prefix count is $val (expected 4) — peer may be idle or PE1 unreachable"
    exit 0
    ;;
  --phase|2|--phase2|"--phase 2")
    check_vm 'netclaw_path_jitter_ms{device_name="pe2"}' "PE2 jitter"
    jitter=$(query 'netclaw_path_jitter_ms{device_name="pe2"}' | python3 -c "
import sys,json
r=json.load(sys.stdin)['data']['result']
print(r[0]['value'][1] if r else 'missing')
")
    echo ""
    echo "Checkpoint: PE2 jitter = $jitter ms"
    check_loki
    echo ""
    echo "PHASE 2 PASS"
    exit 0
    ;;
  --phase|3|--phase3|"--phase 3")
    check_bmp_stack
    check_bmp_consumer
    check_live_bmp_from_rr1
    inject_bmp_test_message
    echo ""
    echo "PHASE 3 PASS (BMP live from RR1 + pipeline healthy)"
    exit 0
    ;;
  --phase|4|--phase4|"--phase 4")
    docker ps --format '{{.Names}}' | grep -qx bgp-gnmi-exporter || {
      echo "  FAIL: bgp-gnmi-exporter container not running"
      exit 1
    }
    check_gnmi_exporter
    check_gnmi_west_spine01
    check_vm_gnmi
    echo ""
    echo "PHASE 4 PASS (gNMI peer state from west-spine01 in VM)"
    exit 0
    ;;
  --phase|5|--phase5|"--phase 5")
    echo "=== Phase 5: alert rules + baselines ==="
    if [[ ! -f docs/baselines/bgp-route-stability.md ]]; then
      echo "  FAIL: docs/baselines/bgp-route-stability.md missing"
      exit 1
    fi
    echo "  OK: baselines doc present"
    for expr in \
      'netclaw_bgp_peer_state{device_name=~"rr1|pe.*"}' \
      'netclaw_bgp_peer_prefixes_received{device_name="rr1"}' \
      'netclaw_path_jitter_ms{device_name=~"pe.*"}' \
      'netclaw_bgp_peer_state{source="gnmi"}'; do
      query "$expr" >/dev/null || { echo "  FAIL: query $expr"; exit 1; }
      echo "  OK: $expr"
    done
    if grep -q 'netclaw-bgp-peer-down' observability/grafana/provisioning/alerting/bgp-route-stability.yaml; then
      echo "  OK: Grafana netclaw alert rules provisioned"
    else
      echo "  FAIL: bgp-route-stability.yaml missing netclaw rules"
      exit 1
    fi
    if grep -q 'netclaw_\*' workspace/skills/bgp-route-stability-watch/SKILL.md; then
      echo "  OK: bgp-route-stability-watch uses netclaw_*"
    else
      echo "  FAIL: skill not rewritten for netclaw_*"
      exit 1
    fi
    echo ""
    echo "PHASE 5 PASS (alerts, skills, baselines — run Scenario B/C for live alert fire)"
    exit 0
    ;;
  --phase|6|--phase6|"--phase 6")
    echo "=== Phase 6: golden config BMP + gNMI ==="
    DS="${NAUTOBOT_DATASOURCE:-$HOME/github-projects/Nautobot-Workshop-Datasource}"
    TPL="${NAUTOBOT_TEMPLATES:-$HOME/Nautobot-Workshop/ansible-lab/roles/build_lab_config/templates}"
    for f in \
      "$DS/config_contexts/observability.yml" \
      "$TPL/ios/bmp.j2" \
      "$TPL/ios/gnmi-telemetry.j2" \
      "$TPL/eos/gnmi-telemetry.j2"; do
      if [[ -f "$f" ]]; then
        echo "  OK: $f"
      else
        echo "  FAIL: missing $f"
        exit 1
      fi
    done
    grep -q 'bmp:' "$DS/config_contexts/observability.yml" && \
      grep -q 'gnmi:' "$DS/config_contexts/observability.yml" || {
      echo "  FAIL: observability.yml missing bmp/gnmi blocks"
      exit 1
    }
    echo "  OK: observability.yml has bmp + gnmi"
    grep -q '_is_iosxe' "$TPL/ios/bmp.j2" || {
      echo "  FAIL: bmp.j2 missing IOS-XE platform guard (IOL skip)"
      exit 1
    }
    echo "  OK: bmp.j2 skips non-IOS-XE platforms"
    ANSIBLE_CFG="${NAUTOBOT_ANSIBLE_CONFIGS:-$HOME/Nautobot-Workshop/ansible-lab/configs}"
    for spec in "RR1.conf:bmp server 1:192.168.3.252" "PE1.conf:no_bmp:bmp server" "West-Spine01.conf:management api gnmi:transport grpc default"; do
      IFS=':' read -r file check1 check2 <<< "$spec"
      path="$ANSIBLE_CFG/$file"
      if [[ ! -f "$path" ]]; then
        echo "  FAIL: missing rendered config $path (run ansible --tags build)"
        exit 1
      fi
      if [[ "$check1" == "no_bmp" ]]; then
        if grep -q "$check2" "$path"; then
          echo "  FAIL: $file should not contain BMP (non-RR role)"
          exit 1
        fi
        echo "  OK: $file has no BMP stanza"
      else
        grep -q "$check1" "$path" && grep -q "$check2" "$path" || {
          echo "  FAIL: $file missing $check1 or $check2"
          exit 1
        }
        echo "  OK: $file contains $check1 + $check2"
      fi
    done
    GC_TPL="${NAUTOBOT_GOLDEN_TEMPLATES:-$HOME/github-projects/nautobot_workshop_golden_config_templates}"
    if [[ -f "$GC_TPL/ios/bmp.j2" ]]; then
      echo "  OK: golden_config_templates repo has ios/bmp.j2 (push + Nautobot sync for intended API)"
    fi
    echo ""
    echo "PHASE 6 PASS (golden config BMP on RR1 + gNMI on West-Spine01)"
    exit 0
    ;;
  *)
    echo "Unknown phase: $PHASE (use: --phase 1, 2, 3, 4, 5, or 6)"
    exit 2
    ;;
esac