#!/usr/bin/env bash
# Smoke-test NetClaw Convergence K3s kustomize (067 Phase 4 / T042).
# Always validates kustomize build. Live cluster checks when kubectl works.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OVERLAY="${OVERLAY:-$ROOT/overlays/greenfield}"
NS="${NS:-netclaw-convergence}"
APPLY=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--apply]"
      echo "  Validates kustomize build; if cluster reachable, checks pods/HTTP."
      echo "  --apply  also kubectl apply -k overlays/greenfield (secrets must exist)"
      exit 0
      ;;
  esac
done

PASS=0
FAIL=0
ok() { echo "  OK  $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL $1"; FAIL=$((FAIL + 1)); }

echo "== NetClaw Convergence K3s smoke =="
echo "Root: $ROOT"
echo "Overlay: $OVERLAY"

echo "-- kustomize build"
if out=$(kubectl kustomize "$OVERLAY" 2>&1); then
  kinds=$(printf '%s\n' "$out" | awk '/^kind:/{print $2}' | sort | uniq -c | tr '\n' ' ')
  echo "  resources: $kinds"
  ok "kustomize build greenfield"
else
  echo "$out"
  bad "kustomize build greenfield"
fi

# Required kinds present
for kind in Namespace StatefulSet Deployment Service ConfigMap; do
  if printf '%s\n' "$out" | grep -q "^kind: ${kind}$"; then
    ok "manifest includes $kind"
  else
    bad "manifest includes $kind"
  fi
done

# Service names match Docker DNS expectations
for svc in postgres prometheus alertmanager blackbox home-api unifi-exporter; do
  if printf '%s\n' "$out" | grep -q "name: ${svc}$"; then
    ok "resource name $svc present"
  else
    bad "resource name $svc present"
  fi
done

# Secret example exists (not applied by kustomize)
if [[ -f "$ROOT/secret.example.yaml" ]]; then
  ok "secret.example.yaml present"
else
  bad "secret.example.yaml present"
fi

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo
  echo "No live cluster (or kubectl misconfigured) — offline checks only."
  echo "Summary: $PASS passed, $FAIL failed"
  if (( FAIL > 0 )); then exit 1; fi
  echo "OK — offline kustomize smoke"
  exit 0
fi

echo "-- live cluster"
if (( APPLY )); then
  if kubectl get secret home-secrets -n "$NS" >/dev/null 2>&1; then
    kubectl apply -k "$OVERLAY"
    ok "kubectl apply -k greenfield"
  else
    bad "home-secrets must exist before --apply (kubectl apply -f secret.yaml)"
  fi
fi

if ! kubectl get ns "$NS" >/dev/null 2>&1; then
  echo "  Namespace $NS not found — apply stack first (see SMOKE.md)"
  echo "Summary: $PASS passed, $FAIL failed (partial live)"
  if (( FAIL > 0 )); then exit 1; fi
  exit 0
fi

wait_ready() {
  local kind="$1" name="$2" timeout="${3:-120}"
  if kubectl -n "$NS" rollout status "$kind/$name" --timeout="${timeout}s" >/dev/null 2>&1; then
    ok "$kind/$name ready"
  else
    bad "$kind/$name ready"
  fi
}

wait_ready deploy home-api 180
wait_ready deploy alertmanager 120
wait_ready deploy blackbox 120
wait_ready sts postgres 180
wait_ready sts prometheus 180
# unifi-exporter may run without key
if kubectl -n "$NS" get deploy unifi-exporter >/dev/null 2>&1; then
  wait_ready deploy unifi-exporter 120 || true
fi

# Port-forward health checks
cleanup_pf() {
  [[ -n "${PF_PIDS:-}" ]] && kill $PF_PIDS 2>/dev/null || true
}
trap cleanup_pf EXIT

kubectl -n "$NS" port-forward svc/home-api 13080:3000 >/dev/null 2>&1 &
PF_PIDS="$!"
kubectl -n "$NS" port-forward svc/prometheus 19090:9090 >/dev/null 2>&1 &
PF_PIDS="$PF_PIDS $!"
kubectl -n "$NS" port-forward svc/alertmanager 19093:9093 >/dev/null 2>&1 &
PF_PIDS="$PF_PIDS $!"
sleep 2

wait_http() {
  local url="$1" n=0
  while (( n < 30 )); do
    if curl -fsS -o /dev/null --max-time 3 "$url" 2>/dev/null; then return 0; fi
    sleep 2
    n=$((n + 1))
  done
  return 1
}

if wait_http "http://127.0.0.1:13080/healthz"; then ok "home-api /healthz"; else bad "home-api /healthz"; fi
if wait_http "http://127.0.0.1:19090/-/ready"; then ok "prometheus ready"; else bad "prometheus ready"; fi
if wait_http "http://127.0.0.1:19093/-/ready"; then ok "alertmanager ready"; else bad "alertmanager ready"; fi

API_KEY="dev-home-api-key-change-me"
if kubectl -n "$NS" get secret home-secrets -o jsonpath='{.data.API_KEYS}' 2>/dev/null | base64 -d >/tmp/home-api-keys.json 2>/dev/null; then
  API_KEY="$(python3 -c 'import json; k=json.load(open("/tmp/home-api-keys.json")); print(k[0]["key"] if k else "")' 2>/dev/null || echo "$API_KEY")"
fi

code=$(curl -sS -o /tmp/home-api-health.json -w '%{http_code}' \
  -H "Authorization: Bearer ${API_KEY}" \
  "http://127.0.0.1:13080/api/health?site=home" || echo "000")
if [[ "$code" == "200" ]]; then
  ok "GET /api/health?site=home"
else
  echo "  status=$code body=$(head -c 160 /tmp/home-api-health.json 2>/dev/null || true)"
  bad "GET /api/health?site=home (got $code)"
fi

echo
echo "Summary: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
  echo "Tips: kubectl -n $NS get pods; kubectl -n $NS logs deploy/convergence-api --tail=40"
  exit 1
fi
echo "OK — HUD env:"
echo "  HOME_API_URL=http://127.0.0.1:3080   # or NodePort :30080 / port-forward"
echo "  HOME_API_TOKEN=${API_KEY}"
exit 0
