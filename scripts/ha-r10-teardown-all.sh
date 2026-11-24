#!/usr/bin/env bash
# Retire only fresh run-owned resources after a verified private evidence export.
# AZ_RUN / GC_RUN select existing run manifests. R10_EXPORT points to a JSON
# {"files":{"relative/path":"sha256",...}} verified before deletion.
# AZ_GENERATIONS / GC_GENERATIONS list exact generation suffixes (e.g. "az az2").
# No prefix-wide deletion; no ledger closure or watchdog unload before absence.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"; cd "$here"
: "${R10_EXPORT:?R10_EXPORT (verified evidence hash manifest)}"
[ -n "${AZ_RUN:-}${GC_RUN:-}" ] || { echo 'run identity required' >&2; exit 2; }
for run in ${AZ_RUN:-} ${GC_RUN:-}; do
  [[ "$run" =~ ^r10[a-z0-9-]+-[0-9]{8}$ ]] || { echo 'invalid run identity' >&2; exit 2; }
  root="$HOME/.local/share/netclaw/r10-run-$run"
  R10_RUN_ID="$run" bash scripts/ha-r10-members.sh stop
  python3 labs/ha/r10_cleanup.py "$root/watchdog-manifest.json" --export "$R10_EXPORT" --apply
  if [ "$run" = "${AZ_RUN:-}" ]; then group=az; generations="${AZ_GENERATIONS:-az}"; provider=azure; phase=p3-ha-az; codes='nne1 ew1 ase1'
  else group=gc; generations="${GC_GENERATIONS:-gc}"; provider=gcp; phase=p3-ha-gc; codes='nne1 ew1 ase1 gcpm'; fi
  for generation in $generations; do
    [[ "$generation" =~ ^${group}[0-9]*$ ]] || { echo 'invalid exact generation suffix' >&2; exit 2; }
    [ -f "$root/gen-$generation/summary.json" ] || { echo 'generation summary missing' >&2; exit 2; }
    python3 labs/ha/r10_dns_cleanup.py "$root/gen-$generation"
  done
  for code in $codes; do python3 labs/ha/r10_ledger.py stop "$phase" "$provider-$code"; done
  R10_GCP_PROJECT="${GCP_PROJECT:-netclaw-506315}" bash scripts/ha-r10-run-fini.sh "$run"
done
python3 labs/ha/r10_ledger.py status
