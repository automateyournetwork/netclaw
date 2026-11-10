#!/usr/bin/env bash
# R09A (spec 183) node bootstrap. Run as root on a fresh Ubuntu 24.04 LTS amd64 nc183-* VM. Idempotent.
#
#   sudo NC183_USER=<operator> bash ha-r09a-vm-bootstrap.sh [all|base|openshell|defenseclaw|metadata|etcd|check]
#
# Facts this encodes (all verified live on a throwaway VM, see specs/183-openshell-defenseclaw-gcp/research.md):
#  - OpenShell needs Landlock ABI >= 3 (Ubuntu 24.04 GCE: kernel 7.0, ABI 8; Debian 12 / kernel 6.1 is unsuitable) and Docker >= 28.
#  - OpenShell 0.1.7 installs as a Debian package; its gateway is a *user* service. The upstream installer exits non-zero on a
#    headless host because the user service cannot start before linger, so success is judged by the installed package version.
#  - The gateway needs OPENSHELL_COMPUTE_DRIVER=docker (auto-detect failed), the operator in the docker group (restart user@UID),
#    and `openshell gateway add https://127.0.0.1:17670 --local`.
#  - DefenseClaw 1.0.4 installs from the checksum-verified pinned release installer on x86_64.
#  - Metadata server (169.254.169.254) is blocked for containers; DNS (UDP/TCP 53) stays allowed because GCE resolves via it.
# No secret is read, written or printed here.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

STAGE="${1:-all}"
STATE=/var/lib/nc183
OPT=/opt/nc183
OPERATOR="${NC183_USER:-${SUDO_USER:-}}"
OPENSHELL_PIN_TAG="${OPENSHELL_VERSION:-v0.1.7}"
OPENSHELL_EXPECT="${OPENSHELL_EXPECT:-0.1.7}"
DEFENSECLAW_VERSION="${DEFENSECLAW_VERSION:-1.0.4}"
OPENCLAW_VERSION="${OPENCLAW_VERSION:-2026.7.1-2}"
DOCKER_MIN_MAJOR=28
GATEWAY_ENDPOINT=https://127.0.0.1:17670
ETCD_IMAGE="${ETCD_IMAGE:-gcr.io/etcd-development/etcd:v3.6.16}"

log() { printf '[r09a-bootstrap] %s\n' "$*" >&2; }
die() { printf '[r09a-bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run as root"
[ -n "$OPERATOR" ] && id "$OPERATOR" >/dev/null 2>&1 || die "set NC183_USER to an existing non-root operator account"
[ "$OPERATOR" != root ] || die "the OpenShell gateway runs as a user service; use a non-root operator"
OP_UID="$(id -u "$OPERATOR")"; OP_HOME="$(getent passwd "$OPERATOR" | cut -d: -f6)"
as_op() { sudo -u "$OPERATOR" -H env XDG_RUNTIME_DIR="/run/user/$OP_UID" PATH="$OPT/node/bin:$OP_HOME/oc/node_modules/.bin:$OP_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" "$@"; }

stage_base() {
  . /etc/os-release
  [ "${ID:-}" = ubuntu ] && [ "${VERSION_ID:-}" = "24.04" ] || die "Ubuntu 24.04 LTS required (found ${PRETTY_NAME:-unknown}); Landlock ABI 3+ is the gate"
  [ "$(uname -m)" = x86_64 ] || die "amd64 required (DefenseClaw/guard images are qualified for x86_64 here)"
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl iptables jq tar xz-utils python3 chrony >/dev/null
  systemctl enable --now chrony >/dev/null 2>&1 || true
  # Landlock ABI check (syscall 444, LANDLOCK_CREATE_RULESET_VERSION): must be >= 3
  abi="$(python3 - <<'PY'
import ctypes
libc = ctypes.CDLL(None, use_errno=True)
print(libc.syscall(444, None, 0, 1))
PY
)"
  [ "$abi" -ge 3 ] 2>/dev/null || die "Landlock ABI $abi < 3 on kernel $(uname -r)"
  log "kernel $(uname -r), Landlock ABI $abi"
  install -d -m 0755 "$OPT"; install -d -m 0750 -o "$OPERATOR" -g "$OPERATOR" "$STATE"
  # Docker >= 28 from Docker's own installer (the Docker snap and Ubuntu's docker.io are not compatible/too old).
  major="$(docker --version 2>/dev/null | sed -E 's/Docker version ([0-9]+).*/\1/' || true)"
  if ! [ "${major:-0}" -ge "$DOCKER_MIN_MAJOR" ] 2>/dev/null; then
    log "installing Docker (found: ${major:-none}, need >= $DOCKER_MIN_MAJOR)"
    curl -fsSL --proto '=https' --tlsv1.2 https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh >/tmp/docker-install.log 2>&1 || { tail -5 /tmp/docker-install.log >&2; die "docker install failed"; }
  fi
  systemctl enable --now docker >/dev/null 2>&1
  major="$(docker --version | sed -E 's/Docker version ([0-9]+).*/\1/')"
  [ "$major" -ge "$DOCKER_MIN_MAJOR" ] || die "Docker $major < $DOCKER_MIN_MAJOR"
  id -nG "$OPERATOR" | tr ' ' '\n' | grep -qx docker || usermod -aG docker "$OPERATOR"
  loginctl enable-linger "$OPERATOR"
  # restart the user manager so the docker group and linger take effect for user services
  systemctl restart "user@${OP_UID}.service"
  sleep 3
}

stage_openshell() {
  if [ "$(dpkg-query -W -f='${Version}' openshell 2>/dev/null | cut -d- -f1)" != "$OPENSHELL_EXPECT" ]; then
    dir="$(mktemp -d)"; chmod 700 "$dir"
    curl -fsSL --proto '=https' --tlsv1.2 https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh -o "$dir/install.sh"
    # The installer exits non-zero on headless hosts (user service cannot start before linger): judge by the package version.
    OPENSHELL_VERSION="$OPENSHELL_PIN_TAG" sh "$dir/install.sh" >/tmp/openshell-install.log 2>&1 || true
    if [ "$(dpkg-query -W -f='${Version}' openshell 2>/dev/null | cut -d- -f1)" != "$OPENSHELL_EXPECT" ]; then
      log "pinned tag '$OPENSHELL_PIN_TAG' did not yield $OPENSHELL_EXPECT; retrying with the latest tagged release"
      sh "$dir/install.sh" >/tmp/openshell-install.log 2>&1 || true
    fi
    rm -rf "$dir"
  fi
  have="$(dpkg-query -W -f='${Version}' openshell 2>/dev/null | cut -d- -f1 || true)"
  [ "$have" = "$OPENSHELL_EXPECT" ] || die "OpenShell $have installed, expected $OPENSHELL_EXPECT (see /tmp/openshell-install.log)"
  install -d -m 0700 -o "$OPERATOR" -g "$OPERATOR" "$OP_HOME/.config/openshell"
  printf 'OPENSHELL_COMPUTE_DRIVER=docker\n' >"$OP_HOME/.config/openshell/gateway.env"
  chown "$OPERATOR:$OPERATOR" "$OP_HOME/.config/openshell/gateway.env"; chmod 600 "$OP_HOME/.config/openshell/gateway.env"
  as_op systemctl --user daemon-reload
  as_op systemctl --user enable openshell-gateway >/dev/null 2>&1 || true
  as_op systemctl --user restart openshell-gateway
  for _ in $(seq 1 30); do as_op systemctl --user is-active openshell-gateway >/dev/null 2>&1 && break; sleep 2; done
  as_op systemctl --user is-active openshell-gateway >/dev/null 2>&1 || die "openshell-gateway not active (journalctl --user -u openshell-gateway)"
  as_op openshell doctor check >/dev/null 2>&1 || die "openshell doctor check failed"
  as_op openshell gateway add "$GATEWAY_ENDPOINT" --local --name node >/dev/null 2>&1 || true
  as_op openshell gateway select node >/dev/null
}

stage_node_and_openclaw() {
  [ -x "$OPT/node/bin/node" ] && return 0
  base=https://nodejs.org/dist/latest-v24.x
  line="$(curl -fsSL --proto '=https' --tlsv1.2 "$base/SHASUMS256.txt" | grep 'linux-x64.tar.xz$')"
  file="$(echo "$line" | awk '{print $2}')"; want="$(echo "$line" | awk '{print $1}')"
  curl -fsSL --proto '=https' --tlsv1.2 "$base/$file" -o /tmp/node.tar.xz
  echo "$want  /tmp/node.tar.xz" | sha256sum -c - >/dev/null || die "node checksum mismatch"
  install -d -m 0755 "$OPT/node"; tar -xJf /tmp/node.tar.xz -C "$OPT/node" --strip-components=1; rm -f /tmp/node.tar.xz
}

stage_defenseclaw() {
  stage_node_and_openclaw
  if [ ! -x "$OP_HOME/oc/node_modules/.bin/openclaw" ]; then
    as_op mkdir -p "$OP_HOME/oc"
    as_op npm install --prefix "$OP_HOME/oc" --ignore-scripts --no-audit --no-fund "openclaw@$OPENCLAW_VERSION" >/tmp/oc.log 2>&1 || die "openclaw install failed"
  fi
  if ! as_op defenseclaw --version 2>/dev/null | grep -q "$DEFENSECLAW_VERSION"; then
    dir="$(mktemp -d)"; chmod 755 "$dir"
    base="https://github.com/cisco-ai-defense/defenseclaw/releases/download/$DEFENSECLAW_VERSION"
    curl -fsSL --proto '=https' --tlsv1.2 -o "$dir/install.sh" "$base/install.sh"
    curl -fsSL --proto '=https' --tlsv1.2 -o "$dir/checksums.txt" "$base/checksums.txt"
    (cd "$dir" && grep -E '[[:space:]]\*?install\.sh$' checksums.txt | sha256sum -c -) || die "DefenseClaw installer checksum mismatch"
    chown -R "$OPERATOR:$OPERATOR" "$dir"
    as_op bash "$dir/install.sh" --yes --connector openclaw >/tmp/dc-install.log 2>&1 || { tail -5 /tmp/dc-install.log >&2; die "DefenseClaw install failed"; }
    rm -rf "$dir"
  fi
  as_op defenseclaw --version 2>/dev/null | grep -q "$DEFENSECLAW_VERSION" || die "DefenseClaw $DEFENSECLAW_VERSION not found after install"
  as_op defenseclaw init --connector openclaw --non-interactive --yes --scanner-mode local >/tmp/dc-init.log 2>&1 || true
  as_op defenseclaw setup guardrail --connector openclaw --mode action --scanner-mode local \
        --detection-strategy regex_only --non-interactive --no-restart >/tmp/dc-guardrail.log 2>&1 \
        || die "defenseclaw setup guardrail failed (see /tmp/dc-guardrail.log)"
  # The guard capability token and the qualified R04A config are applied by the node deploy step, not here.
}

stage_metadata() {
  cat >/etc/systemd/system/nc183-metadata-block.service <<'UNIT'
[Unit]
Description=nc183: block the cloud metadata server for containers (DNS on port 53 stays open)
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'iptables -N DOCKER-USER 2>/dev/null || true; for p in udp tcp; do iptables -C DOCKER-USER -d 169.254.169.254 -p $p --dport 53 -j ACCEPT 2>/dev/null || iptables -I DOCKER-USER 1 -d 169.254.169.254 -p $p --dport 53 -j ACCEPT; done; iptables -C DOCKER-USER -d 169.254.169.254 -j REJECT 2>/dev/null || iptables -A DOCKER-USER -d 169.254.169.254 -j REJECT'
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload; systemctl enable --now nc183-metadata-block.service >/dev/null 2>&1
  iptables -C DOCKER-USER -d 169.254.169.254 -j REJECT 2>/dev/null || die "metadata block rule missing"
}

stage_etcd() {
  # Voter (Border node) or witness (no Border). Inputs placed by the deploy step: $STATE/etcd-owned.json, node.json, etcd-voter/*.
  [ -s "$STATE/etcd-owned.json" ] && [ -s "$STATE/node.json" ] && [ -d "$STATE/etcd-voter" ] || { log "etcd inputs not placed yet; skipping etcd"; return 0; }
  internal="$(jq -r .internal "$STATE/node.json")"; idx="$(jq -r .index "$STATE/node.json")"
  cluster="$(jq -r '.peers | join(",")' "$STATE/etcd-owned.json")"; name="$(jq -r .name "$STATE/etcd-owned.json")"
  hb="$(jq -r .heartbeat_ms "$STATE/etcd-owned.json")"; el="$(jq -r .election_ms "$STATE/etcd-owned.json")"
  install -d -m 0700 -o "$OPERATOR" -g "$OPERATOR" "$STATE/etcd-data"
  uid="$OP_UID"; gid="$(id -g "$OPERATOR")"
  docker rm -f nc183-etcd >/dev/null 2>&1 || true
  docker run -d --name nc183-etcd --restart unless-stopped --network host \
    --label netclaw.spec=183 --label "netclaw.owner=$name" \
    --user "$uid:$gid" --memory 1g --cap-drop ALL --security-opt no-new-privileges -e GOMEMLIMIT=768MiB \
    -v "$STATE/etcd-voter:/pki:ro" -v "$STATE/etcd-data:/data" \
    "$ETCD_IMAGE" /usr/local/bin/etcd --name "v$idx" --data-dir /data \
    --listen-client-urls "https://$internal:2379,https://127.0.0.1:2379" --advertise-client-urls "https://$internal:2379" \
    --listen-peer-urls "https://$internal:2380" --initial-advertise-peer-urls "https://$internal:2380" \
    --initial-cluster "$cluster" --initial-cluster-token "$name" --initial-cluster-state new \
    --cert-file /pki/server.crt --key-file /pki/server.key --trusted-ca-file /pki/client-ca.crt --client-cert-auth=true \
    --peer-cert-file /pki/peer.crt --peer-key-file /pki/peer.key --peer-trusted-ca-file /pki/peer-ca.crt --peer-client-cert-auth=true \
    --tls-min-version=TLS1.3 --heartbeat-interval "$hb" --election-timeout "$el" \
    --quota-backend-bytes 134217728 --auto-compaction-mode periodic --auto-compaction-retention 1m --log-level warn >/dev/null
  sleep 2
  docker ps --filter name=nc183-etcd --format '{{.Names}} {{.Status}}'
}

stage_check() {
  log "self-check"
  printf 'os:        %s\n' "$(. /etc/os-release; echo "$PRETTY_NAME")"
  printf 'kernel:    %s\n' "$(uname -r)"
  printf 'docker:    %s\n' "$(docker --version)"
  printf 'openshell: %s\n' "$(as_op openshell --version 2>&1 | head -1)"
  printf 'gateway:   %s\n' "$(as_op systemctl --user is-active openshell-gateway 2>&1)"
  printf 'defenseclaw: %s\n' "$(as_op defenseclaw --version 2>&1 | head -1)"
  printf 'openclaw:  %s\n' "$(as_op openclaw --version 2>&1 | head -1)"
  printf 'metadata block: %s\n' "$(iptables -C DOCKER-USER -d 169.254.169.254 -j REJECT 2>/dev/null && echo present || echo MISSING)"
  printf 'memory:    %s\n' "$(free -m | awk 'NR==2{print $2" MB total, "$7" MB available"}')"
  echo "--- openshell status"; as_op openshell status 2>&1 | head -12
}

case "$STAGE" in
  all) stage_base; stage_openshell; stage_defenseclaw; stage_metadata; stage_etcd; stage_check ;;
  base) stage_base ;;
  openshell) stage_openshell ;;
  defenseclaw) stage_defenseclaw ;;
  metadata) stage_metadata ;;
  etcd) stage_etcd ;;
  check) stage_check ;;
  *) die "usage: $0 [all|base|openshell|defenseclaw|metadata|etcd|check]" ;;
esac
