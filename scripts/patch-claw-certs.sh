#!/usr/bin/env bash
# Single-command claw-certification upgrade for an EXISTING claw (feature 060).
#
#   scripts/patch-claw-certs.sh [--domain <name>] [--dns-provider <id>] [--enforce] [--yes]
#
# Idempotent and state-preserving: it pulls the release, runs the additive
# schema migration, generates this claw's credential + risk CA, turns on secured
# channels, and reports posture. Your peers, consent records, grants, members,
# tasks, and audit history are untouched (asserted by before/after counts).
#
# It does NOT require your peers to upgrade at the same time — but per the design,
# an unpatched peer cannot federate until it also runs this. Channels to already-
# patched peers resume automatically.
set -euo pipefail

REPO="${NETCLAW_REPO:-$HOME/netclaw}"
DB="$HOME/.openclaw/n2n/federation.db"
DOMAIN=""; PROVIDER=""; ENFORCE="on"; ASSUME_YES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --dns-provider) PROVIDER="$2"; shift 2 ;;
    --enforce) ENFORCE="enforce"; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

say() { printf '\033[0;36m[claw-certs]\033[0m %s\n' "$*"; }

# --- state counts BEFORE (integrity check) ---
counts() {
  python3 - "$DB" <<'PY'
import sqlite3, sys, json
db = sys.argv[1]
try:
    c = sqlite3.connect(db)
    out = {}
    for t in ("federation_peer", "consent_record", "invocation_grant", "member",
              "delegated_task", "remote_invocation_record"):
        try:
            out[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.OperationalError:
            out[t] = 0
    print(json.dumps(out))
except Exception:
    print("{}")
PY
}
BEFORE="$(counts)"
say "state before: $BEFORE"

# --- 1. pull the release ---
if [ -d "$REPO/.git" ]; then
  say "updating repo at $REPO"
  git -C "$REPO" pull --ff-only || say "WARN: git pull skipped (dirty tree or offline)"
fi

# --- 2. lego (only needed for the domain-verified path) ---
if [ -n "$DOMAIN" ]; then
  bash "$REPO/scripts/lib/fetch-lego.sh"
fi

# --- 3. migrate schema + generate credentials (opening the manager runs the
#        additive v3 migration; RiskManager.ensure_risk_ca creates the CA) ---
say "migrating federation.db (additive) + generating credentials"
python3 - "$REPO" <<'PY'
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], "mcp-servers", "protocol-mcp"))
from bgp.federation.manager import FederationManager
from bgp.federation.risk import RiskManager
from bgp.federation import certs
m = FederationManager()                      # runs schema migration v3
certs.keys_dir()                             # ensure keys/ layout
rm = RiskManager(m)
# Host credential (pinned model) — created on first channel too, but do it now.
kd = certs.keys_dir()
hc = kd / "host" / "host.crt"
if not hc.exists():
    cp, kp = certs.create_self_signed(rm.self_member_id() or "netclaw-claw")
    hc.write_text(cp); certs._write_secret(kd / "host" / "host.key", kp)
if rm.is_border():
    rm.ensure_risk_ca(); rm.hub_credential()
    print("risk CA + hub credential ready")
m.close()
print("migration + credentials done")
PY

# --- 4. env: turn on secured channels ---
# IMPORTANT: the systemd --user mesh daemon reads its own EnvironmentFile (feature
# 057, ~/.openclaw/mesh.systemd.env), NOT ~/.openclaw/.env — so cert config MUST
# go there or the running daemon never sees N2N_CERT_MODE. Detect the unit's
# EnvironmentFile; fall back to mesh.systemd.env, then to ~/.openclaw/.env for a
# non-systemd (dev) claw.
ENVF="$(systemctl --user cat netclaw-mesh.service 2>/dev/null \
        | sed -n 's/^EnvironmentFile=-\{0,1\}//p' | head -1)"
[ -z "$ENVF" ] && ENVF="$HOME/.openclaw/mesh.systemd.env"
[ -f "$ENVF" ] || ENVF="$HOME/.openclaw/.env"
touch "$ENVF"
set_env() { grep -q "^$1=" "$ENVF" && sed -i "s|^$1=.*|$1=$2|" "$ENVF" || echo "$1=$2" >> "$ENVF"; }
set_env N2N_CERT_MODE "$ENFORCE"
[ -n "$DOMAIN" ] && set_env N2N_CLAW_DOMAIN "$DOMAIN"
[ -n "$PROVIDER" ] && set_env N2N_ACME_DNS_PROVIDER "$PROVIDER"
say "set N2N_CERT_MODE=$ENFORCE${DOMAIN:+, N2N_CLAW_DOMAIN=$DOMAIN} in $ENVF"

# --- 5. restart services in dependency order (feature 057) ---
if command -v systemctl >/dev/null && systemctl --user list-units >/dev/null 2>&1; then
  say "restarting services (gateway -> mesh -> members)"
  systemctl --user restart openclaw-gateway.service 2>/dev/null || true
  systemctl --user restart netclaw-mesh.service 2>/dev/null || true
  for u in $(systemctl --user list-units --type=service --all --no-legend 'netclaw-member-*' 2>/dev/null | awk '{print $1}'); do
    systemctl --user restart "$u" 2>/dev/null || true
  done
else
  say "no systemd --user manager — restart the daemon manually to apply"
fi

# --- 6. integrity check + posture ---
AFTER="$(counts)"
say "state after:  $AFTER"
if [ "$BEFORE" != "$AFTER" ]; then
  echo "ERROR: federation state counts changed — investigate before federating!" >&2
  exit 2
fi
say "state preserved (peers/consent/grants/members/tasks/audit unchanged)"
sleep 2
if curl -s --max-time 3 http://127.0.0.1:8179/n2n/certs >/dev/null 2>&1; then
  curl -s http://127.0.0.1:8179/n2n/certs | python3 -c "import json,sys; d=json.load(sys.stdin); print('  cert_mode:', d.get('cert_mode')); [print('  peer', p['identity'], p.get('trust_model'), p.get('verify_state')) for p in d.get('peers',[])]" 2>/dev/null || true
fi
say "done. Unpatched peers will be refused until they run this too."
