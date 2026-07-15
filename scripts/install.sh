#!/usr/bin/env bash
# NetClaw — CCIE Network Agent installer.
#
# Interactive TUI: pick an install profile, fine-tune the MCP server list in a
# checklist, and only the selected components are installed. Selections are
# recorded in ~/.openclaw/netclaw-components.conf so setup.sh only asks for
# credentials that matter. Re-run anytime to add or change components.
#
# Non-interactive / scripted use:
#   ./scripts/install.sh --profile recommended
#   ./scripts/install.sh --components "pyats netbox gait"   # exact set (replaces manifest)
#   ./scripts/install.sh --add "gns3 cml"                   # add to what's installed
#   ./scripts/install.sh --all
#   ./scripts/install.sh --list
#
# Install logic lives in scripts/lib/:
#   common.sh         shared helpers, canonical paths, component manifest
#   tui.sh            logo, arrow-key menu, multi-select checklist
#   catalog.sh        component catalog + profiles
#   install-steps.sh  one install function per component

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NETCLAW_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/tui.sh"
source "$SCRIPT_DIR/lib/catalog.sh"
source "$SCRIPT_DIR/lib/install-steps.sh"

define_paths

TOTAL_COMPONENTS=$(catalog_ids | wc -l | tr -d ' ')

# ═══════════════════════════════════════════
# CLI arguments
# ═══════════════════════════════════════════

usage() {
    echo "Usage: ./scripts/install.sh [options]"
    echo ""
    echo "  (no options)              interactive TUI installer"
    echo "  --profile <name>          install a profile without the TUI"
    echo "                            ($PROFILE_NAMES)"
    echo "  --components \"id id ...\"  install an exact component list (see --list);"
    echo "                            REPLACES the recorded component set"
    echo "  --add \"id id ...\"         install components on top of an existing install;"
    echo "                            merges into the recorded component set"
    echo "  --all                     install everything ($TOTAL_COMPONENTS components)"
    echo "  --list                    list all components and profiles, then exit"
    echo "  --help                    this help"
}

list_components() {
    local entry id cat name desc last_cat="" p
    echo ""
    echo "Components ($TOTAL_COMPONENTS):"
    for entry in "${CATALOG[@]}"; do
        IFS='|' read -r id cat name desc <<< "$entry"
        if [ "$cat" != "$last_cat" ]; then
            echo ""
            echo "  $cat"
            last_cat="$cat"
        fi
        printf '    %-16s %-26s %s\n' "$id" "$name" "$desc"
    done
    echo ""
    echo "Profiles:"
    for p in $PROFILE_NAMES; do
        printf '    %-16s %s\n' "$p" "$(profile_components "$p" | tr -s ' ')"
    done
    echo ""
}

SELECTED=""
CLI_MODE=0
ADD_MODE=0

while [ $# -gt 0 ]; do
    case "$1" in
        --profile)
            [ $# -ge 2 ] || { log_error "--profile needs a value"; usage; exit 1; }
            SELECTED="$(profile_components "$2")" || { log_error "Unknown profile: $2 (valid: $PROFILE_NAMES)"; exit 1; }
            CLI_MODE=1; shift 2 ;;
        --components)
            [ $# -ge 2 ] || { log_error "--components needs a value"; usage; exit 1; }
            for id in $2; do
                catalog_has "$id" || { log_error "Unknown component: $id (run --list to see valid ids)"; exit 1; }
            done
            SELECTED="$2"
            CLI_MODE=1; shift 2 ;;
        --add)
            [ $# -ge 2 ] || { log_error "--add needs a value"; usage; exit 1; }
            for id in $2; do
                catalog_has "$id" || { log_error "Unknown component: $id (run --list to see valid ids)"; exit 1; }
            done
            SELECTED="$2"
            ADD_MODE=1
            CLI_MODE=1; shift 2 ;;
        --all|--full)
            SELECTED="$(profile_components full)"
            CLI_MODE=1; shift ;;
        --list)  list_components; exit 0 ;;
        --help|-h) usage; exit 0 ;;
        *) log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# ═══════════════════════════════════════════
# Refuse to run under sudo
# ═══════════════════════════════════════════
# Under sudo, $HOME is /root: OpenClaw config, credentials, skills, and the
# component manifest would all land in /root/.openclaw — invisible to the
# user who will actually run openclaw. The installer asks before running the
# specific commands that need root instead.
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ] && [ "${NETCLAW_ALLOW_ROOT:-0}" != "1" ]; then
    log_error "Do not run the installer with sudo."
    log_error "Everything (OpenClaw config, API keys, skills) would be installed for root in /root/.openclaw,"
    log_error "not for $SUDO_USER — openclaw run as $SUDO_USER would then see none of it."
    echo ""
    log_info "Re-run as your normal user:  ./scripts/install.sh"
    log_info "The installer prompts before each command that actually needs sudo."
    log_info "(Installing deliberately for root? Set NETCLAW_ALLOW_ROOT=1 to override.)"
    exit 1
elif [ "$(id -u)" = "0" ]; then
    log_warn "Running as root — NetClaw will be installed for the root user (/root/.openclaw)."
fi

# ═══════════════════════════════════════════
# Existing-install detection
# ═══════════════════════════════════════════
# Probe real state instead of asking the user what's installed:
# OpenClaw binary, onboard state, gateway service, component manifest.
# Sets DETECTED_* for the banner, the menu, and the core-step skips.

DETECTED_OPENCLAW=""
DETECTED_ONBOARDED=0
DETECTED_GATEWAY=0
DETECTED_COMPONENTS=""

detect_existing() {
    if command -v openclaw &> /dev/null; then
        DETECTED_OPENCLAW="$(openclaw --version 2>/dev/null | head -1 || true)"
        DETECTED_OPENCLAW="${DETECTED_OPENCLAW:-unknown version}"
    fi
    [ -f "$HOME/.openclaw/openclaw.json" ] && DETECTED_ONBOARDED=1
    if command -v systemctl &> /dev/null && \
       [ "$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)" = "active" ]; then
        DETECTED_GATEWAY=1
    elif (exec 3<>/dev/tcp/127.0.0.1/18789) 2>/dev/null; then
        DETECTED_GATEWAY=1
    fi
    if [ -f "$NETCLAW_MANIFEST" ]; then
        # `|| true` guards pipefail: grep -v exits 1 on a comments-only manifest
        DETECTED_COMPONENTS="$(grep -v '^#' "$NETCLAW_MANIFEST" 2>/dev/null | tr '\n' ' ' | tr -s ' ' || true)"
        DETECTED_COMPONENTS="${DETECTED_COMPONENTS# }"; DETECTED_COMPONENTS="${DETECTED_COMPONENTS% }"
    fi
}

detect_banner() {
    local ok="${T_CYAN}✓${T_NC}" no="${T_DIM}—${T_NC}" parts=""
    if [ -n "$DETECTED_OPENCLAW" ]; then
        parts="${DETECTED_OPENCLAW} $ok"
        [ "$DETECTED_ONBOARDED" = "1" ] && parts="$parts ${T_DIM}·${T_NC} onboarded $ok" \
                                        || parts="$parts ${T_DIM}·${T_NC} not onboarded $no"
        [ "$DETECTED_GATEWAY" = "1" ]   && parts="$parts ${T_DIM}·${T_NC} gateway running $ok" \
                                        || parts="$parts ${T_DIM}·${T_NC} gateway not running $no"
        if [ -n "$DETECTED_COMPONENTS" ]; then
            parts="$parts ${T_DIM}·${T_NC} $(echo "$DETECTED_COMPONENTS" | wc -w | tr -d ' ') components installed"
        fi
    else
        parts="OpenClaw not installed $no ${T_DIM}— full setup will run${T_NC}"
    fi
    echo -e "  ${T_BOLD}Detected:${T_NC} $parts"
    echo ""
}

detect_existing

# ═══════════════════════════════════════════
# Component selection (TUI)
# ═══════════════════════════════════════════

# Fill CL_IDS/CL_LABELS/CL_ON from the catalog with category headers.
# $1 = space-separated ids to preselect.
build_checklist() {
    local preselect=" $1 " entry id cat name desc last_cat="" label maxw
    maxw=$(( $(tput cols 2>/dev/null || echo 100) - 12 ))
    CL_IDS=(); CL_LABELS=(); CL_ON=()
    for entry in "${CATALOG[@]}"; do
        IFS='|' read -r id cat name desc <<< "$entry"
        if [ "$cat" != "$last_cat" ]; then
            CL_IDS+=(""); CL_LABELS+=("── $cat ──"); CL_ON+=(0)
            last_cat="$cat"
        fi
        label="$(printf '%-26s %s' "$name" "$desc")"
        CL_IDS+=("$id")
        CL_LABELS+=("${label:0:$maxw}")
        if [[ "$preselect" == *" $id "* ]]; then CL_ON+=(1); else CL_ON+=(0); fi
    done
}

select_components() {
    netclaw_logo
    detect_banner

    # Preselect previously installed components on a re-run
    local previous="$DETECTED_COMPONENTS"

    local rec_count
    rec_count=$(echo $PROFILE_RECOMMENDED | wc -w | tr -d ' ')

    local options=() profiles=()
    if [ -n "$previous" ]; then
        local prev_count
        prev_count=$(echo $previous | wc -w | tr -d ' ')
        options+=("Add / update    — your $prev_count installed components, preselected; tick more to add")
        profiles+=(update)
    fi
    options+=(
        "Recommended     — curated starter set for most users ($rec_count servers)"
        "Custom          — pick exactly the MCP servers you want"
        "Everything      — all $TOTAL_COMPONENTS components (the classic full install)"
        "Cisco           — pyATS, ACI, ISE, Catalyst Center, Meraki, SD-WAN, CML, FMC..."
        "Multivendor     — Cisco + Juniper, Arista, Aruba, F5, NetBox, Nautobot..."
        "Cloud           — AWS, Azure, GCP, Cloudflare, Terraform, Vault, GitHub"
        "Security        — ISE, FMC, Panorama, FortiManager, Check Point, Zscaler..."
        "Labs            — CML, ContainerLab, Batfish, protocol peering, SuzieQ"
        "Observability   — Grafana, Prometheus, Datadog, Splunk, ThousandEyes..."
        "Minimal         — pyATS + audit trail + core utilities"
    )
    profiles+=(recommended custom full cisco multivendor cloud security labs observability minimal)

    tui_menu "How do you want to set up NetClaw?" "${options[@]}" || { log_warn "Install cancelled."; exit 1; }
    local choice="${profiles[$TUI_CHOICE]}"

    if [ "$choice" = "custom" ] || [ "$choice" = "update" ]; then
        build_checklist "${previous:-$PROFILE_RECOMMENDED}"
        tui_checklist "Select MCP servers to install ($TOTAL_COMPONENTS available)" || { log_warn "Install cancelled."; exit 1; }
        SELECTED="$TUI_SELECTED"
    else
        SELECTED="$(profile_components "$choice")"
        if [ "$choice" != "full" ] && tui_yesno "Fine-tune this selection in the component picker?" "n"; then
            build_checklist "$SELECTED"
            tui_checklist "Select MCP servers to install ($TOTAL_COMPONENTS available)" || { log_warn "Install cancelled."; exit 1; }
            SELECTED="$TUI_SELECTED"
        fi
    fi

    if [ -z "$SELECTED" ]; then
        log_warn "Nothing selected — nothing to install."
        exit 0
    fi
}

# Print the current selection grouped by category.
show_selection() {
    local sel=" $SELECTED " entry id cat name desc last_cat="" line=""
    echo ""
    echo -e "  ${T_BOLD}Selected components ($(echo $SELECTED | wc -w | tr -d ' ') of $TOTAL_COMPONENTS):${T_NC}"
    for entry in "${CATALOG[@]}"; do
        IFS='|' read -r id cat name desc <<< "$entry"
        [[ "$sel" == *" $id "* ]] || continue
        if [ "$cat" != "$last_cat" ]; then
            [ -n "$line" ] && echo "$line"
            echo -e "  ${T_PINK}${cat}:${T_NC}"
            line="    "
            last_cat="$cat"
        fi
        if [ ${#line} -gt 4 ] && [ $(( ${#line} + ${#name} + 2 )) -gt 78 ]; then
            echo "$line"
            line="    "
        fi
        [ ${#line} -gt 4 ] && line="$line, $name" || line="$line$name"
    done
    [ -n "$line" ] && [ ${#line} -gt 4 ] && echo "$line"
    echo ""
}

if [ "$CLI_MODE" -eq 0 ]; then
    if tui_is_tty; then
        select_components
        show_selection
        tui_yesno "Install these now?" "y" || { log_warn "Install cancelled."; exit 1; }
    else
        # Piped / CI with no flags: don't guess — a full 72-component install
        # is far too big to start implicitly.
        log_error "No TTY and no selection flags — refusing to guess what to install."
        log_info "Scripted installs must pick explicitly:"
        log_info "  ./scripts/install.sh --profile recommended"
        log_info "  ./scripts/install.sh --components \"pyats netbox gait\""
        log_info "  ./scripts/install.sh --add \"gns3 cml\"       # add to an existing install"
        log_info "  ./scripts/install.sh --all"
        exit 1
    fi
else
    echo ""
    detect_banner
    show_selection
fi

SELECTED_COUNT=$(echo $SELECTED | wc -w | tr -d ' ')

echo "========================================="
echo "  NetClaw - CCIE Network Agent"
echo "  Installing $SELECTED_COUNT of $TOTAL_COMPONENTS components"
echo "========================================="
echo ""
echo "  Project: $NETCLAW_DIR"
echo ""

# ═══════════════════════════════════════════
# Core steps (always run)
# ═══════════════════════════════════════════

core_prereqs
core_openclaw
core_onboard
core_gateway_check
core_mcpdir

# ═══════════════════════════════════════════
# Selected components
# ═══════════════════════════════════════════
# Installer output goes to a per-component log at full verbosity; the
# terminal gets one line per component. On failure the log tail prints
# immediately AND in the final problem report, so nothing depends on
# terminal scrollback. NETCLAW_VERBOSE=1 streams everything like before.
# Components whose installers prompt for input keep the terminal.

INSTALL_LOG_DIR="$HOME/.openclaw/logs/install"
mkdir -p "$INSTALL_LOG_DIR"
INTERACTIVE_COMPONENTS=" checkpoint forward ipfabric threejs-viz "

run_component() {
    # $1 = component id, $2 = function name, $3 = display name
    local id="$1" fn="$2" name="$3" logf="$INSTALL_LOG_DIR/$1.log"
    if [ "${NETCLAW_VERBOSE:-0}" = "1" ] || [[ "$INTERACTIVE_COMPONENTS" == *" $id "* ]]; then
        if ! "$fn"; then
            log_warn "$name install reported an error — continuing."
            return 1
        fi
        return 0
    fi
    if "$fn" > "$logf" 2>&1; then
        # Safety net for installers that log [ERROR] but still return 0 —
        # don't let a component claim success with errors in its log.
        if grep -aq "\[ERROR\]" "$logf"; then
            log_error "$name reported errors despite finishing — last 15 log lines:"
            tail -15 "$logf" | sed -e 's/\x1b\[[0-9;]*m//g' -e 's/^/    /'
            log_warn "Full log: $logf — continuing."
            return 1
        fi
        log_info "$name installed  ${DIM}(log: $logf)${NC}"
        return 0
    fi
    log_error "$name install failed — last 15 log lines:"
    tail -15 "$logf" | sed -e 's/\x1b\[[0-9;]*m//g' -e 's/^/    /'
    log_warn "Full log: $logf — continuing."
    return 1
}

FAILED_COMPONENTS=""
STEP=0
for id in $SELECTED; do
    STEP=$((STEP + 1))
    fn="component_install_${id//-/_}"
    echo -e "${CYAN}── [$STEP/$SELECTED_COUNT] $(catalog_field "$id" 3) ──────────────────${NC}"
    if declare -F "$fn" > /dev/null; then
        run_component "$id" "$fn" "$(catalog_field "$id" 3)" || \
            FAILED_COMPONENTS="$FAILED_COMPONENTS $id"
    else
        log_warn "No installer found for '$id' — skipping."
    fi
done

if [ "${NETCLAW_VERBOSE:-0}" = "1" ]; then
    core_tokens
else
    if core_tokens > "$INSTALL_LOG_DIR/core-tokens.log" 2>&1; then
        log_info "Token optimization library installed  ${DIM}(log: $INSTALL_LOG_DIR/core-tokens.log)${NC}"
    else
        log_warn "Token optimization install reported an error — last 10 log lines:"
        tail -10 "$INSTALL_LOG_DIR/core-tokens.log" | sed 's/^/    /'
    fi
fi
core_deploy

# Record the selection so setup.sh only prompts for what's installed.
# --add merges into the existing manifest; every other path records the
# exact selection (unticking a component in the TUI removes it).
if [ "$ADD_MODE" = "1" ] && [ -n "$DETECTED_COMPONENTS" ]; then
    MERGED="$(printf '%s\n' $DETECTED_COMPONENTS $SELECTED | awk 'NF && !seen[$0]++')"
    manifest_write $MERGED
else
    manifest_write $SELECTED
fi
log_info "Component manifest written: $NETCLAW_MANIFEST"
echo ""

# Top-level `netclaw` command (menu: TUI / installer / protocol peering)
"$SCRIPT_DIR/netclaw" link
echo ""

# ═══════════════════════════════════════════
# Verify installation (selected components only)
# ═══════════════════════════════════════════

log_step "Verifying installation..."

SERVERS_OK=0
SERVERS_FAIL=0

verify_file() {
    local name="$1" path="$2"
    if [ -f "$path" ]; then
        log_info "$name: OK"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_error "$name: MISSING ($path)"
        SERVERS_FAIL=$((SERVERS_FAIL + 1))
    fi
}

verify_dir() {
    local name="$1" path="$2"
    if [ -d "$path" ]; then
        log_info "$name: OK"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_warn "$name: NOT INSTALLED ($path missing)"
        SERVERS_FAIL=$((SERVERS_FAIL + 1))
    fi
}

verify_cmd_or_module() {
    local name="$1" cmd="$2" module="$3" hint="$4"
    if command -v "$cmd" &> /dev/null || python3 -c "import $module" 2>/dev/null; then
        log_info "$name: OK"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_warn "$name: NOT INSTALLED ($hint)"
        SERVERS_FAIL=$((SERVERS_FAIL + 1))
    fi
}

verify_runner() {
    local name="$1" cmd="$2" note="$3"
    if command -v "$cmd" &> /dev/null; then
        log_info "$name: OK ($note)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_warn "$name: NOT AVAILABLE ($cmd not installed)"
        SERVERS_FAIL=$((SERVERS_FAIL + 1))
    fi
}

verify_remote() {
    log_info "$1: OK (remote server — no local install)"
    SERVERS_OK=$((SERVERS_OK + 1))
}

verify_component() {
    local id="$1" name
    name="$(catalog_field "$id" 3)"
    case "$id" in
        pyats)           verify_file "$name" "$PYATS_MCP_DIR/pyats_mcp_server.py" ;;
        junos)           verify_dir  "$name" "$JUNOS_MCP_DIR" ;;
        arista-cvp)      verify_dir  "$name" "$CVP_MCP_DIR" ;;
        f5)              verify_file "$name" "$F5_MCP_DIR/F5MCPserver.py" ;;
        catalyst-center) verify_file "$name" "$CATC_MCP_DIR/catalyst-center-mcp.py" ;;
        aruba-cx)        verify_dir  "$name" "$ARUBA_CX_MCP_DIR" ;;
        gnmi)            verify_dir  "$name" "$GNMI_MCP_DIR" ;;
        radkit)          verify_dir  "$name" "$RADKIT_MCP_DIR" ;;
        netbox)          verify_file "$name" "$NETBOX_MCP_DIR/src/netbox_mcp_server/server.py" ;;
        nautobot)        verify_dir  "$name" "$NAUTOBOT_MCP_DIR" ;;
        infrahub)        verify_cmd_or_module "$name" infrahub-mcp infrahub_mcp "pip3 install infrahub-mcp" ;;
        infoblox)        verify_cmd_or_module "$name" infoblox-ddi-mcp infoblox_ddi_mcp "pip3 install infoblox-ddi-mcp" ;;
        aci)             verify_file "$name" "$ACI_MCP_DIR/aci_mcp/main.py" ;;
        nso)             verify_cmd_or_module "$name" cisco-nso-mcp-server cisco_nso_mcp_server "requires Python 3.12+, pip3 install cisco-nso-mcp-server" ;;
        itential)        verify_cmd_or_module "$name" itential-mcp itential_mcp "pip3 install itential-mcp" ;;
        meraki)          verify_dir  "$name" "$MERAKI_MCP_DIR" ;;
        sdwan)           verify_dir  "$name" "$SDWAN_MCP_DIR" ;;
        prisma-sdwan)    verify_dir  "$name" "$PRISMA_SDWAN_MCP_DIR" ;;
        aap)             verify_dir  "$name" "$AAP_MCP_DIR" ;;
        ise)             verify_file "$name" "$ISE_MCP_DIR/src/ise_mcp_server/server.py" ;;
        fmc)             verify_dir  "$name" "$FMC_MCP_DIR" ;;
        panorama)        verify_cmd_or_module "$name" palo-alto-mcp palo_alto_mcp "pip3 install iflow-mcp-cdot65-palo-alto-mcp" ;;
        fortimanager)    verify_dir  "$name" "$FORTIMANAGER_MCP_DIR" ;;
        checkpoint)      verify_dir  "$name" "$CHECKPOINT_MCP_DIR" ;;
        claroty)         verify_dir  "$name" "$CLAROTY_MCP_DIR" ;;
        nvd-cve)         verify_file "$name" "$NVD_MCP_DIR/mcp_nvd/main.py" ;;
        nmap)            verify_file "$name" "$NMAP_MCP_DIR/server.py" ;;
        fwrule)          verify_dir  "$name" "$FWRULE_MCP_DIR" ;;
        aws)             verify_runner "$name" uvx "6 servers run via uvx" ;;
        azure)           verify_dir  "$name" "$AZURE_NET_MCP_DIR" ;;
        gcp|cloudflare|terraform|vault|zscaler|datadog|jenkins|kubeshark|ue5)
                         verify_remote "$name" ;;
        grafana)         verify_runner "$name" uvx "runs via uvx mcp-grafana" ;;
        prometheus)      verify_runner "$name" prometheus-mcp-server "pip CLI entry point" ;;
        te-community)    verify_file "$name" "$TE_COMMUNITY_MCP_DIR/src/server.py" ;;
        te-official)     verify_runner "$name" npx "remote HTTP via npx mcp-remote" ;;
        forward)         verify_dir  "$name" "$FORWARD_MCP_DIR" ;;
        suzieq)          verify_dir  "$name" "$SUZIEQ_MCP_DIR" ;;
        gtrace)          verify_runner "$name" gtrace "standalone Go binary" ;;
        cml)             verify_cmd_or_module "$name" cml-mcp cml_mcp "requires Python 3.12+, pip3 install cml-mcp" ;;
        containerlab)    verify_file "$name" "$CLAB_MCP_DIR/clab_mcp_server.py" ;;
        batfish)         verify_dir  "$name" "$BATFISH_MCP_DIR" ;;
        protocol)        verify_file "$name" "$PROTOCOL_MCP_DIR/server.py" ;;
        servicenow)      verify_file "$name" "$SERVICENOW_MCP_DIR/src/servicenow_mcp/cli.py" ;;
        github)          verify_runner "$name" docker "runs the GitHub MCP Docker image" ;;
        gitlab|msgraph|drawio-rfc)
                         verify_runner "$name" npx "runs via npx" ;;
        packet-buddy)    verify_file "$name" "$PACKET_BUDDY_MCP_DIR/server.py" ;;
        markmap)         verify_file "$name" "$MARKMAP_INNER/dist/index.js" ;;
        uml)             verify_dir  "$name" "$UML_MCP_DIR" ;;
        subnet-calc)     verify_file "$name" "$SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py" ;;
        wikipedia)       verify_file "$name" "$WIKIPEDIA_MCP_DIR/main.py" ;;
        tts)             verify_file "$name" "$TTS_MCP_DIR/server.py" ;;
        twitter)         verify_file "$name" "$TWITTER_MCP_DIR/server.py" ;;
        twilio)          verify_file "$name" "$TWILIO_MCP_DIR/server.py" ;;
        gait)            verify_file "$name" "$GAIT_MCP_DIR/gait_mcp.py" ;;
        mempalace)       verify_file "$name" "$MEMPALACE_MCP_DIR/mempalace/mcp_server.py" ;;
        humanrail)       verify_file "$name" "$HUMANRAIL_MCP_DIR/server.py" ;;
        *)               log_info "$name: configured (no local artifact to check)"
                         SERVERS_OK=$((SERVERS_OK + 1)) ;;
    esac
}

VERIFY_FAILED_COMPONENTS=""
for id in $SELECTED; do
    FAILS_BEFORE=$SERVERS_FAIL
    verify_component "$id"
    if [ "$SERVERS_FAIL" -gt "$FAILS_BEFORE" ]; then
        VERIFY_FAILED_COMPONENTS="$VERIFY_FAILED_COMPONENTS $id"
    fi
done
verify_file "MCP Call Script" "$NETCLAW_DIR/scripts/mcp-call.py"

echo ""
log_info "Verification: $SERVERS_OK OK, $SERVERS_FAIL FAILED"
echo ""

# ═══════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════

log_step "Installation Summary"
echo ""
echo "========================================="
echo "  NetClaw Installation Complete"
echo "========================================="
echo ""

SKILL_COUNT=$(ls -d "$NETCLAW_DIR/workspace/skills/"*/ 2>/dev/null | wc -l | tr -d ' ')

echo "Installed MCP components ($SELECTED_COUNT of $TOTAL_COMPONENTS):"
SEL=" $SELECTED "
LAST_CAT=""
for entry in "${CATALOG[@]}"; do
    IFS='|' read -r id cat name desc <<< "$entry"
    [[ "$SEL" == *" $id "* ]] || continue
    if [ "$cat" != "$LAST_CAT" ]; then
        echo ""
        echo "  $cat:"
        LAST_CAT="$cat"
    fi
    printf '    %-26s %s\n' "$name" "$desc"
done
echo ""

echo "Skills deployed: $SKILL_COUNT → ~/.openclaw/workspace/skills/"
echo "Component manifest: $NETCLAW_MANIFEST"
echo "  (setup.sh only asks about platforms you installed — re-run install.sh to add more)"
echo ""

# ═══════════════════════════════════════════
# DefenseClaw Security Layer (Opt-In)
# ═══════════════════════════════════════════

if tui_is_tty; then
    core_defenseclaw
else
    log_info "Non-interactive shell — skipping the DefenseClaw prompt."
    log_info "Enable later: ./scripts/defenseclaw-enable.sh"
fi

echo ""

# ═══════════════════════════════════════════
# Launch NetClaw Platform Setup
# ═══════════════════════════════════════════

SETUP_SCRIPT="$NETCLAW_DIR/scripts/setup.sh"
if [ -f "$SETUP_SCRIPT" ] && tui_is_tty; then
    echo ""
    echo -e "${CYAN}Now let's configure your network platform credentials.${NC}"
    echo -e "${DIM}Only the platforms you just installed will be offered.${NC}"
    echo ""
    if tui_yesno "Run NetClaw platform setup now?" "y"; then
        bash "$SETUP_SCRIPT"
    else
        echo ""
        log_info "Skipped platform setup. Run it later:"
        echo "  ./scripts/setup.sh"
    fi
fi

echo ""
echo "========================================="
echo "  Next Steps"
echo "========================================="
echo ""
echo "  1. nano testbed/testbed.yaml        # Add your network devices"
echo "  2. openclaw gateway                 # Start the gateway"
echo "  3. openclaw chat --new              # Talk to NetClaw"
echo ""
echo "  Re-run setup anytime:"
echo "    openclaw onboard --install-daemon  # AI provider, gateway, channels"
echo "    ./scripts/setup.sh                 # Network platform credentials"
echo "    ./scripts/install.sh               # Add or remove MCP servers"
echo ""

# ═══════════════════════════════════════════
# Problem report — printed LAST so it can't scroll away behind
# the setup wizard or the summary.
# ═══════════════════════════════════════════

PROBLEM_COMPONENTS="$(printf '%s\n' $FAILED_COMPONENTS $VERIFY_FAILED_COMPONENTS | awk 'NF && !seen[$0]++')"
if [ -n "$PROBLEM_COMPONENTS" ]; then
    PROBLEM_COUNT=$(echo "$PROBLEM_COMPONENTS" | wc -l | tr -d ' ')
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}  ⚠  $PROBLEM_COUNT component(s) did not install cleanly${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    for id in $PROBLEM_COMPONENTS; do
        reason=""
        [[ " $FAILED_COMPONENTS " == *" $id "* ]] && reason="install step reported an error"
        if [[ " $VERIFY_FAILED_COMPONENTS " == *" $id "* ]]; then
            [ -n "$reason" ] && reason="$reason; failed verification" || reason="failed verification"
        fi
        printf "    %-18s %s\n" "$id" "$reason"
        if [ -f "$INSTALL_LOG_DIR/$id.log" ]; then
            # Replay the tail of the error here so nothing depends on scrollback
            grep -aE "\[(ERROR|WARN)\]|[Ee]rror|ERR!|fatal" "$INSTALL_LOG_DIR/$id.log" 2>/dev/null \
                | tail -3 | sed -e 's/\x1b\[[0-9;]*m//g' -e 's/^/        /' || true
            echo "        full log: $INSTALL_LOG_DIR/$id.log"
        fi
    done
    echo ""
    echo "  Everything else installed fine. Retry just these with:"
    echo ""
    echo "    ./scripts/install.sh --add \"$(echo $PROBLEM_COMPONENTS | tr '\n' ' ' | sed 's/ $//')\""
    echo ""
fi
