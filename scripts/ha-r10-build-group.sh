#!/usr/bin/env bash
# Spec 198 / R10: build ONE three-Border HA group (Azure or GCP) from the steps proven by hand in runs r10c/r10d.
#   PROVIDER=azure|gcp GROUP=az|gc R10_RUN_ID=<id> bash scripts/ha-r10-build-group.sh [--dry-run] <step>
# steps, in order (each is re-runnable; `plan` prints them):
#   nodes       write $EV/nodes.txt (code, public ip, private ip) from the cloud
#   zone        azure only: private DNS zone r10-<date>.azure.internal (A records azca/azus/azse) linked to the three VNets
#   bootstrap   pin SSH host keys (azure), host bootstrap (Docker, OpenShell 0.1.7, Landlock check) on every VM in parallel
#   prepare     identities, cluster manifest, etcd PKI, admission window (R10_ADMISSION_MS, default 4500; 3000 is too tight)
#   dns         GoDaddy A records for the three HUD names       (needs R10_GO_DNS=1: it changes public DNS)
#   cert        lego DNS-01 certificates, one per node           (needs R10_GO_DNS=1)
#   policy-payload   per-node sandbox policy (two remote voters), workspace/HUD packs, node payload
#   image       build the OpenShell node image on every VM
#   provider    OpenShell provider profile (auth_style header, x-api-key) + the Anthropic key (stdin only)
#   etcd        stage the voter bundle + start etcd on all three hosts together
#   sandbox     create each sandbox WITHOUT START (no Border runs yet)
#   authority   bootstrap etcd RBAC + authority once from nne1
#   enroll-members   one outage window: all sandboxes stopped, enroll each member file in $EV/members/*.json via nne1
#   start       touch START on nne1 first, then ew1, then ase1; wait for HTTPS posture 200
#   status      posture of every Border
#   kill-node <code> | start-node <code> | rotate <code>   takeover and certificate-rotation tests (live)
# Environment:
#   PROVIDER (azure|gcp)  GROUP (az|gc; default from provider)  R10_RUN_ID (required; ends in -YYYYMMDD)  PHASE (default p3-ha | gc-ha)
#   CODES (default "nne1 ew1 ase1")  R10_ADMISSION_MS (4500)  EV (default ~/.local/share/netclaw/r10-run-$R10_RUN_ID)
#   R10_PY (python with the image's pinned packages; default python3)  R10_ACME_EMAIL (cert step)  R10_GUARD_DIR (guard yaml dir)
#   R10_ENV_FILE (file holding ANTHROPIC_API_KEY, default repo .env)  R10_IMAGE (nc183-node:r10)  DOMAIN_BASE (automateyournetwork.com)
#   GCP: GCP_PROJECT, GCP_VM_PREFIX (default nc198-$PHASE, required to start with nc198-), AZ_SSH_KEY/R10_SSH_ALLOW_CIDR for azure.
# --dry-run prints every provider/remote/local command and changes nothing (no cloud, DNS or file writes under $EV).
# Never prints a secret: the GoDaddy token and the Anthropic key are read at run time and passed by env/stdin only.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
DRY=0; args=()
for a in "$@"; do if [ "$a" = "--dry-run" ]; then DRY=1; else args+=("$a"); fi; done
step="${args[0]:-plan}"
PROVIDER="${PROVIDER:?PROVIDER=azure|gcp}"
case "$PROVIDER" in azure) GROUP="${GROUP:-az}"; PHASE="${PHASE:-p3-ha}";; gcp) GROUP="${GROUP:-gc}"; PHASE="${PHASE:-gc-ha}";; *) echo "unknown PROVIDER $PROVIDER" >&2; exit 2;; esac
RUN="${R10_RUN_ID:?R10_RUN_ID}"; DATE="${RUN##*-}"
[[ "$DATE" =~ ^[0-9]{8}$ ]] || { echo "R10_RUN_ID must end in -YYYYMMDD" >&2; exit 2; }
CODES=(${CODES:-nne1 ew1 ase1}); [ "${#CODES[@]}" = 3 ] || { echo "three codes required" >&2; exit 2; }
ADM="${R10_ADMISSION_MS:-4500}"; IMAGE="${R10_IMAGE:-nc183-node:r10}"; BASE="${DOMAIN_BASE:-automateyournetwork.com}"
EV="${EV:-$HOME/.local/share/netclaw/r10-run-$RUN}"; G="$EV/gen-$GROUP"; PY="${R10_PY:-python3}"
if [ "$PROVIDER" = gcp ]; then
  export GCP_VM_PREFIX="${GCP_VM_PREFIX:-nc198-$PHASE}"; GCP_PROJECT="${GCP_PROJECT:-netclaw-506315}"; export GCP_PROJECT
  case "$GCP_VM_PREFIX" in nc198-*) ;; *) echo "GCP_VM_PREFIX must start with nc198- (watchdog scope)" >&2; exit 2;; esac
  GEXTRA=(--project "$GCP_PROJECT" --vm-prefix "$GCP_VM_PREFIX")
else GEXTRA=(); fi
export R10_RUN_ID="$RUN" PYTHONPATH="$here/mcp-servers/protocol-mcp:$here:$here/labs/ha"
[ -z "${R10_SSH_KNOWN_HOSTS:-}" ] && [ "$PROVIDER" = azure ] && export R10_SSH_KNOWN_HOSTS="$EV/known_hosts"
DRYFLAG=""; [ "$DRY" = 1 ] && DRYFLAG="--dry-run"

TMPF=(); trap 'rm -f "${TMPF[@]+"${TMPF[@]}"}"' EXIT
say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" = 1 ]; then printf '+ '; printf '%q ' "$@"; printf '\n'; else "$@"; fi; }
cl() { bash "$here/scripts/ha-cloud.sh" "$PROVIDER" "$1" "$PHASE" "${@:2}" $DRYFLAG; }       # <verb> <code> ...
# per-node work in parallel; any failure fails the step
each() { local fn="$1" pids=() c rc=0; for c in "${CODES[@]}"; do ( "$fn" "$c" ) & pids+=($!); done
  for p in "${pids[@]}"; do wait "$p" || rc=1; done; return $rc; }
nodes_file() { # real file when present; in --dry-run a placeholder set so later steps can print their commands
  if [ -s "$EV/nodes.txt" ]; then echo "$EV/nodes.txt"; return; fi
  [ "$DRY" = 1 ] || { echo "run the nodes step first ($EV/nodes.txt missing)" >&2; return 2; }
  local f; f="$(mktemp)"; TMPF+=("$f"); printf 'nne1 192.0.2.1 10.0.1.4\new1 192.0.2.2 10.0.2.4\nase1 192.0.2.3 10.0.3.4\n' > "$f"; echo "$f"; }
grp() { "$PY" "$here/labs/ha/r10_group.py" "$1" --provider "$PROVIDER" --run-date "$DATE" --nodes "$(nodes_file)" ${GEXTRA[@]+"${GEXTRA[@]}"} "${@:2}"; }
field() { # <code> <nodes column 2|3>
  awk -v c="$1" -v k="$2" '$1==c{print $k}' "$(nodes_file)"; }
dns_of() { # <code> -> the HUD DNS label (code-id6)
  if [ -s "$G/summary.json" ]; then "$PY" -c "import json,sys;print([n['dns'] for n in json.load(open('$G/summary.json'))['nodes'] if n['code']=='$1'][0])"
  else echo "$1-<id6>.$BASE"; fi; }
id6_of() { if [ -s "$G/summary.json" ]; then "$PY" -c "import json;print([n['id6'] for n in json.load(open('$G/summary.json'))['nodes'] if n['code']=='$1'][0])"; else echo "<id6>"; fi; }
iid_of() { if [ -s "$G/summary.json" ]; then "$PY" -c "import json;print([n['installation_id'] for n in json.load(open('$G/summary.json'))['nodes'] if n['code']=='$1'][0])"; else echo "<installation-id>"; fi; }
policy_sha() { if [ -s "$G/policy/out-$1/policy.yaml" ]; then grep -m1 'content sha256' "$G/policy/out-$1/policy.yaml" | awk '{print $NF}'; else echo "<policy-sha>"; fi; }
etcd_host() { grp node-spec --code "$1" | "$PY" -c "import json,sys;print(json.load(sys.stdin)['etcd'][0].rsplit(':',1)[0])"; }
RU='$(id -un)'     # the VM's login user, expanded by the REMOTE shell (ncadmin on azure, the IAP user on gcp)

step_plan() { sed -n '/^# steps/,/^# Environment/p' "$0" | sed '$d'; }

step_nodes() {
  [ "$DRY" = 1 ] && { say "+ write $EV/nodes.txt from: cl ip <code> + the VM private IP (az nic show / gcloud describe networkIP)"; return; }
  mkdir -p "$EV"; chmod 700 "$EV"; : > "$EV/nodes.txt"
  for c in "${CODES[@]}"; do
    pub="$(cl ip "$c" | tail -1)"
    if [ "$PROVIDER" = azure ]; then
      priv="$(az network nic show -g "rg-nc198-$PHASE" -n "$(az vm show -g "rg-nc198-$PHASE" -n "nc198-$PHASE-$c" --query 'networkProfile.networkInterfaces[0].id' -o tsv | xargs basename)" --query 'ipConfigurations[0].privateIPAddress' -o tsv)"
    else
      priv="$(gcloud compute instances describe "$GCP_VM_PREFIX-$c" --zone "$("$PY" -c "import r10_group as g;print(g.GCP_ZONES['$c'])")" --project "$GCP_PROJECT" --format='value(networkInterfaces[0].networkIP)')"
    fi
    echo "$c $pub $priv" >> "$EV/nodes.txt"
  done; chmod 600 "$EV/nodes.txt"; say "nodes written: $(wc -l < "$EV/nodes.txt") (see $EV/nodes.txt)"
}

step_zone() {
  [ "$PROVIDER" = azure ] || { say "gcp: zonal internal DNS exists already, no zone to create"; return 0; }
  local Z="r10-$DATE.azure.internal" rg="rg-nc198-$PHASE" tags="netclaw-spec=198 phase=$PHASE run-id=$RUN" c
  run az network private-dns zone create -g "$rg" -n "$Z" --tags $tags -o none
  for c in "${CODES[@]}"; do
    run az network private-dns link vnet create -g "$rg" -z "$Z" -n "link-$c" -v "vnet-nc198-$PHASE-$c" -e false --tags $tags -o none
    run az network private-dns record-set a add-record -g "$rg" -z "$Z" -n "$("$PY" -c "import r10_group as g;print(g.AZURE_NAMES['$c'])")" -a "$(field "$c" 3)" -o none
  done
}

step_bootstrap() {
  [ "$DRY" = 1 ] || { mkdir -p "$EV"; chmod 700 "$EV"; rm -f "$EV"/known_hosts "$EV"/known_hosts.*; }
  boot() { local c="$1"
    if [ "$PROVIDER" = azure ] && [ "$DRY" != 1 ]; then
      for i in 1 2 3 4 5 6; do ssh-keyscan -t ed25519 "$(field "$c" 2)" 2>/dev/null >> "$EV/known_hosts.$c" && [ -s "$EV/known_hosts.$c" ] && break; sleep 10; done
      [ -s "$EV/known_hosts.$c" ] || { echo "no host key for $c" >&2; return 1; }
      cat "$EV/known_hosts.$c" >> "$EV/known_hosts"; chmod 600 "$EV/known_hosts"
    fi
    cl scp "$c" "$here/scripts/ha-r09a-vm-bootstrap.sh" >/dev/null
    cl ssh "$c" "sudo NC183_USER=$RU bash /tmp/ha-r09a-vm-bootstrap.sh all" > "$([ "$DRY" = 1 ] && echo /dev/stdout || echo "$EV/bootstrap-$c.log")" 2>&1; }
  each boot
  if [ "$PROVIDER" = azure ] && [ "$DRY" != 1 ]; then rm -f "$EV"/known_hosts.*; fi
}

step_prepare() {
  # The third --node field is the etcd/peer TLS name (internal host), so the voter certificate carries it.
  run env R10_ADMISSION_MS="$ADM" "$PY" "$here/labs/ha/r10_prepare.py" prepare --root "$G" $(grp prepare-args) --state-dir /sandbox/nc182 --sandbox
}

step_dns() {
  [ "${R10_GO_DNS:-}" = 1 ] || [ "$DRY" = 1 ] || { echo "refused: R10_GO_DNS=1 required (changes public DNS)" >&2; return 4; }
  local a=() c
  for c in "${CODES[@]}"; do a+=(--id6 "$c=$(id6_of "$c")" --ip "$c=$(field "$c" 2)"); done
  run "$PY" "$here/scripts/ha-dns-godaddy.py" "${a[@]}" apply --apply
}

step_cert() {
  [ "${R10_GO_DNS:-}" = 1 ] || [ "$DRY" = 1 ] || { echo "refused: R10_GO_DNS=1 required (writes ACME TXT records)" >&2; return 4; }
  : "${R10_ACME_EMAIL:?R10_ACME_EMAIL (ACME account contact; not stored in the repo)}"
  local names="" c
  for c in "${CODES[@]}"; do names="$names${names:+,}$(dns_of "$c")"; done
  # lego's EXEC_PATH must be ONE executable, so wrap the hook; wait for DNS propagation or the TXT check sees NXDOMAIN.
  if [ "$DRY" = 1 ]; then say "+ printf wrapper -> $G/acme-hook.sh (exec python3 scripts/ha-r10-acme-hook.py)"
  else printf '#!/bin/sh\nexec python3 %s/scripts/ha-r10-acme-hook.py "$@"\n' "$here" > "$G/acme-hook.sh"; chmod 700 "$G/acme-hook.sh"; fi
  lego_one() { local c="$1" d; d="$(dns_of "$c")"
    if [ "$DRY" = 1 ]; then say "+ GODADDY_PAT=<read from ~/.openclaw/.env at run time> R10_DNS_NAMES=$names EXEC_PATH=$G/acme-hook.sh lego --accept-tos --email <R10_ACME_EMAIL> --path $G/lego-$c --dns exec --dns.propagation-wait 90s --domains $d run"; return; fi
    mkdir -p "$G/lego-$c"
    GODADDY_PAT="$("$PY" "$here/scripts/write-env.py" --get "$HOME/.openclaw/.env" GODADDY_PAT)" R10_DNS_NAMES="$names" EXEC_PATH="$G/acme-hook.sh" \
      "${LEGO:-$HOME/.openclaw/n2n/bin/lego}" --accept-tos --email "$R10_ACME_EMAIL" --path "$G/lego-$c" --dns exec --dns.propagation-wait 90s --domains "$d" run > "$EV/lego-$c.log" 2>&1; }
  each lego_one
}

step_policy_payload() {
  local guard="${R10_GUARD_DIR:?R10_GUARD_DIR (dir with the node-guard-config yaml files)}" c
  # Cross-group federation (contracts/cross-cloud-federation.md): PEER_GEN = the OTHER group's generation dir, PEER_LABEL = its label.
  PEERARGS=(); PAYARGS=()
  if [ -n "${PEER_GEN:-}" ]; then
    PEERARGS=(--peer-summary "$PEER_GEN/summary.json"); PAYARGS=(--peer-dir "$G/peer-config")
    run rm -rf "$G/peer-config"; run "$PY" "$here/labs/ha/r10_group.py" peer-config --local-root "$G" --peer-root "$PEER_GEN" --label "${PEER_LABEL:?PEER_LABEL}" --out "$G/peer-config"
  fi
  run "$PY" "$here/labs/ha/r09_workspace.py" pack --out "$G/workspace-backend.tar"
  run "$PY" "$here/labs/ha/r09_hud_pack.py" "$G/hud-source.tar"
  run mkdir -p "$G/guard" "$G/policy"; run cp "$guard"/*.yaml "$G/guard/"
  for c in "${CODES[@]}"; do
    if [ "$DRY" = 1 ]; then say "+ $(grp node-spec --code "$c" "${PEERARGS[@]}") > $EV/spec-$c.json"; else grp node-spec --code "$c" "${PEERARGS[@]}" > "$EV/spec-$c.json"; fi
    local region=unknown
    if [ "$DRY" != 1 ]; then
      if [ "$PROVIDER" = azure ]; then region="$(az vm show -g "rg-nc198-$PHASE" -n "nc198-$PHASE-$c" --query location -o tsv)"
      else region="$("$PY" -c "import r10_group as g;print(g.GCP_ZONES['$c'].rsplit('-',1)[0])")"; fi
    fi
    run "$PY" "$here/labs/ha/r09a_policy.py" render --node-spec "$EV/spec-$c.json" --out "$G/policy/out-$c"
    run "$PY" "$here/labs/ha/r09_workspace.py" render --installation-id "$(iid_of "$c")" --conversation-home /sandbox/.openclaw --out-dir "$G/workspace-$c"
    run "$PY" "$here/labs/ha/r10_payload.py" --root "$G" --code "$c" --dns "$(dns_of "$c")" --policy-dir "$G/policy/out-$c" \
      --guard-config "$G/guard/node-guard-config.yaml" --workspace-config "$G/workspace-$c/workspace.backend.json" --region "$region" "${PAYARGS[@]}"
  done
}

step_image() {
  run rm -rf "$G/image-ctx"
  run "$PY" "$here/labs/ha/r09a_image.py" context --out "$G/image-ctx" --source-tar "$G/source.tar" --source-manifest "$G/source-manifest.json" \
    --hud-tar "$G/hud-source.tar" --workspace-tar "$G/workspace-backend.tar" --require-inputs
  run tar czf "$EV/image-ctx-$GROUP.tgz" -C "$G" image-ctx
  build() { local c="$1"; cl scp "$c" "$EV/image-ctx-$GROUP.tgz" >/dev/null
    cl ssh "$c" "mkdir -p ~/ctx && tar xzf /tmp/image-ctx-$GROUP.tgz -C ~/ctx && cd ~/ctx/image-ctx && docker build -t $IMAGE . > /tmp/build.log 2>&1 && tail -1 /tmp/build.log"; }
  each build
}

step_provider() {
  local envf="${R10_ENV_FILE:-$here/.env}" yaml
  yaml='id: nc183-anthropic
display_name: NC Anthropic
description: Endpointless anthropic key provider
category: inference
credentials:
  - name: api_key
    description: Anthropic API key
    env_vars: [ANTHROPIC_API_KEY]
    required: true
    auth_style: header
    header_name: x-api-key
endpoints: []'
  prov() { local c="$1"
    # NOT live-verified in this order: r10c imported then `profile update`d with the exported resource_version. If import
    # reports the profile exists, export it, set auth_style/header_name, and `profile update` with its resource_version.
    cl ssh "$c" "export PATH=\$HOME/.local/bin:\$PATH; cat > /tmp/p.yaml <<'EOF'
$yaml
EOF
openshell provider profile import --file /tmp/p.yaml 2>&1 | tail -2"
    run env PHASE="$PHASE" PROVIDER="$PROVIDER" PTYPE=nc183-anthropic bash "$here/scripts/ha-r10-openshell-provider.sh" "$c" "$envf"; }
  for c in "${CODES[@]}"; do prov "$c"; done   # serial: the key streams over stdin, one host at a time
}

step_etcd() {
  [ "$DRY" = 1 ] || { for c in "${CODES[@]}"; do rm -rf "$EV/hostin-$c"; done; }
  stage() { local c="$1" T="$EV/hostin-$c"
    run mkdir -p "$T/etcd-voter"; run chmod 700 "$T"
    run cp "$G/bundles/$c/etcd-voter/"* "$T/etcd-voter/"; run cp "$G/bundles/$c/node.json" "$G/etcd-owned.json" "$T/"
    run tar czf "$EV/hostin-$c.tgz" -C "$T" .
    cl scp "$c" "$EV/hostin-$c.tgz" >/dev/null
    cl ssh "$c" "sudo install -d -m 700 -o $RU /var/lib/nc183 && sudo tar xzf /tmp/hostin-$c.tgz -C /var/lib/nc183 --no-same-owner 2>&1 | grep -v xattr; sudo chown -R $RU /var/lib/nc183; sudo NC183_USER=$RU bash /tmp/ha-r09a-vm-bootstrap.sh etcd 2>&1 | tail -1"; }
  # all three voters must come up together (a lone voter cannot elect)
  each stage
  health() { cl ssh "$1" "sleep 20; docker exec nc183-etcd etcdctl --endpoints=https://127.0.0.1:12379 --cacert=/pki/client-ca.crt --cert=/pki/server.crt --key=/pki/server.key endpoint health 2>&1 | tail -1"; }
  each health
}

make_recreate() { local f="$EV/recreate-nostart.sh"   # the recreate script minus its START line (no Border runs yet)
  if [ "$DRY" = 1 ]; then say "+ sed '/touch \\/sandbox\\/nc182\\/START/d' ha-r10-node-recreate.sh > $f"; else mkdir -p "$EV"; sed '/touch \/sandbox\/nc182\/START/d' "$here/scripts/ha-r10-node-recreate.sh" > "$f"; fi; }
recreate_nostart() { # <code>: node tarball + policy + the START-less recreate script, then run it on the VM
  local c="$1" f="$EV/recreate-nostart.sh"
  cl scp "$c" "$G/node-$c.tar" "$G/policy/out-$c/policy.yaml" "$f" >/dev/null
  cl ssh "$c" "rm -rf ~/stage; mkdir -p ~/stage && tar xf /tmp/node-$c.tar -C ~/stage 2>&1 | grep -v xattr; bash /tmp/recreate-nostart.sh $(field "$c" 3) $(policy_sha "$c") $IMAGE 2>&1 | tail -3"
}
step_sandbox() { make_recreate; each recreate_nostart; }

step_authority() {
  local c="${CODES[0]}"
  cl ssh "$c" "export PATH=\$HOME/.local/bin:\$PATH; timeout 170 openshell sandbox exec -n netclaw-node -- env NC_STATE=/sandbox/nc182 NC_ETCD_HOST=$(etcd_host "$c") NC_ETCD_PORT=12379 /opt/nc182/venv/bin/python -B /sandbox/nc182/bin/etcd_bootstrap.py 2>&1 | tail -3"
}

step_enroll_members() {
  # Enrollment needs every Border stopped (leases expired). Members: $EV/members/<name>.json (identity/member.json copies).
  local c0="${CODES[0]}" files=()
  [ "$DRY" = 1 ] && files=("$EV/members/example.json") || { shopt -s nullglob; files=("$EV"/members/*.json); }
  [ "${#files[@]}" -gt 0 ] || { echo "no member files in $EV/members" >&2; return 2; }
  make_recreate; each recreate_nostart                   # stops every Border (sandbox recreated without START)
  cl scp "$c0" "$here/labs/ha/r09_vm_enroll.py" "$G/etcd-owned.json" "${files[@]}" >/dev/null
  local script="export PATH=\$HOME/.local/bin:\$PATH; openshell sandbox upload netclaw-node /tmp/r09_vm_enroll.py /sandbox/nc182/bin; for m in $(printf '/tmp/%s ' "${files[@]##*/}"); do cp \$m /tmp/member.json; openshell sandbox upload netclaw-node /tmp/member.json /sandbox/nc182; openshell sandbox upload netclaw-node /tmp/etcd-owned.json /sandbox/nc182; sleep 25; openshell sandbox exec -n netclaw-node -- env NC_STATE=/sandbox/nc182 /opt/nc182/venv/bin/python -B /sandbox/nc182/bin/r09_vm_enroll.py /sandbox/nc182/member.json 2>&1 | tail -1; done; openshell sandbox exec -n netclaw-node -- rm -f /sandbox/nc182/etcd-owned.json /sandbox/nc182/member.json"
  cl ssh "$c0" "$script"
  if [ "$DRY" != 1 ]; then mkdir -p "$EV/members-done"; mv "${files[@]}" "$EV/members-done/"; fi   # re-enrolling is idempotent but slow (25 s each)
}

step_start() {
  local c
  for c in "${CODES[@]}"; do   # nne1 first; 12-15 s apart so each election settles
    cl ssh "$c" "export PATH=\$HOME/.local/bin:\$PATH; openshell sandbox exec -n netclaw-node -- bash -c 'rm -rf /sandbox/nc182/etcd-bootstrap; touch /sandbox/nc182/START'"
    [ "$DRY" = 1 ] || sleep 15
  done
  step_status wait
}

step_status() {
  local c d code
  for c in "${CODES[@]}"; do d="$(dns_of "$c")"
    if [ "$DRY" = 1 ]; then say "+ curl -s -m 10 https://$d/api/hud/posture   # $c"; continue; fi
    for i in $(seq 1 "$([ "${1:-}" = wait ] && echo 30 || echo 1)"); do
      code="$(curl -s -m 10 -o "$EV/posture-$c.json" -w '%{http_code}' "https://$d/api/hud/posture" || true)"; [ "$code" = 200 ] && break; sleep 8; done
    say "$c $d posture=$code"
  done
}

step_peer_fw() { # open tcp/7445 ONLY from the other group's three public /32s (PEER_NODES = the other group's nodes.txt)
  local src="" line; [ -s "${PEER_NODES:-/nonexistent}" ] || { [ "$DRY" = 1 ] || { echo "PEER_NODES (other group's nodes.txt) required" >&2; return 2; }; }
  while read -r _ ip _; do [ -n "$ip" ] && src="$src${src:+ }$ip/32"; done < <([ -s "${PEER_NODES:-/nonexistent}" ] && cat "$PEER_NODES" || printf 'x 192.0.2.1 y\n')
  if [ "$PROVIDER" = azure ]; then
    for c in "${CODES[@]}"; do run az network nsg rule create -g "rg-nc198-$PHASE" --nsg-name "nsg-nc198-$PHASE-$c" -n fed7445 --priority 130 --access Allow --protocol Tcp --destination-port-ranges 7445 --source-address-prefixes $src --output none; done
  else
    run gcloud compute firewall-rules create "$GCP_VM_PREFIX-allow-fed" --project="$GCP_PROJECT" --network="${GCP_NETWORK:-default}" --direction=INGRESS --allow=tcp:7445 --source-ranges="${src// /,}" --target-tags="nc198-$PHASE" --description="netclaw-spec=198 run-id=$RUN" --quiet
  fi
}

# --- live-test steps (takeover and rotation); each takes one node code -------------------------------------------------------
step_kill_node() { # <code>: take that Border down (runner killed inside its sandbox; sandbox then exits)
  local c="${args[1]:?node code}"
  cl ssh "$c" "export PATH=\$HOME/.local/bin:\$PATH; openshell sandbox exec -n netclaw-node -- pkill -f r10_node_run.py; echo killed $c"
}
step_start_node() { # <code>: bring a stopped Border back (a stopped sandbox must be recreated, then START); allow ~3 min for posture 200
  local c="${args[1]:?node code}"; make_recreate; recreate_nostart "$c"
  cl ssh "$c" "export PATH=\$HOME/.local/bin:\$PATH; openshell sandbox exec -n netclaw-node -- bash -c 'rm -rf /sandbox/nc182/etcd-bootstrap; touch /sandbox/nc182/START'"
  [ "$DRY" = 1 ] || { for i in $(seq 1 30); do code="$(curl -s -m 10 -o /dev/null -w '%{http_code}' "https://$(dns_of "$c")/api/hud/posture" || true)"; [ "$code" = 200 ] && break; sleep 10; done; say "$c posture=$code"; }
}
step_rotate() { # <code>: TLS certificate rotation of one Border: renew with lego, rebuild that node's payload, restart it, compare serials
  local c="${args[1]:?node code}" d old new
  [ "${R10_GO_DNS:-}" = 1 ] || [ "$DRY" = 1 ] || { echo "refused: R10_GO_DNS=1 required (ACME TXT records)" >&2; return 4; }
  d="$(dns_of "$c")"
  old="$(echo | openssl s_client -connect "$d:443" -servername "$d" 2>/dev/null | openssl x509 -noout -serial 2>/dev/null || true)"
  local names="" k; for k in "${CODES[@]}"; do names="$names${names:+,}$(dns_of "$k")"; done
  if [ "$DRY" = 1 ]; then say "+ lego renew --days 100 --path $G/lego-$c --dns exec ...; r10_payload.py --code $c; recreate + START $c; compare serials"; return; fi
  GODADDY_PAT="$("$PY" "$here/scripts/write-env.py" --get "$HOME/.openclaw/.env" GODADDY_PAT)" R10_DNS_NAMES="$names" EXEC_PATH="$G/acme-hook.sh" \
    "${LEGO:-$HOME/.openclaw/n2n/bin/lego}" --accept-tos --email "${R10_ACME_EMAIL:?R10_ACME_EMAIL}" --path "$G/lego-$c" --dns exec --dns.propagation-wait 90s --domains "$d" renew --days 100 > "$EV/lego-renew-$c.log" 2>&1 || { echo "renew failed (see $EV/lego-renew-$c.log)"; return 1; }
  "$PY" "$here/labs/ha/r10_payload.py" --root "$G" --code "$c" --dns "$d" --policy-dir "$G/policy/out-$c" \
    --guard-config "$G/guard/node-guard-config.yaml" --workspace-config "$G/workspace-$c/workspace.backend.json" >/dev/null
  args=("" "$c"); step_start_node
  new="$(echo | openssl s_client -connect "$d:443" -servername "$d" 2>/dev/null | openssl x509 -noout -serial 2>/dev/null || true)"
  say "rotate $c: serial before [$old] after [$new] -> $([ -n "$new" ] && [ "$old" != "$new" ] && echo ROTATED || echo UNCHANGED)"
}

declare -F "step_${step//-/_}" >/dev/null || { echo "unknown step: $step (try: plan)" >&2; exit 2; }
"step_${step//-/_}" "${args[@]:1}"
