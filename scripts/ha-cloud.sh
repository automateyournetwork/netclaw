#!/usr/bin/env bash
# Spec 198 cloud driver: ha-cloud.sh <gcp|azure> <verb> [--dry-run] [args...]
# Verbs: up ssh scp ip peer stop start down list   (contract: specs/198-azure-multicloud-ha/contracts/cloud-driver.md)
# --dry-run prints every provider command and executes nothing. No verb prints a secret.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
provider="${1:-}"; verb="${2:-}"
[ -n "$provider" ] && [ -n "$verb" ] || { echo "usage: ha-cloud.sh <gcp|azure> <verb> [--dry-run] [args]" >&2; exit 2; }
shift 2
HA_DRY=0; args=()
for a in "$@"; do if [ "$a" = "--dry-run" ]; then HA_DRY=1; else args+=("$a"); fi; done
export HA_DRY
[ -r "$here/ha-cloud-$provider.sh" ] || { echo "unknown provider: $provider" >&2; exit 2; }
# run: print in dry-run, execute otherwise.
run() { if [ "$HA_DRY" = 1 ]; then printf '%q ' "$@"; printf '\n'; else "$@"; fi; }
source "$here/ha-cloud-$provider.sh"
declare -F "cloud_$verb" >/dev/null || { echo "unknown verb: $verb" >&2; exit 2; }
"cloud_$verb" "${args[@]+"${args[@]}"}"
