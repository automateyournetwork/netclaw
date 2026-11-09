#!/usr/bin/env bash
# R09 (spec 182): roll the full workspace (backend HUD + OpenClaw gateway) onto all three HA Border VMs. Run under bash.
# usage: ha-r09-deploy-workspace.sh <gen-root> <env-file-with-ANTHROPIC_API_KEY>
# The Border and ingress identity are untouched; only nc182-hud restarts. The provider key is streamed by
# scripts/ha-r09-place-provider-key.sh (never printed or stored locally).
set -uo pipefail
G="$1"; ENVF="$2"; here="$(cd "$(dirname "$0")/.." && pwd)"; cd "$here"
zone() { case "$1" in nne1) echo northamerica-northeast1-b;; ew1) echo europe-west1-b;; ase1) echo asia-southeast1-a;; esac; }
retry() { local n=0; until "$@"; do n=$((n+1)); [ $n -ge 4 ] && return 1; sleep 6; done; }
ssh_() { gcloud compute ssh "nc182-border-$1" --zone="$(zone "$1")" --project=netclaw-506315 --tunnel-through-iap --quiet --command="$2" -- -o StrictHostKeyChecking=no -o ServerAliveInterval=20 2>&1 | grep -v "iap\|NumPy\|^$\|WARNING"; return "${PIPESTATUS[0]}"; }
scp_() { local c="$1"; shift; gcloud compute scp "$@" "nc182-border-$c:/tmp/" --zone="$(zone "$c")" --project=netclaw-506315 --tunnel-through-iap --quiet >/dev/null 2>&1; }
PY=/private/tmp/claude-503/-Users-john-capobianco-netclaw/8e4f7aba-bfb3-4565-9ae8-2535153d5ff0/scratchpad/r09venv/bin/python
W="$G/workspace"; mkdir -p "$W"; chmod 700 "$W"
python3.10 labs/ha/r09_hud_pack.py "$G/hud-source.tar" >/dev/null
[ -f "$W/workspace-backend.tar" ] || $PY labs/ha/r09_workspace.py pack --out "$W/workspace-backend.tar"
node_json() { python3.10 -c "import json;print([n['installation_id'] for n in json.load(open('$G/summary.json'))['nodes'] if n['code']=='$1'][0])"; }

phase() { c="$1"; d="$W/$c"
  [ -f "$d/workspace.edge.json" ] || $PY labs/ha/r09_workspace.py render --installation-id "$(node_json "$c")" --out-dir "$d" >/dev/null
  retry scp_ "$c" "$W/workspace-backend.tar" "$d/workspace.edge.json" "$d/workspace.backend.json" "$d/conversation-home/openclaw.json" scripts/ha-r09-vm-workspace.sh "$G/hud-source.tar" labs/ha/r09_vm_hud.py
  echo "$c install: $(retry ssh_ "$c" "sudo bash /tmp/ha-r09-vm-workspace.sh install >/tmp/ws-install.log 2>&1; echo exit=\$?; tail -2 /tmp/ws-install.log" | tr '\n' ' ')"
  echo "$c configure: $(retry ssh_ "$c" "sudo bash /tmp/ha-r09-vm-workspace.sh configure >/tmp/ws-configure.log 2>&1; echo exit=\$?; tail -2 /tmp/ws-configure.log" | tr '\n' ' ')"
  if retry ssh_ "$c" "sudo test -f /etc/nc182/provider.env && echo present" | grep -q present; then echo "$c key already placed"; else retry bash scripts/ha-r09-place-provider-key.sh "$c" "$ENVF" >/dev/null 2>&1 && echo "$c key placed" || echo "$c KEY PLACEMENT FAILED"; fi
  echo "$c start: $(retry ssh_ "$c" "sudo bash /tmp/ha-r09-vm-workspace.sh start >/tmp/ws-start.log 2>&1; echo exit=\$?; tail -3 /tmp/ws-start.log" | tr '\n' ' ')"
  echo "$c hud: $(retry ssh_ "$c" "sudo systemctl stop nc182-hud; sudo /opt/nc182/venv/bin/python -B /tmp/r09_vm_hud.py --hud-tar /tmp/hud-source.tar --cert /var/lib/nc182/tls/fullchain.pem --key /var/lib/nc182/tls/key.pem | grep -o 'prepare_exit\": [0-9]*'; sudo systemctl start nc182-hud; sleep 6; systemctl is-active nc182-hud nc182-wshud nc182-gateway" | tr '\n' ' ')"
}
for c in nne1 ew1 ase1; do phase "$c" & done; wait
echo "workspace rollout done"
