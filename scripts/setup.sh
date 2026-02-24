#!/usr/bin/env bash
# NetClaw Platform Setup
# Configures network platform credentials (runs after openclaw onboard)
#
# This handles the NetClaw-specific stuff that openclaw onboard doesn't:
# - Network platform credentials (NetBox, ServiceNow, ACI, ISE, F5, CatC, NVD)
# - pyATS testbed editing
# - Slack channel mapping
# - USER.md personalization
#
# AI provider, gateway, and channel connections are handled by:
#   openclaw onboard        (first time)
#   openclaw configure      (reconfigure)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_ENV="$OPENCLAW_DIR/.env"

# ───────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────

prompt() {
    local var="$1" prompt_text="$2" default="${3:-}"
    if [ -n "$default" ]; then
        echo -ne "${CYAN}${prompt_text}${NC} ${DIM}[${default}]${NC}: "
    else
        echo -ne "${CYAN}${prompt_text}${NC}: "
    fi
    read -r input
    eval "$var=\"${input:-$default}\""
}

prompt_secret() {
    local var="$1" prompt_text="$2"
    echo -ne "${CYAN}${prompt_text}${NC}: "
    read -rs input
    echo ""
    eval "$var=\"$input\""
}

yesno() {
    local prompt_text="$1" default="${2:-n}"
    local yn
    if [ "$default" = "y" ]; then
        echo -ne "${CYAN}${prompt_text}${NC} ${DIM}[Y/n]${NC}: "
    else
        echo -ne "${CYAN}${prompt_text}${NC} ${DIM}[y/N]${NC}: "
    fi
    read -r yn
    yn="${yn:-$default}"
    [[ "$yn" =~ ^[Yy] ]]
}

set_env() {
    local key="$1" value="$2"
    [ -z "$value" ] && return
    if grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$OPENCLAW_ENV"
    elif grep -q "^# ${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        sed -i "s|^# ${key}=.*|${key}=${value}|" "$OPENCLAW_ENV"
    else
        echo "${key}=${value}" >> "$OPENCLAW_ENV"
    fi
}

section() {
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════${NC}"
    echo -e "${BOLD}  $1${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════${NC}"
    echo ""
}

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
skip() { echo -e "  ${DIM}– $1 (skipped)${NC}"; }

# ───────────────────────────────────────────
# Preflight
# ───────────────────────────────────────────

if [ ! -d "$OPENCLAW_DIR" ]; then
    echo -e "${RED}Error: ~/.openclaw not found. Run install.sh first.${NC}"
    exit 1
fi

[ -f "$OPENCLAW_ENV" ] || touch "$OPENCLAW_ENV"

# ───────────────────────────────────────────
# Welcome
# ───────────────────────────────────────────

echo ""
echo -e "${BOLD}    NetClaw Platform Setup${NC}"
echo ""
echo -e "  Configure your network platform credentials."
echo -e "  AI provider and Slack were set up by ${BOLD}openclaw onboard${NC}."
echo -e "  Re-run anytime: ${BOLD}./scripts/setup.sh${NC}"
echo ""
echo -e "  ${DIM}All credentials are stored in ~/.openclaw/.env (never committed to git)${NC}"

# ═══════════════════════════════════════════
# Step 1: Network Devices (pyATS)
# ═══════════════════════════════════════════

section "Step 1: Network Devices"

echo "  NetClaw uses pyATS to connect to Cisco devices via SSH."
echo "  Your device inventory goes in testbed/testbed.yaml."
echo ""

if yesno "Open testbed.yaml in your editor now?"; then
    EDITOR="${EDITOR:-nano}"
    "$EDITOR" "$NETCLAW_DIR/testbed/testbed.yaml"
    ok "Testbed edited"
else
    skip "Testbed editing (edit testbed/testbed.yaml later)"
fi

# ═══════════════════════════════════════════
# Step 2: Network Platforms
# ═══════════════════════════════════════════

section "Step 2: Network Platforms"

echo "  Which platforms do you have? NetClaw will only enable what you select."
echo "  You can always re-run this to add more later."
echo ""

# --- NetBox ---
if yesno "Do you have a NetBox instance?"; then
    echo ""
    prompt NETBOX_URL "NetBox URL (https://netbox.example.com)" ""
    prompt_secret NETBOX_TOKEN "NetBox API Token"
    [ -n "$NETBOX_URL" ] && set_env "NETBOX_URL" "$NETBOX_URL"
    [ -n "$NETBOX_TOKEN" ] && set_env "NETBOX_TOKEN" "$NETBOX_TOKEN"
    ok "NetBox configured"
else
    skip "NetBox"
fi
echo ""

# --- ServiceNow ---
if yesno "Do you have a ServiceNow instance?"; then
    echo ""
    prompt SNOW_URL "ServiceNow Instance URL (https://xxx.service-now.com)" ""
    prompt SNOW_USER "ServiceNow Username" ""
    prompt_secret SNOW_PASS "ServiceNow Password"
    [ -n "$SNOW_URL" ] && set_env "SERVICENOW_INSTANCE_URL" "$SNOW_URL"
    [ -n "$SNOW_USER" ] && set_env "SERVICENOW_USERNAME" "$SNOW_USER"
    [ -n "$SNOW_PASS" ] && set_env "SERVICENOW_PASSWORD" "$SNOW_PASS"
    ok "ServiceNow configured"
else
    skip "ServiceNow"
fi
echo ""

# --- Cisco ACI ---
if yesno "Do you have a Cisco ACI fabric (APIC)?"; then
    echo ""
    prompt APIC_URL "APIC URL (https://apic.example.com)" ""
    prompt APIC_USER "APIC Username" "admin"
    prompt_secret APIC_PASS "APIC Password"
    [ -n "$APIC_URL" ] && set_env "APIC_URL" "$APIC_URL"
    [ -n "$APIC_USER" ] && set_env "APIC_USERNAME" "$APIC_USER"
    [ -n "$APIC_PASS" ] && set_env "APIC_PASSWORD" "$APIC_PASS"
    ok "Cisco ACI configured"
else
    skip "Cisco ACI"
fi
echo ""

# --- Cisco ISE ---
if yesno "Do you have Cisco ISE with ERS API enabled?"; then
    echo ""
    prompt ISE_BASE "ISE Base URL (https://ise.example.com)" ""
    prompt ISE_USER "ISE ERS Username" ""
    prompt_secret ISE_PASS "ISE ERS Password"
    [ -n "$ISE_BASE" ] && set_env "ISE_BASE" "$ISE_BASE"
    [ -n "$ISE_USER" ] && set_env "ISE_USERNAME" "$ISE_USER"
    [ -n "$ISE_PASS" ] && set_env "ISE_PASSWORD" "$ISE_PASS"
    ok "Cisco ISE configured"
else
    skip "Cisco ISE"
fi
echo ""

# --- F5 BIG-IP ---
if yesno "Do you have an F5 BIG-IP load balancer?"; then
    echo ""
    prompt F5_IP "F5 Management IP/Hostname" ""
    prompt F5_USER "F5 Username" "admin"
    prompt_secret F5_PASS "F5 Password"
    if [ -n "$F5_IP" ]; then
        set_env "F5_IP_ADDRESS" "$F5_IP"
    fi
    if [ -n "$F5_USER" ] && [ -n "$F5_PASS" ]; then
        F5_AUTH=$(echo -n "${F5_USER}:${F5_PASS}" | base64)
        set_env "F5_AUTH_STRING" "$F5_AUTH"
        ok "F5 BIG-IP configured (auth string base64-encoded)"
    fi
else
    skip "F5 BIG-IP"
fi
echo ""

# --- Catalyst Center ---
if yesno "Do you have Cisco Catalyst Center (DNA Center)?"; then
    echo ""
    prompt CCC_HOST "Catalyst Center Hostname/IP" ""
    prompt CCC_USER "Catalyst Center Username" "admin"
    prompt_secret CCC_PWD "Catalyst Center Password"
    [ -n "$CCC_HOST" ] && set_env "CCC_HOST" "$CCC_HOST"
    [ -n "$CCC_USER" ] && set_env "CCC_USER" "$CCC_USER"
    [ -n "$CCC_PWD" ] && set_env "CCC_PWD" "$CCC_PWD"
    ok "Catalyst Center configured"
else
    skip "Catalyst Center"
fi
echo ""

# --- NVD CVE ---
if yesno "Do you want CVE vulnerability scanning? (free NVD API key)"; then
    echo ""
    echo -e "  Get a free API key from: ${BOLD}https://nvd.nist.gov/developers/request-an-api-key${NC}"
    echo ""
    prompt_secret NVD_KEY "NVD API Key"
    if [ -n "$NVD_KEY" ]; then
        set_env "NVD_API_KEY" "$NVD_KEY"
        ok "NVD CVE scanning configured"
    else
        skip "NVD API key (CVE scanning will work without it, just rate-limited)"
    fi
else
    skip "NVD CVE scanning"
fi

# --- Microsoft Graph (Office 365) ---
if yesno "Do you have a Microsoft 365 tenant? (Visio, SharePoint, Teams, OneDrive)"; then
    echo ""
    echo -e "  Microsoft Graph MCP requires an Azure AD app registration."
    echo -e "  Register at: ${BOLD}https://portal.azure.com → Azure Active Directory → App registrations${NC}"
    echo ""
    echo -e "  Required API permissions (Application type):"
    echo -e "    ${DIM}Files.ReadWrite.All${NC}   — Visio files on OneDrive/SharePoint"
    echo -e "    ${DIM}Sites.ReadWrite.All${NC}   — SharePoint document libraries"
    echo -e "    ${DIM}ChannelMessage.Send${NC}   — Post to Teams channels"
    echo -e "    ${DIM}User.Read${NC}             — Basic profile"
    echo ""
    prompt AZURE_TENANT "Azure Tenant ID" ""
    prompt AZURE_CLIENT "Azure Client ID (Application ID)" ""
    prompt_secret AZURE_SECRET "Azure Client Secret"
    [ -n "$AZURE_TENANT" ] && set_env "AZURE_TENANT_ID" "$AZURE_TENANT"
    [ -n "$AZURE_CLIENT" ] && set_env "AZURE_CLIENT_ID" "$AZURE_CLIENT"
    [ -n "$AZURE_SECRET" ] && set_env "AZURE_CLIENT_SECRET" "$AZURE_SECRET"
    ok "Microsoft Graph (Office 365) configured"
else
    skip "Microsoft Graph (Office 365)"
fi
echo ""

# --- GitHub ---
if yesno "Do you have a GitHub account? (issues, PRs, config-as-code)"; then
    echo ""
    echo -e "  Create a Personal Access Token at: ${BOLD}https://github.com/settings/tokens${NC}"
    echo -e "  Recommended scopes: ${DIM}repo, read:org, read:user, workflow${NC}"
    echo ""
    prompt_secret GH_PAT "GitHub Personal Access Token (ghp_...)"
    if [ -n "$GH_PAT" ]; then
        set_env "GITHUB_PERSONAL_ACCESS_TOKEN" "$GH_PAT"
        ok "GitHub configured"
    else
        skip "GitHub PAT (no token provided)"
    fi
else
    skip "GitHub"
fi
echo ""

# --- Cisco Modeling Labs (CML) ---
if yesno "Do you have a Cisco Modeling Labs (CML) server?"; then
    echo ""
    echo -e "  CML MCP lets you build and manage network labs via natural language."
    echo -e "  Requires CML 2.9+ with API access."
    echo ""
    prompt CML_URL "CML Server URL (https://cml.example.com)" ""
    prompt CML_USER "CML Username" "admin"
    prompt_secret CML_PASS "CML Password"
    if yesno "Verify SSL certificate?" "y"; then
        CML_VERIFY="true"
    else
        CML_VERIFY="false"
    fi
    [ -n "$CML_URL" ] && set_env "CML_URL" "$CML_URL"
    [ -n "$CML_USER" ] && set_env "CML_USERNAME" "$CML_USER"
    [ -n "$CML_PASS" ] && set_env "CML_PASSWORD" "$CML_PASS"
    set_env "CML_VERIFY_SSL" "$CML_VERIFY"
    ok "Cisco CML configured"
else
    skip "Cisco CML"
fi
echo ""

# ═══════════════════════════════════════════
# Step 3: Your Identity
# ═══════════════════════════════════════════

section "Step 3: About You"

echo "  Help NetClaw work better by telling it about yourself."
echo "  This goes into USER.md (never leaves your machine)."
echo ""

prompt USER_NAME "Your name" ""
prompt USER_ROLE "Your role (e.g., Network Engineer, NetOps Lead)" "Network Engineer"
prompt USER_TZ "Your timezone (e.g., US/Eastern, UTC)" ""

USER_MD="$OPENCLAW_DIR/workspace/USER.md"
if [ -n "$USER_NAME" ] || [ -n "$USER_ROLE" ] || [ -n "$USER_TZ" ]; then
    cat > "$USER_MD" << USEREOF
# About My Human

## Identity
- **Name:** ${USER_NAME:-[your name]}
- **Role:** ${USER_ROLE:-Network Engineer}
- **Timezone:** ${USER_TZ:-[your timezone]}

## Preferences
- Communication style: technical, direct
- Output format: structured tables and bullet points preferred
- Change management: always require ServiceNow CR before config changes
- Escalation: alert me for P1/P2, queue P3/P4 for next business day

## Network
- Edit TOOLS.md with your device IPs, sites, and Slack channels
- Edit testbed/testbed.yaml with your pyATS device inventory
USEREOF
    ok "USER.md personalized"
fi

# ═══════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════

section "Setup Complete"

echo "  Platform credentials saved to: ~/.openclaw/.env"
echo ""
echo "  What's configured:"

grep -q "^NETBOX_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "NetBox" || skip "NetBox"
grep -q "^SERVICENOW_INSTANCE_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "ServiceNow" || skip "ServiceNow"
grep -q "^APIC_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco ACI" || skip "Cisco ACI"
grep -q "^ISE_BASE=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco ISE" || skip "Cisco ISE"
grep -q "^F5_IP_ADDRESS=" "$OPENCLAW_ENV" 2>/dev/null && ok "F5 BIG-IP" || skip "F5 BIG-IP"
grep -q "^CCC_HOST=" "$OPENCLAW_ENV" 2>/dev/null && ok "Catalyst Center" || skip "Catalyst Center"
grep -q "^NVD_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && ok "NVD CVE Scanning" || skip "NVD CVE Scanning"
grep -q "^AZURE_TENANT_ID=" "$OPENCLAW_ENV" 2>/dev/null && ok "Microsoft Graph (Office 365)" || skip "Microsoft Graph (Office 365)"
grep -q "^GITHUB_PERSONAL_ACCESS_TOKEN=" "$OPENCLAW_ENV" 2>/dev/null && ok "GitHub" || skip "GitHub"
grep -q "^CML_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco CML" || skip "Cisco CML"

echo ""
echo -e "  ${BOLD}Ready to go:${NC}"
echo ""
echo -e "    ${CYAN}openclaw gateway${NC}          # Terminal 1"
echo -e "    ${CYAN}openclaw chat --new${NC}       # Terminal 2"
echo ""
echo -e "  Reconfigure anytime:"
echo -e "    ${CYAN}openclaw configure${NC}        # AI provider, gateway, channels"
echo -e "    ${CYAN}./scripts/setup.sh${NC}        # Network platform credentials"
echo ""
