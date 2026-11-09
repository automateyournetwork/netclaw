#!/usr/bin/env bash
# R09 (spec 182): deploy one prepared generation onto the three nc182 Border VMs. Run under bash.
# usage: ha-r09-deploy-gen.sh <gen-root> <evidence-dir>
# Preconditions: r09_prepare.py prepare ran for <gen-root>; DNS A records exist; lego certs issued into
# <gen-root>/lego-<code>/certificates/. Archives the previous VM state into <evidence-dir> before wiping it.
set -uo pipefail
G="$1"; EV="$2"; mkdir -p "$EV"; chmod 700 "$EV"
here="$(cd "$(dirname "$0")/.." && pwd)"; cd "$here"
zone() { case "$1" in nne1) echo northamerica-northeast1-b;; ew1) echo europe-west1-b;; ase1) echo asia-southeast1-a;; esac; }
retry() { local n=0; until "$@"; do n=$((n+1)); [ $n -ge 4 ] && return 1; sleep 6; done; }
ssh_() { gcloud compute ssh "nc182-border-$1" --zone="$(zone "$1")" --project=netclaw-506315 --tunnel-through-iap --quiet --command="$2" -- -o StrictHostKeyChecking=no -o ServerAliveInterval=20 2>&1 | grep -v "iap\|NumPy\|^$\|WARNING"; return "${PIPESTATUS[0]}"; }
scp_() { local c="$1"; shift; gcloud compute scp "$@" "nc182-border-$c:/tmp/" --zone="$(zone "$c")" --project=netclaw-506315 --tunnel-through-iap --quiet >/dev/null 2>&1; }
msha=$(shasum -a 256 "$G/source-manifest.json" | cut -d' ' -f1)
cp "$G/summary.json" "$G/cluster.json"; python3.10 labs/ha/r09_hud_pack.py "$G/hud-source.tar" >/dev/null

phase1() { c="$1"
  retry ssh_ "$c" "sudo systemctl stop nc182-hud nc182-border 2>/dev/null; sudo journalctl -u nc182-border --no-pager > /tmp/border-$c.log 2>/dev/null; sudo tar czf /tmp/prev-$c.tgz -C /var/lib nc182 2>/dev/null; sudo chmod 644 /tmp/prev-$c.tgz /tmp/border-$c.log" >/dev/null
  retry gcloud compute scp "nc182-border-$c:/tmp/prev-$c.tgz" "nc182-border-$c:/tmp/border-$c.log" "$EV/" --zone="$(zone "$c")" --project=netclaw-506315 --tunnel-through-iap --quiet >/dev/null 2>&1
  retry ssh_ "$c" "sudo docker rm -f nc182-etcd >/dev/null 2>&1; sudo find /var/lib/nc182 -mindepth 1 -maxdepth 1 -exec rm -rf {} +" >/dev/null
  retry bash scripts/ha-r09-push.sh "$G" "$c" "$msha" >"$G/push-$c.log" 2>&1
  retry scp_ "$c" scripts/ha-r09-vm-net-etcd.sh scripts/ha-r09-vm-units.sh
  retry ssh_ "$c" "sudo bash /tmp/ha-r09-vm-net-etcd.sh" | grep nc182-etcd | tail -1 | sed "s/^/$c etcd: /"
}
for c in nne1 ew1 ase1; do phase1 "$c" & done; wait

# etcd RBAC + authority bootstrap (one-shot, from the first Border)
retry scp_ nne1 labs/ha/r09_vm_etcd_bootstrap.py
retry ssh_ nne1 "chmod 644 /tmp/r09_vm_etcd_bootstrap.py; sudo -u nc182 -H /opt/nc182/venv/bin/python -B /tmp/r09_vm_etcd_bootstrap.py; sudo rm -rf /var/lib/nc182/etcd-bootstrap"

# Borders (Montreal first so it takes the lease), then HUD ingress per host
for c in nne1 ew1 ase1; do retry ssh_ "$c" "sudo bash /tmp/ha-r09-vm-units.sh border; sleep 12; systemctl is-active nc182-border" | tail -1 | sed "s/^/$c border: /"; done
for i in $(seq 1 120); do n=0; for c in nne1 ew1 ase1; do ls "$G/lego-$c/certificates/"*.key >/dev/null 2>&1 && n=$((n+1)); done; [ $n -eq 3 ] && break; sleep 5; done
phase2() { c="$1"; d=$(python3.10 -c "import json;print([n['dns'] for n in json.load(open('$G/summary.json'))['nodes'] if n['code']=='$c'][0])")
  retry scp_ "$c" "$G/hud-source.tar" labs/ha/r09_vm_hud.py "$G/lego-$c/certificates/$d.crt" "$G/lego-$c/certificates/$d.key"
  retry ssh_ "$c" "sudo /opt/nc182/venv/bin/python -B /tmp/r09_vm_hud.py --hud-tar /tmp/hud-source.tar --cert /tmp/$d.crt --key /tmp/$d.key; sudo shred -u /tmp/$d.key /tmp/$d.crt; sudo bash /tmp/ha-r09-vm-units.sh hud; sleep 6; systemctl is-active nc182-hud" | grep -o 'prepare_exit": [0-9]*\|^active\|inactive\|failed' | tr '\n' ' ' | sed "s/^/$c hud: /"; echo
}
for c in nne1 ew1 ase1; do phase2 "$c" & done; wait
echo "deploy-gen done"
