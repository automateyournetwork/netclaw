#!/usr/bin/env bash
# Spec 198: bring up BOTH three-Border groups (Azure `az`, GCP `gc`) in parallel and attach members. Billable: needs the owner's go.
#   R10_GO=mesh AZ_RUN=r10g-YYYYMMDD GC_RUN=r10h-YYYYMMDD R10_GUARD_DIR=<dir> R10_ACME_EMAIL=<acme contact> \
#     bash scripts/ha-r10-mesh-up.sh [--from <step>] [--members "netbox:1 netbox:2 subnet:sn1 ..."]
# Steps (each group): vms nodes zone bootstrap prepare dns cert peer-fw policy-payload image provider etcd sandbox authority members start
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"; cd "$here"
[ "${R10_GO:-}" = mesh ] || { echo "refused: owner go required (export R10_GO=mesh)" >&2; exit 4; }
: "${AZ_RUN:?AZ_RUN}"; : "${GC_RUN:?GC_RUN}"; : "${R10_GUARD_DIR:?R10_GUARD_DIR}"; : "${R10_ACME_EMAIL:?R10_ACME_EMAIL}"
CIDR="${R10_SSH_ALLOW_CIDR:-$(curl -s -m 10 https://api.ipify.org)/32}"; [ "$CIDR" != "/32" ] || { echo "cannot determine owner IP" >&2; exit 2; }
export R10_MAX_HOURS="${R10_HOURS:-8}"   # reserved window per VM in the ledger projection AND the watchdog deadline
FROM=vms; MEMBERS="${R10_MEMBERS:-netbox:1 netbox:2 netbox:3 netbox:4 subnet:sn1 subnet:sn2}"
while [ $# -gt 0 ]; do case "$1" in --from) FROM="$2"; shift 2;; --members) MEMBERS="$2"; shift 2;; *) echo "unknown arg $1" >&2; exit 2;; esac; done
STEPS=(vms nodes zone bootstrap prepare dns cert peer-fw policy-payload image provider etcd sandbox authority members start)
export R10_SSH_ALLOW_CIDR="$CIDR" R10_GO_DNS=1 AZ_SSH_KEY="${AZ_SSH_KEY:-$HOME/.ssh/nc198_azure}" R10_AZ_REGION_EW1="${R10_AZ_REGION_EW1:-eastus2}" R10_AZ_REGION_ASE1="${R10_AZ_REGION_ASE1:-swedencentral}"
export R10_SIZE_AZ="${R10_SIZE_AZ:-Standard_D2as_v7}" R10_SIZE_GCP="${R10_SIZE_GCP:-e2-standard-2}" R10_PY="${R10_PY:-$HOME/.local/share/netclaw/r10-venv/bin/python}"
AZ_GROUP_NAME="rg-nc198-p3-ha-az"; GC_PREFIX="nc198-p3-ha-gc"
genv() { # <az|gc>: environment for ha-r10-build-group.sh
  if [ "$1" = az ]; then echo "PROVIDER=azure GROUP=az R10_RUN_ID=$AZ_RUN PHASE=p3-ha-az"; else echo "PROVIDER=gcp GROUP=gc R10_RUN_ID=$GC_RUN PHASE=p3-ha-gc GCP_VM_PREFIX=$GC_PREFIX"; fi; }
ev() { echo "$HOME/.local/share/netclaw/r10-run-$([ "$1" = az ] && echo "$AZ_RUN" || echo "$GC_RUN")"; }
other() { [ "$1" = az ] && echo gc || echo az; }
peerenv() { local o; o="$(other "$1")"; echo "PEER_GEN=$(ev "$o")/gen-$o PEER_NODES=$(ev "$o")/nodes.txt PEER_LABEL=$([ "$o" = az ] && echo azure || echo gcp)"; }
build() { env $(genv "$1") $(peerenv "$1") bash scripts/ha-r10-build-group.sh "${@:2}"; }
past() { local s; for s in "${STEPS[@]}"; do [ "$s" = "$FROM" ] && return 0; [ "$s" = "$1" ] && return 1; done; return 0; }   # true when step >= FROM
step_vms() {
  python3 labs/ha/r10_ledger.py status | grep -q '"paused": false' || { echo "ledger paused" >&2; return 3; }
  bash scripts/ha-r10-run-init.sh "$AZ_RUN" "${R10_HOURS:-8}" "$AZ_GROUP_NAME" >/dev/null
  bash scripts/ha-r10-run-init.sh "$GC_RUN" "${R10_HOURS:-8}" --gcp-project "${GCP_PROJECT:-netclaw-506315}" \
    --gcp-firewall "$GC_PREFIX-owner" --gcp-firewall "$GC_PREFIX-mesh" --gcp-firewall "$GC_PREFIX-allow-fed" >/dev/null
  # Exact run labels are required by the watchdog. Serial phase creation also
  # propagates a failure instead of masking a failed background `up` with wait.
  R10_RUN_ID="$AZ_RUN" R10_GO=p3-ha-az R10_SIZE="$R10_SIZE_AZ" R10_RATE_USD_PER_H=0.15 bash scripts/ha-r10-phase.sh up p3-ha-az nne1 ew1 ase1
  R10_RUN_ID="$GC_RUN" GCP_VM_PREFIX="$GC_PREFIX" R10_GO=p3-ha-gc R10_SIZE="$R10_SIZE_GCP" R10_RATE_USD_PER_H=0.12 bash scripts/ha-r10-phase.sh up p3-ha-gc nne1 ew1 ase1 --provider gcp
}
run_step() { # <step>: both groups in parallel; all must succeed
  local s="$1" g rc=0 pids=()
  for g in az gc; do ( build "$g" "$s" > "$(ev "$g")/step-$s.log" 2>&1 ) & pids+=($!); done
  for p in "${pids[@]}"; do wait "$p" || rc=1; done
  echo "step $s: $([ $rc = 0 ] && echo ok || echo FAILED)"; return $rc
}
mkdir -p "$(ev az)" "$(ev gc)"; chmod 700 "$(ev az)" "$(ev gc)"
export R10_GUARD_DIR R10_ACME_EMAIL
for s in "${STEPS[@]}"; do
  past "$s" || continue
  case "$s" in
    vms) step_vms;;
    members)
      for g in az gc; do E="$(ev $g)"; args=(); n=0
        for spec in $MEMBERS; do args+=("${spec%%:*}:$g${spec##*:}"); done
        env R10_RUN_ID="$([ $g = az ] && echo "$AZ_RUN" || echo "$GC_RUN")" GEN="$E/gen-$g" bash scripts/ha-r10-members.sh build "${args[@]}" > "$E/members-build.log" 2>&1 || { echo "member build failed ($E/members-build.log)"; exit 1; }
      done; run_step enroll-members;;
    *) run_step "$s";;
  esac
done
for g in az gc; do E="$(ev $g)"; names=""; for spec in $MEMBERS; do names="$names $g${spec##*:}"; done
  env R10_RUN_ID="$([ $g = az ] && echo "$AZ_RUN" || echo "$GC_RUN")" bash scripts/ha-r10-members.sh start $names; done
echo "mesh up. HUD URLs:"; for g in az gc; do for c in nne1 ew1 ase1; do python3 - "$(ev $g)" "$g" "$c" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]+'/gen-'+sys.argv[2]+'/summary.json'))
print(' ', sys.argv[2], sys.argv[3], 'https://'+[n for n in s['nodes'] if n['code']==sys.argv[3]][0]['dns'])
PY
done; done
