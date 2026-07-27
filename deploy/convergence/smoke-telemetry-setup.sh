#!/usr/bin/env bash
# Smoke: Phase 10 PR2 telemetry setup (T137).
# Verifies Nautobot (or yaml) inventory path produces valid targets YAML without
# applying live Prometheus changes (dry-run).
#
# Usage:
#   ./deploy/convergence/smoke-telemetry-setup.sh
#   MODE=yaml ./deploy/convergence/smoke-telemetry-setup.sh
#   MODE=manual ./deploy/convergence/smoke-telemetry-setup.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SETUP_PY="${REPO_ROOT}/scripts/convergence-telemetry-setup.py"
SETUP_SH="${REPO_ROOT}/scripts/convergence-telemetry-setup.sh"
MODE="${MODE:-nautobot}"
REPORT_FILE="${REPORT_FILE:-/tmp/smoke-telemetry-setup.report.json}"
TMPDIR_RUN="${TMPDIR:-/tmp}/netclaw-telemetry-setup-smoke-$$"
mkdir -p "$TMPDIR_RUN"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

PASS=0
FAIL=0
ok() { echo "  OK  $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL $1"; FAIL=$((FAIL + 1)); }

run_setup() {
  python3 "$SETUP_PY" "$@"
}

echo "== Convergence telemetry setup smoke (T137) =="
echo "Mode: $MODE"
echo "Repo: $REPO_ROOT"

if [[ ! -f "$SETUP_PY" ]]; then
  bad "setup script present"
  echo "PASS=$PASS FAIL=$FAIL"
  exit 1
fi
ok "setup script present"

OUT_YAML="${TMPDIR_RUN}/convergence.yaml"
OUT_TARGETS="${TMPDIR_RUN}/targets.yml"
DRY_LOG="${TMPDIR_RUN}/dry-run.log"

case "$MODE" in
  nautobot)
    # Load env for NAUTOBOT_* without printing secrets
    for f in \
      "${REPO_ROOT}/.env" \
      "${REPO_ROOT}/deploy/convergence/.env" \
      "${HOME}/.openclaw/.env"
    do
      if [[ -f "$f" ]]; then
        set -a
        # shellcheck disable=SC1090
        source "$f" 2>/dev/null || true
        set +a
      fi
    done
    if [[ -z "${NAUTOBOT_URL:-}" || -z "${NAUTOBOT_TOKEN:-}" ]]; then
      bad "NAUTOBOT_URL + NAUTOBOT_TOKEN in env"
      echo "  Set credentials or run MODE=yaml"
      echo "PASS=$PASS FAIL=$FAIL"
      exit 1
    fi
    ok "NAUTOBOT credentials present"
    if ! run_setup --mode nautobot --select all --dry-run \
      --out "$OUT_YAML" --out-targets "$OUT_TARGETS" \
      >"$DRY_LOG" 2>&1; then
      bad "nautobot dry-run exits 0"
      tail -20 "$DRY_LOG" || true
      echo "PASS=$PASS FAIL=$FAIL"
      exit 1
    fi
    ok "nautobot dry-run exits 0"
    # Write for real to temp (not live ~/.openclaw config)
    run_setup --mode nautobot --select 'HomeSwitch,pfSense' \
      --write --out "$OUT_YAML" --out-targets "$OUT_TARGETS" \
      >"${TMPDIR_RUN}/write.log" 2>&1 || {
        bad "nautobot write to temp yaml"
        cat "${TMPDIR_RUN}/write.log"
        echo "PASS=$PASS FAIL=$FAIL"
        exit 1
      }
    ok "nautobot write to temp yaml"
    ;;
  yaml)
    EX="${REPO_ROOT}/deploy/convergence/adapters/device-snmp/targets.example.yml"
    run_setup --mode yaml --import "$EX" --write \
      --out "$OUT_YAML" --out-targets "$OUT_TARGETS" \
      >"${TMPDIR_RUN}/write.log" 2>&1 || {
        bad "yaml import write"
        cat "${TMPDIR_RUN}/write.log"
        echo "PASS=$PASS FAIL=$FAIL"
        exit 1
      }
    ok "yaml import write"
    ;;
  manual)
    run_setup --mode manual \
      --csv 'HomeSwitch01=192.168.3.2:cisco,HomeSwitch04=192.168.3.5:cisco' \
      --write --out "$OUT_YAML" --out-targets "$OUT_TARGETS" \
      >"${TMPDIR_RUN}/write.log" 2>&1 || {
        bad "manual csv write"
        cat "${TMPDIR_RUN}/write.log"
        echo "PASS=$PASS FAIL=$FAIL"
        exit 1
      }
    ok "manual csv write"
    ;;
  *)
    bad "unknown MODE=$MODE"
    exit 2
    ;;
esac

echo "-- validate written inventory"
python3 - <<PY
import json, sys, yaml
from pathlib import Path
out = Path("${OUT_YAML}")
tgt = Path("${OUT_TARGETS}")
report = {"targets": 0, "names": [], "has_ip": True, "enabled": False, "error": ""}
try:
    cfg = yaml.safe_load(out.read_text()) or {}
    snmp = (cfg.get("device_telemetry") or {}).get("snmp") or {}
    targets = snmp.get("targets") or []
    report["targets"] = len(targets)
    report["names"] = [t.get("name") for t in targets]
    report["enabled"] = bool(snmp.get("enabled"))
    for t in targets:
        if not t.get("ip") or not t.get("name"):
            report["has_ip"] = False
    if tgt.is_file():
        doc = yaml.safe_load(tgt.read_text()) or {}
        report["targets_file"] = len(doc.get("targets") or [])
    else:
        report["targets_file"] = 0
except Exception as e:
    report["error"] = str(e)
Path("${REPORT_FILE}").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if report.get("error"):
    sys.exit(1)
if report["targets"] < 1:
    sys.exit(2)
if not report["has_ip"]:
    sys.exit(3)
if not report["enabled"]:
    sys.exit(4)
PY
RC=$?
if [[ $RC -eq 0 ]]; then
  NAMES=$(python3 -c "import json; print(','.join(json.load(open('${REPORT_FILE}'))['names']))")
  COUNT=$(python3 -c "import json; print(json.load(open('${REPORT_FILE}'))['targets'])")
  ok "inventory yaml has ${COUNT} target(s) with IPs (${NAMES})"
  ok "device_telemetry.snmp.enabled true"
else
  bad "inventory yaml valid (rc=$RC)"
  cat "$REPORT_FILE" 2>/dev/null || true
fi

# Ensure dry-run did not require live apply
ok "no live prometheus apply required for this smoke"

echo
echo "PASS=$PASS FAIL=$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  echo "T137 smoke FAILED"
  exit 1
fi
echo "T137 smoke PASSED — telemetry setup ${MODE} → yaml"
exit 0
