#!/usr/bin/env bash
# Show / seed Convergence investigation policy (067 Phase 9).
# Usage:
#   ./scripts/netclaw-investigation-policy.sh show
#   ./scripts/netclaw-investigation-policy.sh seed-observe-only
#   ./scripts/netclaw-investigation-policy.sh thin-agent   # show T106 alert agent profile
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLICY="${INVESTIGATION_POLICY_PATH:-$HOME/.openclaw/investigation-policy.yaml}"
EXAMPLE="$ROOT/deploy/convergence/config/investigation-policy.example.yaml"
RECEIVER="${INVESTIGATION_POLICY_STATUS_URL:-http://127.0.0.1:8099/policy/status}"
THIN="$ROOT/scripts/netclaw-alert-agent-profile.sh"

cmd="${1:-show}"

case "$cmd" in
  show)
    echo "Policy file: $POLICY"
    if [[ -f "$POLICY" ]]; then
      echo "---"
      cat "$POLICY"
    else
      echo "(missing — alert-receiver fail-safes to T0)"
    fi
    echo "---"
    if curl -sf -m 3 "$RECEIVER" >/dev/null 2>&1; then
      curl -sS -m 3 "$RECEIVER" | python3 -m json.tool 2>/dev/null || curl -sS -m 3 "$RECEIVER"
    else
      echo "alert-receiver /policy/status not reachable at $RECEIVER"
    fi
    if [[ -x "$THIN" ]]; then
      echo "--- thin T2 agent ---"
      "$THIN" show 2>/dev/null || true
    fi
    ;;
  seed-observe-only|seed)
    mkdir -p "$(dirname "$POLICY")"
    if [[ ! -f "$EXAMPLE" ]]; then
      echo "Example not found: $EXAMPLE" >&2
      exit 1
    fi
    cp "$EXAMPLE" "$POLICY"
    echo "Seeded $POLICY (default_tier: T0, empty allow_t2)"
    echo "Reload is automatic within ~30s (cache TTL) or restart netclaw-alert-receiver"
    echo "Tip: also run $THIN apply so T2 hooks use the thin agent profile"
    ;;
  thin-agent|alert-agent)
    exec "$THIN" "${2:-show}"
    ;;
  *)
    echo "Usage: $0 {show|seed-observe-only|thin-agent}" >&2
    exit 2
    ;;
esac
