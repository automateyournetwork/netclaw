#!/usr/bin/env bash
# R09 (spec 182) OWNER STEP: place the Anthropic provider key on a Border VM for the OpenClaw gateway ONLY.
# NOT RUN by the agent. Never prints, logs or stores the key locally: it is read in-process and streamed over the IAP ssh
# channel straight into a root-owned 0600 file that only the gateway unit loads (EnvironmentFile).
#
#   ha-r09-place-provider-key.sh <code> <env-file-containing-ANTHROPIC_API_KEY>
#
# Exposure to state before running: the key then sits on an internet-facing VM, in the gateway process environment
# (readable by that UID and root). The workspace HUD is an unauthenticated open-lab surface, so anyone who can reach
# https://<node>.automateyournetwork.com can spend this key through Chat. Use a dedicated key with a spend cap, and
# restrict firewall 443 to your own IPs while the workspace is enabled.
set -euo pipefail
code="${1:?code nne1|ew1|ase1}"; envfile="${2:?path to an env file that contains ANTHROPIC_API_KEY=...}"
case "$code" in nne1) z=northamerica-northeast1-b;; ew1) z=europe-west1-b;; ase1) z=asia-southeast1-a;; *) exit 2;; esac
[ -r "$envfile" ] || { echo "cannot read $envfile" >&2; exit 2; }
python3 - "$envfile" <<'PY' | gcloud compute ssh "nc182-border-$code" --zone="$z" --project=netclaw-506315 --tunnel-through-iap --quiet \
  --command='sudo install -d -m 0750 /etc/nc182 && sudo sh -c "umask 077; cat > /etc/nc182/provider.env" && sudo chown root:root /etc/nc182/provider.env && sudo chmod 0600 /etc/nc182/provider.env && sudo test -s /etc/nc182/provider.env && echo placed' -- -o StrictHostKeyChecking=no
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
