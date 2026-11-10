#!/usr/bin/env bash
# R09A (spec 183) infrastructure driver for the validation topology: 2 Border VMs + 1 etcd witness VM in ONE region.
#
#   ha-r09a-deploy.sh plan                                   read-only: print every resource this stage would own
#   ha-r09a-deploy.sh apply --confirm-cost --g1-file FILE    create (refused without BOTH the flag and an approval file)
#   ha-r09a-deploy.sh status                                 list owned resources (label netclaw-spec=183 / prefix nc183-)
#   ha-r09a-deploy.sh ssh NAME 'command'                     IAP ssh with retries
#   ha-r09a-deploy.sh teardown --confirm                     list, then delete ONLY owned resources
#
# Ownership: label `netclaw-spec=183` or name prefix `nc183-`. The default network, default-* firewall rules and anything
# else are never touched. Nothing here prints a secret. `gcloud` is overridable via GCLOUD (tests use a stub).
# G1 approval file: a private text file the owner (or the owner's instruction recorded by the agent) creates after
# confirming specs/183-openshell-defenseclaw-gcp/cost-model.md; it must contain a line `G1: APPROVED`.
set -euo pipefail

GCLOUD="${GCLOUD:-gcloud}"
PROJECT="${NC183_PROJECT:-netclaw-506315}"
REGION="${NC183_REGION:-northamerica-northeast1}"
ZONE_A="${NC183_ZONE_A:-${REGION}-b}"
ZONE_B="${NC183_ZONE_B:-${REGION}-c}"
ZONE_W="${NC183_ZONE_W:-${REGION}-b}"
BORDER_TYPE="${NC183_BORDER_TYPE:-e2-standard-2}"
WITNESS_TYPE="${NC183_WITNESS_TYPE:-e2-small}"
NETWORK=nc183-r09a
SUBNET=nc183-sub
CIDR=10.183.2.0/24
LABELS="netclaw-spec=183"
OWNED_RE='^nc183-[a-z0-9-]+$'

log() { printf '[r09a-deploy] %s\n' "$*" >&2; }
die() { printf '[r09a-deploy] ERROR: %s\n' "$*" >&2; exit 1; }
g() { "$GCLOUD" "$@" --project="$PROJECT" --quiet; }

# name|kind|detail  (single source of truth for plan, apply and tests)
resources() {
  cat <<EOF
$NETWORK|network|custom-mode VPC
$SUBNET|subnet|$CIDR in $REGION
nc183-allow-iap-ssh|firewall|tcp:22 from 35.235.240.0/20 to tag nc183-node (IAP only)
nc183-allow-mesh|firewall|tcp:2379-2380,tcp:7443 from $CIDR (cluster plane stays internal)
nc183-allow-public|firewall|tcp:443,tcp:7444 from 0.0.0.0/0 to tag nc183-border (HUD and iN2N)
nc183-ip-a|address|static external IPv4 for border-a in $REGION
nc183-ip-b|address|static external IPv4 for border-b in $REGION
nc183-border-a|instance|$BORDER_TYPE ubuntu-2404-lts-amd64 40GB pd-balanced in $ZONE_A (Border node)
nc183-border-b|instance|$BORDER_TYPE ubuntu-2404-lts-amd64 40GB pd-balanced in $ZONE_B (Border node)
nc183-witness|instance|$WITNESS_TYPE ubuntu-2404-lts-amd64 20GB pd-balanced in $ZONE_W (etcd witness only, no Border)
EOF
}

cmd_plan() {
  echo "R09A validation topology (project $PROJECT, region $REGION). Labels: $LABELS. Nothing is created by 'plan'."
  printf '%-22s %-10s %s\n' NAME KIND DETAIL
  resources | while IFS='|' read -r n k d; do printf '%-22s %-10s %s\n' "$n" "$k" "$d"; done
  echo "Cost: see specs/183-openshell-defenseclaw-gcp/cost-model.md (apply requires --confirm-cost and --g1-file)."
}

check_g1() {
  local confirm="$1" file="$2"
  [ "$confirm" = 1 ] || die "refused: apply requires --confirm-cost (owner must confirm the line-item estimate first, gate G1)"
  [ -n "$file" ] || die "refused: apply requires --g1-file <approval file>"
  [ -s "$file" ] || die "refused: G1 approval file '$file' is missing or empty"
  grep -qiE '^G1:[[:space:]]*APPROVED[[:space:]]*$' "$file" || die "refused: '$file' must contain a line 'G1: APPROVED'"
}

# exists "<command group>" NAME [flags]  (group may be two words, e.g. "networks subnets")
exists() { local grp="$1"; shift; g compute $grp describe "$@" >/dev/null 2>&1; }

cmd_apply() {
  local confirm=0 file=""
  while [ $# -gt 0 ]; do
    case "$1" in --confirm-cost) confirm=1 ;; --g1-file) shift; file="${1:-}" ;; *) die "unknown option $1" ;; esac; shift
  done
  check_g1 "$confirm" "$file"
  log "G1 satisfied; creating owned resources in $PROJECT/$REGION"
  exists networks "$NETWORK" || g compute networks create "$NETWORK" --subnet-mode=custom >/dev/null
  exists "networks subnets" "$SUBNET" --region="$REGION" || g compute networks subnets create "$SUBNET" --network="$NETWORK" --region="$REGION" --range="$CIDR" >/dev/null
  exists firewall-rules "nc183-allow-iap-ssh" || g compute firewall-rules create nc183-allow-iap-ssh --network="$NETWORK" --allow=tcp:22 --source-ranges=35.235.240.0/20 --target-tags=nc183-node >/dev/null
  exists firewall-rules "nc183-allow-mesh" || g compute firewall-rules create nc183-allow-mesh --network="$NETWORK" --allow=tcp:2379-2380,tcp:7443 --source-ranges="$CIDR" --target-tags=nc183-node >/dev/null
  exists firewall-rules "nc183-allow-public" || g compute firewall-rules create nc183-allow-public --network="$NETWORK" --allow=tcp:443,tcp:7444 --source-ranges=0.0.0.0/0 --target-tags=nc183-border >/dev/null
  for ip in a b; do
    exists addresses "nc183-ip-$ip" --region="$REGION" || g compute addresses create "nc183-ip-$ip" --region="$REGION" >/dev/null
  done
  create_instance nc183-border-a "$ZONE_A" "$BORDER_TYPE" 40 border nc183-ip-a
  create_instance nc183-border-b "$ZONE_B" "$BORDER_TYPE" 40 border nc183-ip-b
  create_instance nc183-witness "$ZONE_W" "$WITNESS_TYPE" 20 witness ""
  cmd_status
}

create_instance() {
  local name="$1" zone="$2" type="$3" disk="$4" role="$5" ip="$6" tags="nc183-node" addr="" extra=()
  [ "$role" = border ] && tags="nc183-node,nc183-border"
  [ -n "$ip" ] && addr="--address=$ip"
  exists instances "$name" --zone="$zone" && { log "$name exists"; return 0; }
  # shellcheck disable=SC2086
  g compute instances create "$name" --zone="$zone" --machine-type="$type" --subnet="$SUBNET" $addr \
    --tags="$tags" --labels="$LABELS,netclaw-role=$role" --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
    --boot-disk-size="${disk}GB" --boot-disk-type=pd-balanced >/dev/null
}

cmd_status() {
  echo "== instances";   g compute instances list --filter="labels.netclaw-spec=183" --format="table(name,zone.basename(),machineType.basename(),status,networkInterfaces[0].accessConfigs[0].natIP)" || true
  echo "== addresses";   g compute addresses list --filter="name~^nc183-" --format="table(name,region.basename(),address,status)" || true
  echo "== firewalls";   g compute firewall-rules list --filter="name~^nc183-" --format="table(name,network.basename(),sourceRanges.list():label=SRC)" || true
  echo "== network";     g compute networks list --filter="name~^nc183-" --format="table(name)" || true
  echo "== subnets";     g compute networks subnets list --filter="name~^nc183-" --format="table(name,region.basename(),ipCidrRange)" || true
}

cmd_ssh() {
  local name="${1:-}" command="${2:-}" zone out i
  [[ "$name" =~ $OWNED_RE ]] || die "refused: '$name' is not an owned (nc183-) instance"
  [ -n "$command" ] || die "usage: ssh NAME 'command'"
  case "$name" in nc183-border-a) zone="$ZONE_A" ;; nc183-border-b) zone="$ZONE_B" ;; nc183-witness) zone="$ZONE_W" ;; *) die "unknown owned instance $name" ;; esac
  for i in 1 2 3 4; do
    out="$("$GCLOUD" compute ssh "$name" --zone="$zone" --project="$PROJECT" --tunnel-through-iap --quiet --command="$command" -- -o StrictHostKeyChecking=no -o ServerAliveInterval=20 2>&1)" && { printf '%s\n' "$out"; return 0; }
    if printf '%s' "$out" | grep -qiE 'Connection closed|255|Connection refused|timed out|could not parse'; then sleep 8; continue; fi
    printf '%s\n' "$out" >&2; return 1
  done
  printf '%s\n' "$out" >&2; return 1
}

# Names only, filtered twice: by gcloud filter and again by the ownership regex here.
owned_names() {
  local kind="$1"; shift
  g compute "$@" list --format="value(name)" 2>/dev/null | grep -E "$OWNED_RE" || true
}

cmd_teardown() {
  local confirm=0
  while [ $# -gt 0 ]; do case "$1" in --confirm) confirm=1 ;; *) die "unknown option $1" ;; esac; shift; done
  local inst fw addr sub net
  inst="$(g compute instances list --filter="labels.netclaw-spec=183" --format='value(name,zone.basename())' 2>/dev/null | awk '$1 ~ /^nc183-/' || true)"
  fw="$(owned_names firewall firewall-rules)"
  addr="$(g compute addresses list --filter='name~^nc183-' --format='value(name,region.basename())' 2>/dev/null | awk '$1 ~ /^nc183-/' || true)"
  sub="$(g compute networks subnets list --filter='name~^nc183-' --format='value(name,region.basename())' 2>/dev/null | awk '$1 ~ /^nc183-/' || true)"
  net="$(owned_names network networks)"
  echo "Teardown list (label netclaw-spec=183 / prefix nc183- only):"
  echo "instances:"; printf '%s\n' "$inst" | sed 's/^/  /'
  echo "addresses:"; printf '%s\n' "$addr" | sed 's/^/  /'
  echo "firewalls:"; printf '%s\n' "$fw" | sed 's/^/  /'
  echo "subnets:";   printf '%s\n' "$sub" | sed 's/^/  /'
  echo "networks:";  printf '%s\n' "$net" | sed 's/^/  /'
  [ "$confirm" = 1 ] || die "listed only. Re-run with --confirm after the owner confirms this exact list."
  printf '%s\n' "$inst" | while read -r n z; do if [ -n "$n" ] && [[ "$n" =~ $OWNED_RE ]]; then g compute instances delete "$n" --zone="$z" --delete-disks=all >/dev/null; fi; done
  printf '%s\n' "$addr" | while read -r n r; do if [ -n "$n" ] && [[ "$n" =~ $OWNED_RE ]]; then g compute addresses delete "$n" --region="$r" >/dev/null; fi; done
  printf '%s\n' "$fw" | while read -r n; do if [ -n "$n" ] && [[ "$n" =~ $OWNED_RE ]]; then g compute firewall-rules delete "$n" >/dev/null; fi; done
  printf '%s\n' "$sub" | while read -r n r; do if [ -n "$n" ] && [[ "$n" =~ $OWNED_RE ]]; then g compute networks subnets delete "$n" --region="$r" >/dev/null; fi; done
  printf '%s\n' "$net" | while read -r n; do if [ -n "$n" ] && [[ "$n" =~ $OWNED_RE ]]; then g compute networks delete "$n" >/dev/null; fi; done
  log "teardown complete"
}

case "${1:-}" in
  plan) shift; cmd_plan "$@" ;;
  apply) shift; cmd_apply "$@" ;;
  status) shift; cmd_status "$@" ;;
  ssh) shift; cmd_ssh "$@" ;;
  teardown) shift; cmd_teardown "$@" ;;
  *) die "usage: $0 plan | apply --confirm-cost --g1-file FILE | status | ssh NAME CMD | teardown --confirm" ;;
esac
