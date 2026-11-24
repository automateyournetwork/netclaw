#!/usr/bin/env bash
# Spec 198 phase runner: ha-r10-phase.sh <up|status|down> <phase> [codes...] [--provider azure|gcp] [--dry-run]
# up   : refuses unless R10_GO=<phase> (the owner's explicit go) or --dry-run; each VM is ledger-gated ($15 pause, $25 ceiling).
# down : deletes the whole phase, stops its ledger entries, verifies nothing tagged remains.
# gcp: export GCP_VM_PREFIX=nc198-<phase> and R10_RUN_ID (labels + watchdog scope); `up` creates the nc198-<phase>-* firewall rules.
# phases: p2-single (nne1) | p3-ha (nne1 ew1 ase1) | p4-mesh (azure nne1 + gcp gcpm; run once per provider)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
verb="${1:?up|status|down}"; phase="${2:?phase}"; shift 2
provider=azure; dry=""; codes=()
while [ $# -gt 0 ]; do case "$1" in --provider) provider="$2"; shift 2;; --dry-run) dry="--dry-run"; shift;; *) codes+=("$1"); shift;; esac; done
cloud() { bash "$here/scripts/ha-cloud.sh" "$provider" "$@" $dry; }
ledger() { if [ -n "$dry" ]; then echo "ledger $*"; else python3 "$here/labs/ha/r10_ledger.py" "$@"; fi; }
RATE="${R10_RATE_USD_PER_H:-0.13}"   # reviewed D2als_v7 + static IP/SSD allowance; live retail price still required
SIZE="${R10_SIZE:-}"; [ -z "$SIZE" ] && { [ "$provider" = gcp ] && SIZE=e2-standard-2 || SIZE=Standard_B2s; }
case "$verb" in
  up)
    [ -n "$dry" ] || [ "${R10_GO:-}" = "$phase" ] || { echo "refused: owner go required (export R10_GO=$phase)" >&2; exit 4; }
    [ "${#codes[@]}" -gt 0 ] || { echo "no node codes" >&2; exit 2; }
    [ "$provider" = gcp ] && cloud firewall "$phase"
    for c in "${codes[@]}"; do
      ledger start "$phase" "$provider-$c" "$RATE" --hours "${R10_MAX_HOURS:-8}" || { echo "ledger stopped the phase before $c" >&2; exit 3; }
      cloud up "$phase" "$c" - "$SIZE"
    done
    [ "$provider" = azure ] && [ "${#codes[@]}" -gt 1 ] && cloud peer "$phase" "${codes[@]}"
    echo "phase $phase up: ${codes[*]}" ;;
  status) ledger status; cloud list "$phase" ;;
  down)
    cloud down "$phase"
    for c in "${codes[@]:-}"; do [ -n "$c" ] && ledger stop "$phase" "$provider-$c"; done
    if [ -z "$dry" ]; then echo "remaining tagged resources:"; cloud list "$phase"; fi
    echo "phase $phase down" ;;
  *) echo "unknown verb $verb" >&2; exit 2 ;;
esac
