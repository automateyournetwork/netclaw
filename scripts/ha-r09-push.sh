#!/usr/bin/env bash
# Push R09 artifacts to one Border VM and finalize the frozen source/venv/contract.
# usage: ha-r09-push.sh <root> <code> <source-manifest-sha256>
set -euo pipefail
R="$1"; code="$2"; msha="$3"
case "$code" in nne1) z=northamerica-northeast1-b;; ew1) z=europe-west1-b;; ase1) z=asia-southeast1-a;; *) exit 2;; esac
vm="nc182-border-$code"; here="$(cd "$(dirname "$0")/.." && pwd)"
scp() { gcloud compute scp "$@" --zone="$z" --project=netclaw-506315 --tunnel-through-iap --quiet >/dev/null 2>&1; }
ssh() { gcloud compute ssh "$vm" --zone="$z" --project=netclaw-506315 --tunnel-through-iap --quiet --command="$1" -- -o StrictHostKeyChecking=no -o ServerAliveInterval=20; }
scp "$R/source.tar" "$R/source-manifest.json" "$R/bundles/$code.tar" "$R/etcd-owned.json" "$R/cluster.json" \
    "$R/hud-source.tar" "$here/labs/ha/r09_vm_finalize.py" "$here/labs/ha/r09_vm_hud.py" "$vm:/tmp/"
ssh "sudo mv /tmp/$code.tar /tmp/bundle.tar && sudo /opt/nc182/venv/bin/python -B /tmp/r09_vm_finalize.py --source-tar /tmp/source.tar --bundle /tmp/bundle.tar --source-manifest-sha256 $msha --source-manifest-file /tmp/source-manifest.json --refreeze && sudo cp /tmp/etcd-owned.json /tmp/cluster.json /var/lib/nc182/ && sudo chown nc182:nc182 /var/lib/nc182/etcd-owned.json /var/lib/nc182/cluster.json && sudo chmod 600 /var/lib/nc182/etcd-owned.json /var/lib/nc182/cluster.json"
