#!/usr/bin/env bash
# R10 (spec 198): shred the provider key on a Border VM. PHASE=<phase> [PROVIDER=azure] ha-r10-remove-provider-key.sh <code>
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
bash "$here/scripts/ha-cloud.sh" "${PROVIDER:-azure}" ssh "${PHASE:?PHASE}" "${1:?node code}" 'sudo shred -u /etc/nc182/provider.env 2>/dev/null; sudo test ! -e /etc/nc182/provider.env && echo key-removed'
