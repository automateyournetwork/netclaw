#!/usr/bin/env bash
# R10 (spec 198) OWNER-GO STEP: place the Anthropic key on a Border VM for the gateway ONLY, over the driver's ssh channel.
#   PHASE=<phase> [PROVIDER=azure] ha-r10-place-provider-key.sh <code> <env-file-with-ANTHROPIC_API_KEY>
# The key is read in-process, streamed on stdin into a root-owned 0600 file, never printed, never in argv or logs.
# Removal at teardown: ha-r10-remove-provider-key.sh (and phase `down` deletes the VM anyway). Use a dedicated spend-capped key.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
PHASE="${PHASE:?PHASE}"; PROVIDER="${PROVIDER:-azure}"
code="${1:?node code}"; envfile="${2:?env file}"
[ -r "$envfile" ] || { echo "cannot read $envfile" >&2; exit 2; }
python3 - "$envfile" <<'PY' | bash "$here/scripts/ha-cloud.sh" "$PROVIDER" ssh "$PHASE" "$code" \
  'sudo install -d -m 0750 /etc/nc182 && sudo sh -c "umask 077; cat > /etc/nc182/provider.env" && sudo chown root:root /etc/nc182/provider.env && sudo chmod 0600 /etc/nc182/provider.env && sudo test -s /etc/nc182/provider.env && echo placed'
import re, sys
value = None
for line in open(sys.argv[1], encoding='utf-8'):
    m = re.match(r'^\s*(?:export\s+)?ANTHROPIC_API_KEY\s*=\s*(.+?)\s*$', line)
    if m:
        value = m.group(1).strip('"\'')
if not value or re.search(r'[\s\x00-\x1f]', value):
    sys.exit('no usable ANTHROPIC_API_KEY in the env file')
sys.stdout.write('ANTHROPIC_API_KEY=' + value + '\n')
PY
