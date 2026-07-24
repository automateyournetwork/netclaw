#!/usr/bin/env bash
# Smoke-test NetClaw Home Docker stack (067 Phase 3 / T033).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env}"
COMPOSE_ARGS=(-f "$ROOT/docker-compose.yml")
if [[ -f "$ENV_FILE" ]]; then
  COMPOSE_ARGS+=(--env-file "$ENV_FILE")
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

dc() { docker compose "${COMPOSE_ARGS[@]}" "$@"; }

HOME_API_PORT="${HOME_API_HOST_PORT:-3080}"
PROM_PORT="${PROMETHEUS_HOST_PORT:-9090}"
AM_PORT="${ALERTMANAGER_HOST_PORT:-9093}"

API_KEY="dev-home-api-key-change-me"
if [[ -n "${API_KEYS:-}" ]]; then
  API_KEY="$(API_KEYS="$API_KEYS" python3 -c 'import json,os; k=json.loads(os.environ["API_KEYS"]); print(k[0]["key"] if k else "")' 2>/dev/null || echo "$API_KEY")"
fi

PASS=0
FAIL=0
ok() { echo "  OK  $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL $1"; FAIL=$((FAIL + 1)); }

echo "== NetClaw Home Docker smoke =="
echo "Root: $ROOT"

"$ROOT/render-config.sh"

echo "-- compose config"
if dc config --quiet; then ok "compose config validates"; else bad "compose config validates"; fi

echo "-- bring up core services"
dc up -d --build postgres prometheus alertmanager blackbox home-api

wait_http() {
  local url="$1" n=0
  while (( n < 45 )); do
    if curl -fsS -o /dev/null --max-time 3 "$url" 2>/dev/null; then
      return 0
    fi
    sleep 2
    n=$((n + 1))
  done
  return 1
}

echo "-- containers"
for svc in postgres prometheus alertmanager blackbox home-api; do
  if [[ -n "$(dc ps -q "$svc" 2>/dev/null)" ]]; then
    ok "$svc container present"
  else
    bad "$svc container present"
  fi
done

echo "-- HTTP"
if wait_http "http://127.0.0.1:${HOME_API_PORT}/healthz"; then
  ok "home-api /healthz"
else
  bad "home-api /healthz"
  dc logs --tail=40 home-api || true
fi
if wait_http "http://127.0.0.1:${PROM_PORT}/-/ready"; then ok "prometheus ready"; else bad "prometheus ready"; fi
if wait_http "http://127.0.0.1:${AM_PORT}/-/ready"; then ok "alertmanager ready"; else bad "alertmanager ready"; fi

echo "-- authenticated API"
code=$(curl -sS -o /tmp/home-api-health.json -w '%{http_code}' \
  -H "Authorization: Bearer ${API_KEY}" \
  "http://127.0.0.1:${HOME_API_PORT}/api/health?site=home" || echo "000")
if [[ "$code" == "200" ]]; then
  ok "GET /api/health?site=home"
  head -c 220 /tmp/home-api-health.json; echo
else
  echo "  status=$code body=$(head -c 160 /tmp/home-api-health.json 2>/dev/null || true)"
  bad "GET /api/health?site=home (got $code)"
fi

echo "-- prometheus targets"
if curl -fsS "http://127.0.0.1:${PROM_PORT}/api/v1/targets" -o /tmp/prom-targets.json 2>/dev/null; then
  count=$(python3 -c 'import json; d=json.load(open("/tmp/prom-targets.json")); print(len(d.get("data",{}).get("activeTargets",[])))')
  echo "  active targets: $count"
  if [[ "${count:-0}" -ge 1 ]]; then ok "prometheus has targets"; else bad "prometheus has targets"; fi
else
  bad "prometheus targets API"
fi

echo "-- alertmanager webhook"
if grep -q "webhook_configs" "$ROOT/alertmanager/alertmanager.yml" \
  && grep -qE "8099|webhook|ALERT" "$ROOT/alertmanager/alertmanager.yml"; then
  ok "alertmanager webhook configured"
else
  bad "alertmanager webhook configured"
fi

echo
echo "Summary: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
  echo "Tips: dc logs --tail=80 home-api"
  exit 1
fi
echo "OK — HUD env:"
echo "  HOME_API_URL=http://127.0.0.1:${HOME_API_PORT}"
echo "  HOME_API_TOKEN=${API_KEY}"
exit 0
