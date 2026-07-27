#!/usr/bin/env bash
# Smoke: Phase 8 device SNMP (067 T088).
# Verifies Prometheus has healthy device_snmp scrapes and IF-MIB series
# labeled device_name (lab switches or configured mock targets).
#
# Usage:
#   ./deploy/convergence/smoke-device-snmp.sh
#   PROM_URL=http://127.0.0.1:9090 MIN_DEVICES=1 ./deploy/convergence/smoke-device-snmp.sh
#
set -euo pipefail

PROM_URL="${PROM_URL:-http://127.0.0.1:9090}"
SNMP_EXPORTER_URL="${SNMP_EXPORTER_URL:-http://127.0.0.1:9117}"
MIN_DEVICES="${MIN_DEVICES:-1}"
JOB="${DEVICE_SNMP_JOB:-device_snmp}"
REPORT_FILE="${REPORT_FILE:-/tmp/smoke-device-snmp.report.json}"

PASS=0
FAIL=0
ok() { echo "  OK  $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL $1"; FAIL=$((FAIL + 1)); }

echo "== Convergence device_snmp smoke (T088) =="
echo "Prometheus: $PROM_URL"
echo "SNMP exporter: $SNMP_EXPORTER_URL"
echo "Job: $JOB  min devices: $MIN_DEVICES"

echo "-- prometheus ready"
if curl -fsS -m 5 -o /dev/null "${PROM_URL}/-/ready" 2>/dev/null \
  || curl -fsS -m 5 -o /dev/null "${PROM_URL}/api/v1/status/config" 2>/dev/null; then
  ok "prometheus reachable"
else
  bad "prometheus reachable at $PROM_URL"
  echo "Bring up: cd deploy/convergence && docker compose --profile device-snmp up -d"
  echo "PASS=$PASS FAIL=$FAIL"
  exit 1
fi

echo "-- snmp exporter (optional)"
if curl -fsS -m 5 -o /dev/null "${SNMP_EXPORTER_URL}/metrics" 2>/dev/null \
  || curl -fsS -m 5 -o /dev/null "${SNMP_EXPORTER_URL}/" 2>/dev/null; then
  ok "snmp exporter HTTP responds"
else
  echo "  (warn) snmp exporter not on $SNMP_EXPORTER_URL — continue if Prom still has series"
fi

echo "-- device_snmp scrape targets + ifOperStatus"
PROM_URL="$PROM_URL" JOB="$JOB" REPORT_FILE="$REPORT_FILE" python3 <<'PY'
import json, os, urllib.parse, urllib.request

prom = os.environ["PROM_URL"].rstrip("/")
job = os.environ["JOB"]
path = os.environ["REPORT_FILE"]

def get(url_path, params=None):
    url = prom + url_path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)

out = {
    "total": 0,
    "up": 0,
    "t_names": [],
    "devices": 0,
    "device_list": [],
    "sample": "",
    "agent_series": 0,
    "target_lines": [],
    "error": "",
}

try:
    d = get("/api/v1/targets")
    active = (d.get("data") or {}).get("activeTargets") or []
except Exception as e:
    out["error"] = f"targets: {e}"
    active = []

ours = []
for t in active:
    lab = t.get("labels") or {}
    j = lab.get("job") or ""
    pool = t.get("scrapePool") or ""
    if j == job or pool == job or job in j or job in pool:
        ours.append(t)

up = [t for t in ours if (t.get("health") or "").lower() == "up"]
t_names = sorted(
    {
        (t.get("labels") or {}).get("device_name")
        for t in up
        if (t.get("labels") or {}).get("device_name")
    }
)
out["total"] = len(ours)
out["up"] = len(up)
out["t_names"] = t_names
for t in ours[:8]:
    lab = t.get("labels") or {}
    err = (t.get("lastError") or "")[:50]
    out["target_lines"].append(
        f"health={t.get('health')} device_name={lab.get('device_name')} "
        f"instance={lab.get('instance')} err={err}"
    )

try:
    q = f'count by (device_name) (ifOperStatus{{job="{job}"}})'
    d = get("/api/v1/query", {"query": q})
    res = (d.get("data") or {}).get("result") or []
    s_names = sorted(
        {
            (r.get("metric") or {}).get("device_name")
            for r in res
            if (r.get("metric") or {}).get("device_name")
        }
    )
    out["devices"] = len(s_names)
    out["device_list"] = s_names
except Exception as e:
    out["error"] = (out["error"] + f" query: {e}").strip()

try:
    d = get("/api/v1/query", {"query": f'ifOperStatus{{job="{job}"}}'})
    res = (d.get("data") or {}).get("result") or []
    if res:
        m = res[0].get("metric") or {}
        val = res[0].get("value", [None, None])[1]
        out["sample"] = (
            f"device_name={m.get('device_name')} ifIndex={m.get('ifIndex')} "
            f"ifDescr={(m.get('ifDescr') or '')[:40]} value={val}"
        )
except Exception:
    pass

try:
    d = get("/api/v1/query", {"query": "count(netclaw_model_input_tokens_total)"})
    res = (d.get("data") or {}).get("result") or []
    out["agent_series"] = int(float(res[0]["value"][1])) if res else 0
except Exception:
    pass

with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f)

if out.get("error"):
    print("  (warn)", out["error"])
print(
    f"  targets total={out['total']} up={out['up']} "
    f"names={out['t_names'] or ['(none)']}"
)
for line in out["target_lines"]:
    print("   ", line)
print(
    f"  ifOperStatus devices: {out['devices']} "
    f"({out['device_list'] or ['(none)']})"
)
if out.get("sample"):
    print("  sample:", out["sample"])
PY

TOTAL=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['total'])")
UP=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['up'])")
DEVICES=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['devices'])")
AGENT_SERIES=$(python3 -c "import json; print(json.load(open('$REPORT_FILE')).get('agent_series',0))")

if [[ "${TOTAL}" -ge 1 ]]; then
  ok "prometheus has ${JOB} targets"
else
  bad "prometheus has ${JOB} targets (enable profile device-snmp + targets in prometheus.yml)"
fi
if [[ "${UP}" -ge 1 ]]; then
  ok "at least one ${JOB} target health=up"
else
  bad "at least one ${JOB} target health=up"
fi
if [[ "${DEVICES}" -ge "${MIN_DEVICES}" ]]; then
  ok "ifOperStatus has device_name for >=${MIN_DEVICES} device(s)"
else
  bad "ifOperStatus has device_name for >=${MIN_DEVICES} device(s) (got ${DEVICES})"
fi

echo "-- optional agent metrics (Phase 8 US-DT3, non-fatal)"
if [[ "${AGENT_SERIES}" -gt 0 ]]; then
  ok "netclaw_model_* present in Prometheus"
else
  echo "  (skip) netclaw_model_* not in this Prom instance"
fi

echo "-- named interfaces (Phase 10 / T136)"
NAMED_JSON=$(curl -fsS -m 10 -G "${PROM_URL}/api/v1/query" \
  --data-urlencode 'query=count(interface_status{interface_name!=""})' 2>/dev/null || echo "")
NAMED_COUNT=$(python3 -c "
import json,sys
try:
  d=json.loads(sys.argv[1] or '{}')
  r=(d.get('data') or {}).get('result') or []
  print(int(float(r[0]['value'][1])) if r else 0)
except Exception:
  print(0)
" "$NAMED_JSON")
SAMPLE_NAME=$(curl -fsS -m 10 -G "${PROM_URL}/api/v1/query" \
  --data-urlencode 'query=interface_status{interface_name!=""}' 2>/dev/null \
  | python3 -c "
import json,sys
try:
  r=json.load(sys.stdin)['data']['result']
  if r:
    m=r[0]['metric']
    print(m.get('interface_name','')[:48], m.get('device_name',''), sep='|')
  else:
    print('|')
except Exception:
  print('|')
" 2>/dev/null || echo "|")
IF_NAME="${SAMPLE_NAME%%|*}"
IF_DEV="${SAMPLE_NAME##*|}"
if [[ "${NAMED_COUNT}" -ge 1 && -n "${IF_NAME}" ]]; then
  ok "interface_status has named interfaces (count=${NAMED_COUNT}, e.g. ${IF_DEV}:${IF_NAME})"
else
  bad "interface_status has non-empty interface_name (apply templates + recording rules; got count=${NAMED_COUNT})"
fi

echo
echo "PASS=$PASS FAIL=$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  echo "device_snmp smoke FAILED"
  exit 1
fi
echo "device_snmp smoke PASSED — labeled device_name + named interfaces"
exit 0
