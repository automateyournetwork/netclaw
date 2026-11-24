#!/usr/bin/env bash
# R10 (spec 198) OWNER-GO STEP: create the OpenShell provider that holds the Anthropic key ON THE VM, so the sandbox only
# ever sees an `openshell:resolve:` placeholder. The key streams over ssh stdin into a one-shot environment variable; it is
# never in argv, never written to a file on the VM, never printed.
#   PHASE=<phase> [PROVIDER=azure] ha-r10-openshell-provider.sh <code> <env-file-with-ANTHROPIC_API_KEY> [provider-name]
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
PHASE="${PHASE:?PHASE}"; PROVIDER="${PROVIDER:-azure}"; code="${1:?node code}"; envfile="${2:?env file}"; name="${3:-nc183-anthropic}"
[ -r "$envfile" ] || { echo "cannot read $envfile" >&2; exit 2; }
python3 - "$envfile" <<'PY' | bash "$here/scripts/ha-cloud.sh" "$PROVIDER" ssh "$PHASE" "$code" \
  "export PATH=\$HOME/.local/bin:\$PATH; IFS= read -r K; ANTHROPIC_API_KEY=\"\${K#ANTHROPIC_API_KEY=}\" openshell provider create --name $name --type ${PTYPE:-anthropic} --credential ANTHROPIC_API_KEY 2>&1 | sed -E 's/(sk-ant-)[A-Za-z0-9_-]+/\\1<redacted>/g' | tail -4; unset K"
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
