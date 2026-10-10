#!/usr/bin/env bash
# NetClaw — Protocol Peering & Mesh configuration (BGP/OSPF over GRE + ngrok).
#
# Standalone and re-runnable: existing values from ~/.openclaw/.env are shown
# as defaults, so fixing one answer is a 30-second re-run, not a reinstall.
# Called by scripts/setup.sh when the 'peering' component is installed, or
# run directly:
#
#   ./scripts/peering-setup.sh           # interactive configuration wizard
#   ./scripts/peering-setup.sh start     # start (or restart) the mesh BGP daemon
#   ./scripts/peering-setup.sh stop      # stop the mesh BGP daemon
#   ./scripts/peering-setup.sh status    # show daemon, sessions, and RIB summary

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NETCLAW_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
# TTY-aware yes/no (spec 119) -- this file's own ask()/ask_yn() below always
# read()/block regardless of TTY, an existing property this change doesn't
# touch; the new mobile-enrollment prompt uses tui_yesno instead so it alone
# defaults safely (to "no") under a non-interactive invocation.
source "$SCRIPT_DIR/lib/tui.sh"

eval "$(python3 "$SCRIPT_DIR/federation-control.py" env)"
OPENCLAW_ENV="${OPENCLAW_ENV:-$RUNTIME_HOME/.env}"
PROTOCOL_MCP_DIR="$NETCLAW_DIR/mcp-servers/protocol-mcp"
BGP_DAEMON="$PROTOCOL_MCP_DIR/bgp-daemon-v2.py"
DAEMON_OUT="$RUNTIME_HOME/netclaw-federation/daemon.log"

# Read a value from ~/.openclaw/.env ('' if unset)
env_get() {
    [ -f "$OPENCLAW_ENV" ] || return 0
    python3 "$SCRIPT_DIR/write-env.py" --get "$OPENCLAW_ENV" "$1"
}

# Prompt with default; re-prompts yes/no questions until the answer is valid
# (a stray key like "7" must not silently mean "no").
ask() {
    local var="$1" text="$2" default="${3:-}" input
    echo -ne "  ${CYAN}${text}${NC}${default:+ ${DIM}[$default]${NC}}: "
    read -r input
    printf -v "$var" '%s' "${input:-$default}"
}

ask_yn() {
    local var="$1" text="$2" default="$3" input
    while true; do
        if [ "$default" = "y" ]; then
            echo -ne "  ${CYAN}${text}${NC} ${DIM}[Y/n]${NC}: "
        else
            echo -ne "  ${CYAN}${text}${NC} ${DIM}[y/N]${NC}: "
        fi
        read -r input
        input="${input:-$default}"
        case "$input" in
            [Yy]|[Yy]es) printf -v "$var" '%s' y; return ;;
            [Nn]|[Nn]o)  printf -v "$var" '%s' n; return ;;
            *) echo -e "  ${YELLOW}Please answer y or n.${NC}" ;;
        esac
    done
}

# ── daemon control ───────────────────────────────────────────────
daemon_running() {
    python3 "$SCRIPT_DIR/federation-control.py" status >/dev/null 2>&1
}

daemon_start() {
    python3 "$SCRIPT_DIR/federation-control.py" start
}

daemon_status() {
    if ! daemon_running; then
        log_warn "Mesh daemon is not running. Start it with: ./scripts/peering-setup.sh start"
        exit 1
    fi
    echo ""
    echo -e "${BOLD}  BGP sessions:${NC}"
    curl -s "$BGP_API/status" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for p in d.get("peers", []):
    print("    %-30s %s" % (p["peer"], p["state"]))'
    echo ""
    echo -e "${BOLD}  RIB (best routes):${NC}"
    curl -s "$BGP_API/rib" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for pfx, r in d.get("loc_rib", {}).items():
    path = ",".join(str(a) for a in r.get("as_path", [])) or "local"
    print("    %-28s via %-22s as_path [%s] (%s)" % (pfx, r.get("peer_ip", "-"), path, r.get("source", "?")))'
    echo ""
    log_info "Add a peer at runtime:"
    echo "    curl -X POST $BGP_API/add_peer -d '{\"ip\":\"N.tcp.ngrok.io\",\"as\":65001,\"port\":NNNNN,\"hostname\":true}'"
}

daemon_stop() {
    python3 "$SCRIPT_DIR/federation-control.py" stop
}

case "${1:-}" in
    start)  daemon_start;  exit 0 ;;
    stop)   daemon_stop;   exit 0 ;;
    status) daemon_status; exit 0 ;;
    "") ;;
    *) echo "Usage: $0 [start|stop|status]"; exit 1 ;;
esac

# ── configuration wizard ─────────────────────────────────────────
mkdir -p "$(dirname "$OPENCLAW_ENV")"
[ -f "$OPENCLAW_ENV" ] || (umask 077; touch "$OPENCLAW_ENV")

echo ""
echo -e "${BOLD}  NetClaw Protocol Peering${NC}"
echo "  NetClaw can participate in BGP/OSPF as a real routing peer."
echo "  Re-run this script anytime to change answers."
echo ""

ask PROTO_ROUTER_ID "Router ID (e.g. 4.4.4.4)"        "$(env_get NETCLAW_ROUTER_ID)"
PROTO_ROUTER_ID="${PROTO_ROUTER_ID:-4.4.4.4}"
ask PROTO_LOCAL_AS  "Local BGP AS (e.g. 65001)"       "$(env_get NETCLAW_LOCAL_AS)"
PROTO_LOCAL_AS="${PROTO_LOCAL_AS:-65001}"
ask PROTO_PEER_IP   "Local BGP peer IP — your FRR lab or router (e.g. 172.16.0.1)" "172.16.0.1"
ask PROTO_PEER_AS   "Local BGP peer AS (e.g. 65000)"  "65000"
ask_yn PROTO_LAB_MODE "Lab mode (skip ServiceNow CR)?" "y"
[ "$PROTO_LAB_MODE" = "y" ] && PROTO_LAB_MODE_VAL="true" || PROTO_LAB_MODE_VAL="false"

_set_env_var "NETCLAW_ROUTER_ID"   "$PROTO_ROUTER_ID"
_set_env_var "NETCLAW_LOCAL_AS"    "$PROTO_LOCAL_AS"
_set_env_var "NETCLAW_LAB_MODE"    "$PROTO_LAB_MODE_VAL"
_set_env_var "PROTOCOL_MCP_SCRIPT" "$PROTOCOL_MCP_DIR/server.py"

MESH_PEERS_JSON="[{\"ip\":\"$PROTO_PEER_IP\",\"as\":$PROTO_PEER_AS}"

echo ""
echo -e "  ${BOLD}── NetClaw Mesh ──${NC}"
echo "  Peer with other NetClaw instances worldwide over BGP via ngrok."
echo ""
ask_yn ENABLE_MESH "Enable NetClaw Mesh peering (BGP over ngrok)?" "n"

if [ "$ENABLE_MESH" = "y" ]; then
    ask MESH_BGP_PORT "BGP listen port" "$(env_get BGP_LISTEN_PORT)"
    MESH_BGP_PORT="${MESH_BGP_PORT:-1179}"

    echo ""
    echo "  Add remote NetClaw peers (other people's ngrok endpoints)."
    echo "  You can also add peers at runtime — no restart needed:"
    echo "    curl -X POST $BGP_API/add_peer -d '{\"ip\":\"HOST\",\"as\":AS,\"port\":PORT,\"hostname\":true}'"
    echo ""
    MESH_REMOTE_COUNT=0
    ask_yn ADD_REMOTE "Add a remote NetClaw peer?" "n"
    while [ "$ADD_REMOTE" = "y" ]; do
        ask REMOTE_HOST "  Remote ngrok hostname (e.g. 0.tcp.ngrok.io)" ""
        ask REMOTE_PORT "  Remote ngrok port (e.g. 12345)" ""
        ask REMOTE_AS   "  Remote AS number (e.g. 65002)" ""
        if [ -n "$REMOTE_HOST" ] && [ -n "$REMOTE_PORT" ] && [ -n "$REMOTE_AS" ]; then
            MESH_PEERS_JSON="${MESH_PEERS_JSON},{\"ip\":\"${REMOTE_HOST}\",\"as\":${REMOTE_AS},\"port\":${REMOTE_PORT},\"hostname\":true}"
            MESH_PEERS_JSON="${MESH_PEERS_JSON},{\"as\":${REMOTE_AS},\"passive\":true,\"accept_any_source\":true}"
            MESH_REMOTE_COUNT=$((MESH_REMOTE_COUNT + 1))
        else
            log_warn "Peer skipped — hostname, port, and AS are all required."
        fi
        ask_yn ADD_REMOTE "Add another remote peer?" "n"
    done

    echo ""
    ask_yn ACCEPT_INBOUND "Accept inbound mesh connections from any AS?" "y"
    [ "$ACCEPT_INBOUND" = "y" ] && MESH_OPEN="true" || MESH_OPEN="false"

    MESH_PEERS_JSON="${MESH_PEERS_JSON}]"

    _set_env_var "BGP_LISTEN_PORT"      "$MESH_BGP_PORT"
    _set_env_var "NETCLAW_MESH_ENABLED" "true"
    _set_env_var "NETCLAW_MESH_OPEN"    "$MESH_OPEN"   # the daemon reads this one
    _set_env_var "NETCLAW_BGP_PEERS"    "$MESH_PEERS_JSON"

    echo ""
    log_info "NetClaw Mesh configured:"
    log_info "  BGP listen port: $MESH_BGP_PORT · remote peers: $MESH_REMOTE_COUNT · accept inbound: $MESH_OPEN"
    echo ""
    log_info "To expose your BGP port to other operators:  ngrok tcp $MESH_BGP_PORT"
    log_info "Share the ngrok hostname/port it prints plus your AS ($PROTO_LOCAL_AS)."
else
    MESH_PEERS_JSON="${MESH_PEERS_JSON}]"
    _set_env_var "NETCLAW_BGP_PEERS"    "$MESH_PEERS_JSON"
    _set_env_var "NETCLAW_MESH_ENABLED" "false"
fi

echo ""
log_info "Configuration written to $OPENCLAW_ENV"

# The wizard writes config; the daemon makes it real.
echo ""
if daemon_running; then
    ask_yn RESTART_DAEMON "Mesh daemon is running with old settings — restart it now?" "y"
    [ "$RESTART_DAEMON" = "y" ] && daemon_start
else
    ask_yn START_DAEMON "Start the mesh BGP daemon now?" "y"
    if [ "$START_DAEMON" = "y" ]; then
        daemon_start
    else
        log_info "Start it later: ./scripts/peering-setup.sh start"
    fi
fi


# ── NetClaw Mobile enrollment (spec 119) ──────────────────────────
# Only worth asking once the mesh daemon is actually up -- an enrollment
# token cannot be validly issued before the daemon that issues it is
# running. Delegates entirely to `netclaw risk enroll-mobile` rather than
# duplicating its edge-check/promote/token logic here (research.md R5).
if daemon_running; then
    echo ""
    if tui_yesno "Would you like to enroll a mobile device now?" n; then
        # `|| true`: an incomplete/declined enrollment here is not a fatal
        # error for the mesh peering setup this script's main job already
        # finished -- only this bonus step should stop, not the whole wizard.
        "$NETCLAW_DIR/scripts/netclaw" risk enroll-mobile || true
    else
        log_info "Enroll a phone later: netclaw risk enroll-mobile [device-label]"
    fi
fi

echo ""
log_info "Check sessions and routes anytime: ./scripts/peering-setup.sh status"
