#!/usr/bin/env bash
# R10 (spec 198) cloud-neutral copy of ha-r09-push.sh. Push artifacts to one Border VM and finalize the frozen source/venv/contract.
# usage: PHASE=<phase> ha-r10-push.sh <root> <code> <source-manifest-sha256>
set -euo pipefail
R="$1"; code="$2"; msha="$3"
PHASE="${PHASE:?PHASE e.g. p3-ha}"; PROVIDER="${PROVIDER:-azure}"
here="$(cd "$(dirname "$0")/.." && pwd)"
drv() { bash "$here/scripts/ha-cloud.sh" "$PROVIDER" "$@"; }
scp() { drv scp "$PHASE" "$code" "$@" >/dev/null 2>&1; }
ssh() { drv ssh "$PHASE" "$code" "$1"; }
scp "$R/source.tar" "$R/source-manifest.json" "$R/bundles/$code.tar" "$R/etcd-owned.json" "$R/cluster.json" \
    "$R/hud-source.tar" "$here/labs/ha/r09_vm_finalize.py" "$here/labs/ha/r09_vm_hud.py"
ssh "sudo mv /tmp/$code.tar /tmp/bundle.tar && sudo /opt/nc182/venv/bin/python -B /tmp/r09_vm_finalize.py --source-tar /tmp/source.tar --bundle /tmp/bundle.tar --source-manifest-sha256 $msha --source-manifest-file /tmp/source-manifest.json --refreeze && sudo cp /tmp/etcd-owned.json /tmp/cluster.json /var/lib/nc182/ && sudo chown nc182:nc182 /var/lib/nc182/etcd-owned.json /var/lib/nc182/cluster.json && sudo chmod 600 /var/lib/nc182/etcd-owned.json /var/lib/nc182/cluster.json"
