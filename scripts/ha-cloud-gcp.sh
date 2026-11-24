# GCP driver for ha-cloud.sh (sourced). Reproduces the commands hardcoded in scripts/ha-r09-*.sh (project, zones, IAP).
GCP_PROJECT="${GCP_PROJECT:-netclaw-506315}"
GCP_VM_PREFIX="${GCP_VM_PREFIX:-nc182-border}"   # R09 compatibility; spec 198 mesh uses GCP_VM_PREFIX=nc198-<phase>
GCP_IMAGE_FAMILY="${GCP_IMAGE_FAMILY:-ubuntu-2404-lts-amd64}"   # Landlock ABI >= 3 gate: Ubuntu 24.04 (Debian 12 is unsuitable)
GCP_IMAGE_PROJECT="${GCP_IMAGE_PROJECT:-ubuntu-os-cloud}"
gcp_labels() { echo "netclaw-spec=198,phase=$1${R10_RUN_ID:+,run-id=$R10_RUN_ID}"; }
gcp_zone() { case "$1" in nne1) echo northamerica-northeast1-b;; ew1) echo europe-west1-b;; ase1) echo asia-southeast1-a;; gcpm) echo us-central1-a;; *) echo "unknown code $1" >&2; return 2;; esac; }
gcp_vm() { echo "$GCP_VM_PREFIX-$1"; }
cloud_up() { # <phase> <code> <region(ignored, zone from code)> <size>
  local phase="$1" code="$2" size="${4:-e2-medium}"
  run gcloud compute instances create "$(gcp_vm "$code")" --zone="$(gcp_zone "$code")" --project="$GCP_PROJECT" --machine-type="$size" \
    --image-family="$GCP_IMAGE_FAMILY" --image-project="$GCP_IMAGE_PROJECT" --boot-disk-size="${R10_OS_DISK_GB:-40}GB" \
    --tags="nc198-$phase" --labels="$(gcp_labels "$phase")" --quiet
}
cloud_ssh() { # <phase> <code> <command>
  run gcloud compute ssh "$(gcp_vm "$2")" --zone="$(gcp_zone "$2")" --project="$GCP_PROJECT" --tunnel-through-iap --quiet --command="$3" -- -o StrictHostKeyChecking=no -o ServerAliveInterval=20
}
cloud_scp() { # <phase> <code> <files...>
  local code="$2"; shift 2
  run gcloud compute scp "$@" "$(gcp_vm "$code"):/tmp/" --zone="$(gcp_zone "$code")" --project="$GCP_PROJECT" --tunnel-through-iap --quiet
}
cloud_ip() { run gcloud compute instances describe "$(gcp_vm "$2")" --zone="$(gcp_zone "$2")" --project="$GCP_PROJECT" --format='value(networkInterfaces[0].accessConfigs[0].natIP)'; }
cloud_firewall() { # <phase>: owner ingress (443, federation) from R10_SSH_ALLOW_CIDR; node-to-node etcd/peers inside the VPC.
  # Rules are scoped to the target tag nc198-<phase>, named nc198-<phase>-*, and listed in the watchdog manifest (--gcp-firewall).
  local phase="$1" net="${GCP_NETWORK:-default}" owner="${R10_SSH_ALLOW_CIDR:-}"
  [ -n "$owner" ] || { [ "$HA_DRY" = 1 ] && owner="<owner-ip>/32" || { echo "R10_SSH_ALLOW_CIDR is required (owner public IP /32)" >&2; return 2; }; }
  run gcloud compute firewall-rules create "nc198-$phase-owner" --network="$net" --project="$GCP_PROJECT" --direction=INGRESS \
    --allow=tcp:443,tcp:7443,tcp:7444 --source-ranges="$owner" --target-tags="nc198-$phase" --description="netclaw-spec=198 run-id=${R10_RUN_ID:-}" --quiet
  run gcloud compute firewall-rules create "nc198-$phase-mesh" --network="$net" --project="$GCP_PROJECT" --direction=INGRESS \
    --allow=tcp:12379,tcp:12380,tcp:7443,tcp:7444 --source-tags="nc198-$phase" --target-tags="nc198-$phase" --description="netclaw-spec=198 run-id=${R10_RUN_ID:-}" --quiet
}
cloud_peer() { echo "gcp: global VPC, no peering needed"; }
cloud_stop() { run gcloud compute instances stop "$(gcp_vm "$2")" --zone="$(gcp_zone "$2")" --project="$GCP_PROJECT" --quiet; }
cloud_start() { run gcloud compute instances start "$(gcp_vm "$2")" --zone="$(gcp_zone "$2")" --project="$GCP_PROJECT" --quiet; }
cloud_down() { # <phase>: delete every labelled instance
  local phase="$1"
  if [ "$HA_DRY" = 1 ]; then echo "gcloud compute instances list --filter labels.netclaw-spec=198 AND labels.phase=$phase | delete each"; return; fi
  gcloud compute instances list --project="$GCP_PROJECT" --filter="labels.netclaw-spec=198 AND labels.phase=$phase" --format='value(name,zone.basename())' |
    while read -r n z; do [ -n "$n" ] && gcloud compute instances delete "$n" --zone="$z" --project="$GCP_PROJECT" --quiet; done
  for r in "nc198-$phase-owner" "nc198-$phase-mesh"; do
    gcloud compute firewall-rules describe "$r" --project="$GCP_PROJECT" >/dev/null 2>&1 &&
      gcloud compute firewall-rules delete "$r" --project="$GCP_PROJECT" --quiet || true
  done
}
cloud_list() { run gcloud compute instances list --project="$GCP_PROJECT" --filter="labels.netclaw-spec=198${1:+ AND labels.phase=$1}" --format='table(name,zone.basename(),status,labels.phase)'; }
cloud_get() { # <phase> <code> <localdir> <remote files...>
  local code="$2" dir="$3"; shift 3; local f srcs=()
  for f in "$@"; do srcs+=("$(gcp_vm "$code"):$f"); done
  run gcloud compute scp "${srcs[@]}" "$dir/" --zone="$(gcp_zone "$code")" --project="$GCP_PROJECT" --tunnel-through-iap --quiet
}
