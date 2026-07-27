#!/usr/bin/env bash
# Apply Convergence device telemetry (Phase 10 — T128).
# Renders inventory → snmp modules + managed Prometheus section → compose profile → reload.
#
# Usage:
#   ./scripts/convergence-telemetry-apply.sh
#   ./scripts/convergence-telemetry-apply.sh --config config/convergence.example.yaml
#   ./scripts/convergence-telemetry-apply.sh --dry-run
#   SNMP_COMMUNITY=secret ./scripts/convergence-telemetry-apply.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY="${REPO_ROOT}/deploy/convergence"
RENDER="${REPO_ROOT}/scripts/render-convergence-telemetry.py"
PROM_YML="${DEPLOY}/prometheus/prometheus.yml"
SNMP_YML="${DEPLOY}/adapters/device-snmp/snmp.yml"
CHECKLIST_DIR="${DEPLOY}/generated"
CHECKLIST_OUT="${CHECKLIST_DIR}/device-config-checklist.md"
COMPOSE_FILE="${DEPLOY}/docker-compose.yml"
COMPOSE_FULL="${DEPLOY}/docker-compose.full.yml"

CONFIG=""
DRY_RUN=0
SKIP_COMPOSE=0
SKIP_RELOAD=0
TARGETS=""

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \?//'
  echo "Options:"
  echo "  --config PATH     convergence.yaml (default: search order below)"
  echo "  --targets PATH    targets YAML instead of full config"
  echo "  --dry-run         render only; do not write live paths or reload"
  echo "  --skip-compose    do not docker compose up device-snmp"
  echo "  --skip-reload     do not SIGHUP/reload prometheus"
  echo "  -h, --help        this help"
  echo
  echo "Config search order:"
  echo "  \$CONVERGENCE_CONFIG, ~/.openclaw/convergence.yaml,"
  echo "  ${REPO_ROOT}/config/convergence.yaml, config/convergence.example.yaml"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="${2:-}"; shift 2 ;;
    --targets) TARGETS="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --skip-compose) SKIP_COMPOSE=1; shift ;;
    --skip-reload) SKIP_RELOAD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

resolve_config() {
  if [[ -n "$CONFIG" ]]; then
    echo "$CONFIG"
    return
  fi
  if [[ -n "${CONVERGENCE_CONFIG:-}" && -f "${CONVERGENCE_CONFIG}" ]]; then
    echo "$CONVERGENCE_CONFIG"
    return
  fi
  for c in \
    "${HOME}/.openclaw/convergence.yaml" \
    "${REPO_ROOT}/config/convergence.yaml" \
    "${REPO_ROOT}/config/convergence.example.yaml"
  do
    if [[ -f "$c" ]]; then
      echo "$c"
      return
    fi
  done
  return 1
}

if [[ ! -f "$RENDER" ]]; then
  echo "Missing renderer: $RENDER" >&2
  exit 1
fi

# Load deploy/.env for SNMP_COMMUNITY if present
if [[ -f "${DEPLOY}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${DEPLOY}/.env"
  set +a
fi
export SNMP_COMMUNITY="${SNMP_COMMUNITY:-public}"

RENDER_ARGS=(python3 "$RENDER")
if [[ -n "$TARGETS" ]]; then
  RENDER_ARGS+=(--targets "$TARGETS")
else
  CFG="$(resolve_config)" || {
    echo "No convergence.yaml found. Pass --config or create config/convergence.yaml" >&2
    exit 1
  }
  RENDER_ARGS+=(--config "$CFG")
  echo "Using config: $CFG"
fi

RENDER_ARGS+=(--community "$SNMP_COMMUNITY")
RENDER_ARGS+=(--modules-dir "${DEPLOY}/adapters/device-snmp/modules")

if [[ "$DRY_RUN" -eq 1 ]]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  echo "== dry-run render → $TMP =="
  "${RENDER_ARGS[@]}" \
    --out-scrape "${TMP}/scrape.yml" \
    --out-snmp "${TMP}/snmp.yml" \
    --out-checklist "${TMP}/checklist.md"
  echo "--- scrape (head) ---"
  head -40 "${TMP}/scrape.yml"
  echo "--- snmp modules keys ---"
  python3 -c "import yaml; d=yaml.safe_load(open('${TMP}/snmp.yml')); print(list((d.get('modules') or {}).keys()))"
  echo "dry-run OK (no live writes)"
  exit 0
fi

mkdir -p "$CHECKLIST_DIR"

echo "== render + inject =="
"${RENDER_ARGS[@]}" \
  --out-snmp "$SNMP_YML" \
  --out-checklist "$CHECKLIST_OUT" \
  --inject-prometheus "$PROM_YML"

echo "  snmp.yml:     $SNMP_YML"
echo "  prometheus:   $PROM_YML (managed section)"
echo "  checklist:    $CHECKLIST_OUT"

if [[ "$SKIP_COMPOSE" -eq 0 ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found — skip compose (configs written)" >&2
  else
    echo "== docker compose profile device-snmp =="
    cd "$DEPLOY"
    COMPOSE_FILES=(-f docker-compose.yml)
    # Prefer full compose when present so grafana stays up with same project
    if [[ -f docker-compose.full.yml ]]; then
      # only add if already using full stack services; harmless if profiles unused
      :
    fi
    # Prefer full compose when that project is already up (grafana/loki/etc.)
    if docker compose -f docker-compose.yml -f docker-compose.full.yml ps --status running 2>/dev/null | grep -q prometheus; then
      DC=(docker compose -f docker-compose.yml -f docker-compose.full.yml --env-file .env --profile device-snmp)
    else
      DC=(docker compose -f docker-compose.yml --env-file .env --profile device-snmp)
    fi
    "${DC[@]}" up -d snmp-device-exporter
    # snmp_exporter reads config at start — always restart after snmp.yml write
    "${DC[@]}" restart snmp-device-exporter
  fi
else
  echo "skip-compose: left containers untouched"
fi

if [[ "$SKIP_RELOAD" -eq 0 ]]; then
  echo "== prometheus reload =="
  reloaded=0
  if command -v docker >/dev/null 2>&1; then
    # Prefer kill -s SIGHUP on prometheus container
    if docker compose -f "${DEPLOY}/docker-compose.yml" --env-file "${DEPLOY}/.env" exec -T prometheus \
      wget -qO- --post-data='' http://127.0.0.1:9090/-/reload 2>/dev/null; then
      reloaded=1
    elif curl -fsS -X POST http://127.0.0.1:9090/-/reload >/dev/null 2>&1; then
      reloaded=1
    elif docker kill -s SIGHUP "$(docker compose -f "${DEPLOY}/docker-compose.yml" ps -q prometheus 2>/dev/null)" 2>/dev/null; then
      reloaded=1
    fi
  elif curl -fsS -X POST http://127.0.0.1:9090/-/reload >/dev/null 2>&1; then
    reloaded=1
  fi
  if [[ "$reloaded" -eq 1 ]]; then
    echo "  prometheus reloaded"
  else
    echo "  (warn) could not reload prometheus — restart the container manually" >&2
  fi
else
  echo "skip-reload: prometheus not reloaded"
fi

echo
echo "Apply complete."
echo "  Checklist: $CHECKLIST_OUT"
echo "  Smoke:     ${REPO_ROOT}/deploy/convergence/smoke-device-snmp.sh"
echo "  Grafana:   http://127.0.0.1:3300 (folder Convergence)"
echo "  Named IF:  query interface_status on :9090"
exit 0
