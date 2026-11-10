#!/usr/bin/env bash
# R09 (spec 182): full-workspace backend for ONE HA Border VM. NOT RUN by the agent; deploy only on owner approval.
# See specs/182-multi-region-ha-borders/workspace-plan.md. Run as root on a gen-N nc182-border-* VM.
#
#   ha-r09-vm-workspace.sh install     users, pinned OpenClaw, frozen backend source (+ npm ci), firewall unit
#   ha-r09-vm-workspace.sh configure   conversation home, workspace configs, token env, systemd units
#   ha-r09-vm-workspace.sh start       gateway then backend HUD (needs /etc/nc182/provider.env placed by the owner step)
#
# Inputs in /tmp (scp'd): workspace-backend.tar, workspace.edge.json, workspace.backend.json, openclaw.json
# (from `labs/ha/r09_workspace.py render` and `pack`). No secret value is created in or read from the repo; the gateway
# token is generated here and never printed; the provider key is placed by scripts/ha-r09-place-provider-key.sh.
set -euo pipefail

OPENCLAW_VERSION="${OPENCLAW_VERSION:-2026.7.1-2}"      # the version owner-qualified in R04a; override only with approval
WS_USER=nc182ws; WS_STATE=/var/lib/nc182ws; WS_HOME=$WS_STATE/home
EDGE_USER=nc182; EDGE_STATE=/var/lib/nc182
NODE_DIR=/opt/nc182/node/bin
BACKEND_ROOT=/opt/nc182/netclaw; OC_PREFIX=/opt/nc182/openclaw
UPSTREAM_PORT=3001; GATEWAY_PORT=18789

need_root() { [ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 2; }; }

install_all() {
  id "$WS_USER" >/dev/null 2>&1 || useradd --system --home-dir "$WS_STATE" --shell /usr/sbin/nologin "$WS_USER"
  install -d -m 0700 -o "$WS_USER" -g "$WS_USER" "$WS_STATE"
  export PATH="$NODE_DIR:/usr/bin:/bin"

  # Pinned OpenClaw (root-owned, read-only afterwards). Scripts disabled; engines require Node 24.15+ (VM has 24.x).
  if [ ! -x "$OC_PREFIX/node_modules/.bin/openclaw" ]; then
    install -d -m 0755 "$OC_PREFIX"
    npm install --prefix "$OC_PREFIX" --ignore-scripts --no-audit --no-fund "openclaw@$OPENCLAW_VERSION" >/dev/null
    chown -R root:root "$OC_PREFIX"; chmod -R go-w "$OC_PREFIX"
  fi

  # Frozen backend source tree (git archive of a pinned commit + built dist), root-owned, read-only to the service.
  if [ ! -d "$BACKEND_ROOT/ui/netclaw-visual/node_modules" ]; then
    rm -rf "$BACKEND_ROOT"; install -d -m 0755 "$BACKEND_ROOT"
    tar -xf /tmp/workspace-backend.tar -C "$BACKEND_ROOT" --no-same-owner
    (cd "$BACKEND_ROOT/ui/netclaw-visual" && npm ci --omit=dev --ignore-scripts --no-audit --no-fund >/dev/null)
    chown -R root:root "$BACKEND_ROOT"; chmod -R go-w "$BACKEND_ROOT"
  fi

  # Keep the conversation UID away from the cloud metadata server (service-account tokens) and from the Border's state.
  cat >/etc/systemd/system/nc182-ws-fw.service <<UNIT
[Unit]
Description=nc182 conversation UID: deny metadata server
After=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'iptables -C OUTPUT -d 169.254.169.254 -m owner --uid-owner $WS_USER -j REJECT 2>/dev/null || iptables -I OUTPUT -d 169.254.169.254 -m owner --uid-owner $WS_USER -j REJECT; for proto in udp tcp; do iptables -C OUTPUT -d 169.254.169.254 -p \$proto --dport 53 -m owner --uid-owner $WS_USER -j ACCEPT 2>/dev/null || iptables -I OUTPUT 1 -d 169.254.169.254 -p \$proto --dport 53 -m owner --uid-owner $WS_USER -j ACCEPT; done'
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload; systemctl enable --now nc182-ws-fw.service >/dev/null 2>&1
  echo "install ok: openclaw $("$OC_PREFIX/node_modules/.bin/openclaw" --version 2>/dev/null | head -1)"
}

configure_all() {
  # Conversation home is a separate 0700 tree owned by the conversation UID; no `workspace/skills` child so the HUD
  # falls back to the frozen source tree's skills (read-only).
  install -d -m 0700 -o "$WS_USER" -g "$WS_USER" "$WS_HOME" "$WS_HOME/workspace" "$WS_HOME/netclaw-hud"
  install -m 0600 -o "$WS_USER" -g "$WS_USER" /tmp/openclaw.json "$WS_HOME/openclaw.json"
  install -m 0600 -o "$WS_USER" -g "$WS_USER" /tmp/workspace.backend.json "$WS_STATE/workspace.json"
  # Edge copy: byte-identical, owned by the Border (edge) UID, read by hud_ingress_r09.mjs and pinned by sha256.
  install -d -m 0700 -o "$EDGE_USER" -g "$EDGE_USER" "$EDGE_STATE/workspace"
  install -m 0600 -o "$EDGE_USER" -g "$EDGE_USER" /tmp/workspace.edge.json "$EDGE_STATE/workspace/workspace.json"
  cmp -s "$EDGE_STATE/workspace/workspace.json" "$WS_STATE/workspace.json" || { echo "workspace copies differ" >&2; exit 1; }

  # Gateway token: generated here, never printed. Both units read it; only the gateway also reads provider.env.
  install -d -m 0750 -o root -g root /etc/nc182
  if [ ! -f /etc/nc182/ws-token.env ]; then
    umask 077; printf 'OPENCLAW_GATEWAY_TOKEN=%s\n' "$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')" >/etc/nc182/ws-token.env
  fi
  chmod 0600 /etc/nc182/ws-token.env; chown root:root /etc/nc182/ws-token.env

  local HARDEN="NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=$WS_STATE
PrivateTmp=yes
ProtectHome=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes"
  local COMMON="HOME=$WS_STATE
OPENCLAW_HOME=$WS_STATE
OPENCLAW_STATE_DIR=$WS_HOME
OPENCLAW_CONFIG_PATH=$WS_HOME/openclaw.json
PATH=$OC_PREFIX/node_modules/.bin:$NODE_DIR:/usr/bin:/bin"
  cat >/etc/systemd/system/nc182-gateway.service <<UNIT
[Unit]
Description=nc182 OpenClaw conversation gateway (loopback only; holds the provider key)
After=network-online.target
Wants=network-online.target
[Service]
User=$WS_USER
WorkingDirectory=$WS_HOME
$(printf '%s\n' "$COMMON" | sed 's/^/Environment=/')
EnvironmentFile=/etc/nc182/ws-token.env
EnvironmentFile=/etc/nc182/provider.env
ExecStart=$OC_PREFIX/node_modules/.bin/openclaw gateway --port $GATEWAY_PORT
Restart=on-failure
RestartSec=5
$HARDEN
[Install]
WantedBy=multi-user.target
UNIT
  cat >/etc/systemd/system/nc182-wshud.service <<UNIT
[Unit]
Description=nc182 NetClaw HUD workspace backend (loopback upstream of the protected Border HUD)
After=nc182-gateway.service
[Service]
User=$WS_USER
WorkingDirectory=$BACKEND_ROOT/ui/netclaw-visual
$(printf '%s\n' "$COMMON" | sed 's/^/Environment=/')
Environment=NETCLAW_OPEN_LAB_WORKSPACE_CONFIG=$WS_STATE/workspace.json
Environment=HUD_PORT=$UPSTREAM_PORT
Environment=HUD_UI_PORT=3000
EnvironmentFile=/etc/nc182/ws-token.env
ExecStart=$NODE_DIR/node server.js
Restart=on-failure
RestartSec=5
$HARDEN
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  echo "configure ok (edge ingress must be re-prepared with the workspace entry: r09_vm_hud.py)"
}

start_all() {
  [ -s /etc/nc182/provider.env ] || { echo "provider key not placed: run scripts/ha-r09-place-provider-key.sh (owner step)" >&2; exit 3; }
  systemctl enable --now nc182-gateway.service; sleep 8
  systemctl enable --now nc182-wshud.service; sleep 8
  systemctl is-active nc182-gateway nc182-wshud
  curl -s -m 5 "http://127.0.0.1:$UPSTREAM_PORT/api/runtime" | head -c 300; echo
}

need_root
case "${1:-}" in
  install) install_all ;;
  configure) configure_all ;;
  start) start_all ;;
  *) echo "usage: $0 install|configure|start" >&2; exit 2 ;;
esac
