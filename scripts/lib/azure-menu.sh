#!/usr/bin/env bash
# NetClaw in Azure: TUI step (spec 198 / R10). Sourced by install.sh. Azure is an operator path (docs/NETCLAW-IN-AZURE.md):
# this step shows the warning, runs ONLY the read-only preflight, and prints the exact commands. It never creates a billable
# resource: every billable step needs the owner's explicit go (R10_GO=<phase>) and is ledger-gated ($25 cap, pause at $15).

azure_warning() {
    echo ""
    echo -e "${RED:-}${BOLD:-}"
    cat "$NETCLAW_DIR/scripts/lib/azure_warning.txt"
    echo -e "${NC:-}"
}

azure_deploy_menu() {
    local choice phase codes cidr in myip
    local ids=(p2-single p3-ha)
    local opts=(
        "Azure Border            — one full Border in Canada Central (p2-single)"
        "Azure HA group          — three Borders: Canada Central, East US 2, Sweden Central (p3-ha)"
        "Not now"
    )
    azure_warning
    tui_yesno "I understand this deployment has NO authentication and its URLs must stay private" "n" || { log_info "Skipped Azure deployment."; return 0; }
    tui_menu "NetClaw in Azure: choose a shape" "${opts[@]}" || return 0
    [ "$TUI_CHOICE" -ge "${#ids[@]}" ] && return 0
    phase="${ids[$TUI_CHOICE]}"
    [ "$phase" = p2-single ] && codes="nne1" || codes="nne1 ew1 ase1"
    command -v az >/dev/null 2>&1 || { log_error "Azure CLI not found: https://learn.microsoft.com/cli/azure/install-azure-cli"; return 1; }
    az account show >/dev/null 2>&1 || { log_error "No Azure login. Run: az login"; return 1; }
    myip="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
    read -r -p "Your public address as a /32 for SSH and HTTPS [${myip:+$myip/32}]: " in; cidr="${in:-${myip:+$myip/32}}"
    [ -n "$cidr" ] || { log_error "An address is required; 0.0.0.0/0 is refused."; return 1; }
    log_info "Read-only preflight (creates nothing): subscription, size, quota per region, budget alert, secrets present."
    bash "$NETCLAW_DIR/scripts/ha-r10-preflight.sh" --regions canadacentral,eastus2,swedencentral --size Standard_D2as_v7 --disk-gb 40 || {
        log_warn "Preflight did not report GO; nothing was created."; return 1; }
    echo ""
    log_info "Nothing has been created. To build ${phase} (billable; needs your explicit go and the ledger):"
    echo "  export R10_SSH_ALLOW_CIDR=$cidr R10_AZ_REGION_EW1=eastus2 R10_AZ_REGION_ASE1=swedencentral R10_SIZE=Standard_D2as_v7"
    echo "  export R10_RUN_ID=r10x-\$(date +%Y%m%d) R10_GO=${phase}"
    echo "  bash scripts/ha-r10-run-init.sh \$R10_RUN_ID 8 rg-nc198-${phase}"
    echo "  bash scripts/ha-r10-phase.sh up ${phase} ${codes}"
    echo "  PROVIDER=azure GROUP=az bash scripts/ha-r10-build-group.sh plan"
    log_info "Full guide: docs/NETCLAW-IN-AZURE.md   Tear down: bash scripts/ha-r10-phase.sh down ${phase} ${codes}"
}
