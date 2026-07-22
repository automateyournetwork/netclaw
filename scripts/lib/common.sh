#!/usr/bin/env bash
# NetClaw installer — shared helpers, logging, and path definitions.
# Sourced by scripts/install.sh and scripts/setup.sh.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
ORANGE='\033[38;5;208m'
CORAL='\033[38;5;203m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${CYAN}[STEP]${NC} $1"; }

check_command() {
    if command -v "$1" &> /dev/null; then
        log_info "$1 found: $(command -v "$1")"
        return 0
    else
        log_error "$1 not found"
        return 1
    fi
}

clone_or_pull() {
    local dir="$1" url="$2"
    if [ -d "$dir" ]; then
        log_info "Already cloned. Pulling latest..."
        git -C "$dir" pull || log_warn "git pull failed, using existing version"
    else
        log_info "Cloning from $url..."
        git clone "$url" "$dir"
    fi
}

# ───────────────────────────────────────────
# Agent runtime abstraction.
# NetClaw runs on top of an agent runtime — OpenClaw (default) or Hermes
# (Nous Research). Everything downstream (state dir, config file, skills
# dir, env file, lifecycle commands) is derived from the selected runtime
# so the installer, deploy, and verify steps are runtime-agnostic.
#
# openclaw keeps its historical layout exactly:
#   ~/.openclaw/openclaw.json, ~/.openclaw/workspace/skills, ~/.openclaw/.env
# hermes uses its native layout (overridable with $HERMES_HOME):
#   ~/.hermes/config.yaml, ~/.hermes/skills, ~/.hermes/.env
#
# Call after NETCLAW_RUNTIME is known; safe to call again if the choice
# changes (e.g. after a --runtime flag or the TUI prompt).
# ───────────────────────────────────────────
define_runtime() {
    RUNTIME="${NETCLAW_RUNTIME:-openclaw}"
    case "$RUNTIME" in
        openclaw)
            RUNTIME_CMD="openclaw"
            RUNTIME_NAME="OpenClaw"
            RUNTIME_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
            RUNTIME_CONFIG="$RUNTIME_HOME/openclaw.json"
            RUNTIME_WORKSPACE="$RUNTIME_HOME/workspace"
            RUNTIME_SKILLS="$RUNTIME_HOME/workspace/skills"
            ;;
        hermes)
            RUNTIME_CMD="hermes"
            RUNTIME_NAME="Hermes"
            RUNTIME_HOME="${HERMES_HOME:-$HOME/.hermes}"
            RUNTIME_CONFIG="$RUNTIME_HOME/config.yaml"
            RUNTIME_WORKSPACE="$RUNTIME_HOME"
            RUNTIME_SKILLS="$RUNTIME_HOME/skills"
            ;;
        *)
            log_error "Unknown runtime: $RUNTIME (valid: openclaw, hermes)"
            exit 1
            ;;
    esac
    RUNTIME_ENV="$RUNTIME_HOME/.env"

    # The component manifest lives under the runtime's state dir unless the
    # caller pinned NETCLAW_MANIFEST explicitly in the environment (captured
    # once at source time so re-deriving on a runtime switch still works).
    NETCLAW_MANIFEST="${_NETCLAW_MANIFEST_ENV:-$RUNTIME_HOME/netclaw-components.conf}"
}

# Write KEY=VALUE into the runtime .env (create or update in place).
# Portable — no associative arrays for macOS bash 3.2.
_set_env_var() {
    local key="$1" val="$2"
    local env_file="${RUNTIME_ENV:-${OPENCLAW_ENV:-$HOME/.openclaw/.env}}"
    mkdir -p "$(dirname "$env_file")"
    [ -f "$env_file" ] || touch "$env_file"
    if grep -q "^${key}=" "$env_file" 2>/dev/null; then
        sed -i.bak "s|^${key}=.*|${key}=${val}|" "$env_file" && rm -f "$env_file.bak"
    else
        echo "${key}=${val}" >> "$env_file"
    fi
}

# ───────────────────────────────────────────
# Canonical install locations for every MCP.
# Defined up front so deploy/verify/setup work no matter which
# subset of components was selected.
# ───────────────────────────────────────────
define_paths() {
    # Resolve the agent runtime (OpenClaw/Hermes) and its state-dir paths first.
    define_runtime

    MCP_DIR="$NETCLAW_DIR/mcp-servers"

    PYATS_MCP_DIR="$MCP_DIR/pyATS_MCP"
    JUNOS_MCP_DIR="$MCP_DIR/junos-mcp-server"
    CVP_MCP_DIR="$MCP_DIR/mcp-cvp-fun"
    MARKMAP_MCP_DIR="$MCP_DIR/markmap_mcp"
    MARKMAP_INNER="$MARKMAP_MCP_DIR/markmap-mcp"
    GAIT_MCP_DIR="$MCP_DIR/gait_mcp"
    NETBOX_MCP_DIR="$MCP_DIR/netbox-mcp-server"
    NAUTOBOT_MCP_DIR="$MCP_DIR/mcp-nautobot"
    INFRAHUB_MCP_DIR="$MCP_DIR/infrahub-mcp"
    ITENTIAL_MCP_DIR="$MCP_DIR/itential-mcp"
    SERVICENOW_MCP_DIR="$MCP_DIR/servicenow-mcp"
    ACI_MCP_DIR="$MCP_DIR/ACI_MCP"
    ISE_MCP_DIR="$MCP_DIR/ISE_MCP"
    WIKIPEDIA_MCP_DIR="$MCP_DIR/Wikipedia_MCP"
    NVD_MCP_DIR="$MCP_DIR/mcp-nvd"
    SUBNET_MCP_DIR="$MCP_DIR/subnet-calculator-mcp"
    F5_MCP_DIR="$MCP_DIR/f5-mcp-server"
    CATC_MCP_DIR="$MCP_DIR/catalyst-center-mcp"
    GITHUB_MCP_IMAGE="ghcr.io/github/github-mcp-server"
    PACKET_BUDDY_MCP_DIR="$MCP_DIR/packet-buddy-mcp"
    FMC_MCP_DIR="$MCP_DIR/CiscoFMC-MCP-server-community"
    MERAKI_MCP_DIR="$MCP_DIR/meraki-magic-mcp-community"
    TE_COMMUNITY_MCP_DIR="$MCP_DIR/thousandeyes-mcp-community"
    RADKIT_MCP_DIR="$MCP_DIR/radkit-mcp-server-community"
    UML_MCP_DIR="$MCP_DIR/uml-mcp"
    CLAB_MCP_DIR="$MCP_DIR/clab-mcp-server"
    SDWAN_MCP_DIR="$MCP_DIR/cisco-sdwan-mcp"
    PROMETHEUS_MCP_DIR="$MCP_DIR/prometheus-mcp-server"
    NMAP_MCP_DIR="$MCP_DIR/nmap-mcp"
    TTS_MCP_DIR="$MCP_DIR/tts-mcp"
    PROTOCOL_MCP_DIR="$MCP_DIR/protocol-mcp"
    FORTIMANAGER_MCP_DIR="$MCP_DIR/fortimanager-mcp"
    PRISMA_SDWAN_MCP_DIR="$MCP_DIR/prisma-sdwan-mcp"
    ARUBA_CX_MCP_DIR="$MCP_DIR/aruba-cx-mcp"
    AAP_MCP_DIR="$MCP_DIR/AAP-Enterprise-MCP-Server"
    FWRULE_MCP_DIR="$MCP_DIR/fwrule-mcp"
    MEMPALACE_MCP_DIR="$MCP_DIR/mempalace"
    HUMANRAIL_MCP_DIR="$MCP_DIR/humanrail-mcp-server"
    CHECKPOINT_MCP_DIR="$MCP_DIR/checkpoint-mcp-servers"
    FORWARD_MCP_DIR="$MCP_DIR/forward-mcp"

    # Bundled with the NetClaw repo (prefer in-repo copy)
    SUZIEQ_MCP_DIR="$MCP_DIR/suzieq-mcp"
    [ -d "$NETCLAW_DIR/mcp-servers/suzieq-mcp" ] && SUZIEQ_MCP_DIR="$NETCLAW_DIR/mcp-servers/suzieq-mcp"
    BATFISH_MCP_DIR="$MCP_DIR/batfish-mcp"
    [ -d "$NETCLAW_DIR/mcp-servers/batfish-mcp" ] && BATFISH_MCP_DIR="$NETCLAW_DIR/mcp-servers/batfish-mcp"
    AZURE_NET_MCP_DIR="$MCP_DIR/azure-network-mcp"
    [ -d "$NETCLAW_DIR/mcp-servers/azure-network-mcp" ] && AZURE_NET_MCP_DIR="$NETCLAW_DIR/mcp-servers/azure-network-mcp"
    GNMI_MCP_DIR="$MCP_DIR/gnmi-mcp"
    [ -d "$NETCLAW_DIR/mcp-servers/gnmi-mcp" ] && GNMI_MCP_DIR="$NETCLAW_DIR/mcp-servers/gnmi-mcp"
    CLAROTY_MCP_DIR="$MCP_DIR/claroty-mcp"
    [ -d "$NETCLAW_DIR/mcp-servers/claroty-mcp" ] && CLAROTY_MCP_DIR="$NETCLAW_DIR/mcp-servers/claroty-mcp"
    TWITTER_MCP_DIR="$NETCLAW_DIR/mcp-servers/twitter-mcp"
    TWILIO_MCP_DIR="$NETCLAW_DIR/mcp-servers/twilio-voice-mcp"
    TOKEN_LIB_DIR="$NETCLAW_DIR/src/netclaw_tokens"

    # Console-script detection defaults (components refine these when installed)
    INFOBLOX_MCP_CMD_DETECTED="infoblox-ddi-mcp"
    command -v infoblox-ddi-mcp &> /dev/null || INFOBLOX_MCP_CMD_DETECTED="python3 -m infoblox_ddi_mcp"
    PANOS_MCP_CMD_DETECTED="palo-alto-mcp"
    command -v palo-alto-mcp &> /dev/null || PANOS_MCP_CMD_DETECTED="python3 -m palo_alto_mcp"
    FORTIMANAGER_MCP_CMD_DETECTED="python3 -m fortimanager_mcp"
}

# ───────────────────────────────────────────
# Component manifest — records which MCPs were selected at install
# time so setup.sh only prompts for credentials that matter. The path is
# derived per-runtime in define_runtime(); an explicit NETCLAW_MANIFEST in
# the environment still wins (captured here before define_runtime overwrites
# the variable).
# ───────────────────────────────────────────
_NETCLAW_MANIFEST_ENV="${NETCLAW_MANIFEST:-}"

manifest_write() {
    # $@ = selected component ids
    mkdir -p "$(dirname "$NETCLAW_MANIFEST")"
    {
        echo "# NetClaw installed components — written by scripts/install.sh"
        echo "# Re-run ./scripts/install.sh to add or change components."
        printf '%s\n' "$@"
    } > "$NETCLAW_MANIFEST"
}

# True if the component was installed. If no manifest exists (pre-TUI
# install, or manual setup), everything is considered installed.
component_selected() {
    [ -f "$NETCLAW_MANIFEST" ] || return 0
    grep -qx "$1" "$NETCLAW_MANIFEST" 2>/dev/null
}

# Resolve the runtime (and NETCLAW_MANIFEST / RUNTIME_* paths) on source, so
# consumers that don't call define_paths (e.g. setup.sh, peering-setup.sh)
# still get them. Honors NETCLAW_RUNTIME from the environment; install.sh
# re-derives after a --runtime flag or the TUI prompt. Idempotent.
define_runtime
