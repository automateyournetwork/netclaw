#!/usr/bin/env bash
# NetClaw Platform Setup
# Configures network platform credentials (runs after openclaw onboard)
#
# This handles the NetClaw-specific stuff that openclaw onboard doesn't:
# - Network platform credentials (NetBox, ServiceNow, ACI, ISE, F5, CatC, NVD)
# - pyATS testbed editing
# - Slack channel mapping / WebEx space mapping
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
echo -e "  AI provider and channels (Slack, WebEx, etc.) were set up by ${BOLD}openclaw onboard${NC}."
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

# --- Nautobot ---
if yesno "Do you have a Nautobot instance? (alternative to NetBox for source of truth)"; then
    echo ""
    echo -e "  Nautobot MCP provides read-only IPAM queries — IP addresses, prefixes, VRF/tenant/site."
    echo -e "  Get your API token from: ${BOLD}Nautobot → Admin → API Tokens${NC}"
    echo ""
    prompt NAUTOBOT_URL_VAL "Nautobot URL (https://nautobot.example.com)" ""
    prompt_secret NAUTOBOT_KEY "Nautobot API Token (read permissions)"
    [ -n "$NAUTOBOT_URL_VAL" ] && set_env "NAUTOBOT_URL" "$NAUTOBOT_URL_VAL"
    [ -n "$NAUTOBOT_KEY" ] && set_env "NAUTOBOT_TOKEN" "$NAUTOBOT_KEY"
    ok "Nautobot configured"
else
    skip "Nautobot"
fi
echo ""

# --- OpsMill Infrahub ---
if yesno "Do you have an OpsMill Infrahub instance? (schema-driven infrastructure source of truth)"; then
    echo ""
    echo -e "  Infrahub MCP provides schema-driven infrastructure queries and safe, branch-isolated changes."
    echo -e "  10 tools: nodes, search, schema, read-only GraphQL, plus writes that land on an auto-created"
    echo -e "  session branch and are submitted as a Proposed Change for human review."
    echo -e "  Tip: pair with the infrahub-skills plugin (npx skills add opsmill/infrahub-skills) for authoring"
    echo -e "  schemas, checks, transforms, and generators."
    echo -e "  Get your API token from: ${BOLD}Infrahub UI → Settings → API Tokens${NC}"
    echo ""
    prompt INFRAHUB_ADDR "Infrahub URL (http://infrahub.example.com:8000)" ""
    prompt_secret INFRAHUB_KEY "Infrahub API Token"
    [ -n "$INFRAHUB_ADDR" ] && set_env "INFRAHUB_ADDRESS" "$INFRAHUB_ADDR"
    [ -n "$INFRAHUB_KEY" ] && set_env "INFRAHUB_API_TOKEN" "$INFRAHUB_KEY"
    ok "OpsMill Infrahub configured"
else
    skip "OpsMill Infrahub"
fi
echo ""

# --- Infoblox DDI ---
if yesno "Do you have an Infoblox DDI platform? (DNS, DHCP, IPAM)"; then
    echo ""
    echo -e "  Infoblox MCP covers DNS records, DHCP scopes and leases, and IPAM utilization."
    echo ""
    prompt INFOBLOX_URL_VAL "Infoblox URL (https://infoblox.example.com)" ""
    prompt_secret INFOBLOX_KEY "Infoblox API Key / Token"
    [ -n "$INFOBLOX_URL_VAL" ] && set_env "INFOBLOX_URL" "$INFOBLOX_URL_VAL"
    [ -n "$INFOBLOX_KEY" ] && set_env "INFOBLOX_API_KEY" "$INFOBLOX_KEY"
    ok "Infoblox DDI configured"
else
    skip "Infoblox DDI"
fi
echo ""

# --- Itential Automation Platform ---
if yesno "Do you have an Itential Automation Platform (IAP) instance? (network automation orchestration)"; then
    echo ""
    echo -e "  Itential MCP provides 65+ tools: config mgmt, compliance, workflows, golden config, lifecycle."
    echo ""
    prompt ITENTIAL_HOST "IAP hostname (itential.example.com)" ""
    prompt ITENTIAL_USER "IAP Username" ""
    prompt_secret ITENTIAL_PASS "IAP Password"
    [ -n "$ITENTIAL_HOST" ] && set_env "ITENTIAL_MCP_PLATFORM_HOST" "$ITENTIAL_HOST"
    [ -n "$ITENTIAL_USER" ] && set_env "ITENTIAL_MCP_PLATFORM_USER" "$ITENTIAL_USER"
    [ -n "$ITENTIAL_PASS" ] && set_env "ITENTIAL_MCP_PLATFORM_PASSWORD" "$ITENTIAL_PASS"
    ok "Itential IAP configured"
else
    skip "Itential IAP"
fi
echo ""

# --- Juniper JunOS ---
if yesno "Do you have Juniper JunOS devices? (PyEZ/NETCONF automation)"; then
    echo ""
    echo -e "  JunOS MCP provides 10 tools: CLI execution, config management, Jinja2 templates, device facts, batch operations."
    echo -e "  Devices are defined in a JSON inventory file (not environment variables)."
    echo ""
    prompt JUNOS_DEVICES "Path to devices.json inventory file" "devices.json"
    [ -n "$JUNOS_DEVICES" ] && set_env "JUNOS_DEVICES_FILE" "$JUNOS_DEVICES"
    ok "Juniper JunOS configured"
else
    skip "Juniper JunOS"
fi
echo ""

# --- Arista CloudVision ---
if yesno "Do you have an Arista CloudVision Portal (CVP) instance? (Arista network management)"; then
    echo ""
    echo -e "  CVP MCP provides 4 tools: device inventory, events, connectivity monitoring, tag management."
    echo -e "  Generate a service account token from: ${BOLD}CVP → Settings → Service Accounts${NC}"
    echo ""
    prompt CVP_HOST "CloudVision hostname (e.g., www.arista.io)" ""
    prompt_secret CVP_TOKEN_VAL "CVP Service Account Token"
    [ -n "$CVP_HOST" ] && set_env "CVP" "$CVP_HOST"
    [ -n "$CVP_TOKEN_VAL" ] && set_env "CVPTOKEN" "$CVP_TOKEN_VAL"
    ok "Arista CloudVision configured"
else
    skip "Arista CloudVision"
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

# --- Cisco NSO ---
if yesno "Do you have a Cisco NSO (Network Services Orchestrator) server?"; then
    echo ""
    echo -e "  NSO MCP connects via RESTCONF API for device config, sync, and services."
    echo ""
    prompt NSO_URL "NSO URL (e.g., https://sandbox-nso-1.cisco.com)" ""
    prompt NSO_USER "NSO username" "admin"
    prompt_secret NSO_PASS "NSO password"
    if [ -n "$NSO_URL" ]; then
        # Parse scheme, host, port from URL
        NSO_SCHEME=$(echo "$NSO_URL" | sed -n 's|^\(https\?\)://.*|\1|p')
        NSO_HOST=$(echo "$NSO_URL" | sed -n 's|^https\?://\([^:/]*\).*|\1|p')
        NSO_PORT_NUM=$(echo "$NSO_URL" | sed -n 's|^https\?://[^:]*:\([0-9]*\).*|\1|p')
        [ -z "$NSO_SCHEME" ] && NSO_SCHEME="https"
        [ -z "$NSO_PORT_NUM" ] && { [ "$NSO_SCHEME" = "https" ] && NSO_PORT_NUM="443" || NSO_PORT_NUM="8080"; }
        set_env "NSO_SCHEME" "$NSO_SCHEME"
        set_env "NSO_ADDRESS" "$NSO_HOST"
        set_env "NSO_PORT" "$NSO_PORT_NUM"
    fi
    [ -n "$NSO_USER" ] && set_env "NSO_USERNAME" "$NSO_USER"
    [ -n "$NSO_PASS" ] && set_env "NSO_PASSWORD" "$NSO_PASS"
    ok "Cisco NSO configured"
else
    skip "Cisco NSO"
fi
echo ""

# --- AWS Cloud ---
if yesno "Do you have an AWS account? (VPC, Transit GW, CloudWatch, IAM, costs)"; then
    echo ""
    echo -e "  AWS MCP servers connect via standard AWS credentials."
    echo -e "  Create an access key at: ${BOLD}https://console.aws.amazon.com/iam/home#/security_credentials${NC}"
    echo -e "  Required: IAM user or role with read access to EC2, VPC, CloudWatch, IAM, CloudTrail, Cost Explorer"
    echo ""
    prompt AWS_KEY "AWS Access Key ID (AKIA...)" ""
    prompt_secret AWS_SECRET "AWS Secret Access Key"
    prompt AWS_REGION_VAL "AWS Region (e.g., us-east-1)" "us-east-1"
    [ -n "$AWS_KEY" ] && set_env "AWS_ACCESS_KEY_ID" "$AWS_KEY"
    [ -n "$AWS_SECRET" ] && set_env "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET"
    [ -n "$AWS_REGION_VAL" ] && set_env "AWS_REGION" "$AWS_REGION_VAL"
    ok "AWS configured"
else
    skip "AWS"
fi
echo ""

# --- Google Cloud Platform ---
if yesno "Do you have a GCP project? (Compute Engine, Cloud Monitoring, Cloud Logging)"; then
    echo ""
    echo -e "  GCP MCP servers are remote HTTP endpoints hosted by Google."
    echo -e "  Auth via service account key or gcloud application-default credentials."
    echo ""
    prompt GCP_PROJECT "GCP Project ID (e.g., my-project-123)" ""
    prompt GCP_SA_KEY "Path to service account key JSON (or leave blank for gcloud auth)" ""
    [ -n "$GCP_PROJECT" ] && set_env "GCP_PROJECT_ID" "$GCP_PROJECT"
    if [ -n "$GCP_SA_KEY" ]; then
        if [ -f "$GCP_SA_KEY" ]; then
            set_env "GOOGLE_APPLICATION_CREDENTIALS" "$GCP_SA_KEY"
            ok "GCP configured (service account key)"
        else
            echo -e "  ${YELLOW}File not found: $GCP_SA_KEY${NC}"
            ok "GCP project set — configure auth later"
        fi
    else
        ok "GCP project set — using gcloud auth (run: gcloud auth application-default login)"
    fi
else
    skip "GCP"
fi
echo ""

# --- Cisco Meraki ---
if yesno "Do you have a Cisco Meraki Dashboard? (wireless, switching, security, cameras)"; then
    echo ""
    echo -e "  Meraki Magic MCP connects to the Meraki Dashboard API (~804 endpoints)."
    echo -e "  Get your API key from: ${BOLD}Dashboard → Organization → Settings → Dashboard API access${NC}"
    echo -e "  Get your Org ID from: ${BOLD}Dashboard → Organization → Overview (URL contains org ID)${NC}"
    echo ""
    prompt_secret MERAKI_KEY "Meraki Dashboard API Key"
    prompt MERAKI_ORG "Meraki Organization ID" ""
    if yesno "Enable read-only mode? (blocks all write operations)" "n"; then
        MERAKI_RO="true"
    else
        MERAKI_RO="false"
    fi
    [ -n "$MERAKI_KEY" ] && set_env "MERAKI_API_KEY" "$MERAKI_KEY"
    [ -n "$MERAKI_ORG" ] && set_env "MERAKI_ORG_ID" "$MERAKI_ORG"
    set_env "READ_ONLY_MODE" "$MERAKI_RO"
    ok "Cisco Meraki configured"
else
    skip "Cisco Meraki"
fi
echo ""

# --- Cisco FMC (Secure Firewall) ---
if yesno "Do you have a Cisco Secure Firewall Management Center (FMC)?"; then
    echo ""
    echo -e "  FMC MCP connects via HTTP to the FMC REST API for firewall policy search."
    echo -e "  Requires FMC with API access enabled."
    echo ""
    prompt FMC_URL "FMC Base URL (https://fmc.example.com)" ""
    prompt FMC_USER "FMC API Username" ""
    prompt_secret FMC_PASS "FMC API Password"
    if yesno "Verify SSL certificate?" "y"; then
        FMC_VERIFY="true"
    else
        FMC_VERIFY="false"
    fi
    [ -n "$FMC_URL" ] && set_env "FMC_BASE_URL" "$FMC_URL"
    [ -n "$FMC_USER" ] && set_env "FMC_USERNAME" "$FMC_USER"
    [ -n "$FMC_PASS" ] && set_env "FMC_PASSWORD" "$FMC_PASS"
    set_env "FMC_VERIFY_SSL" "$FMC_VERIFY"
    ok "Cisco FMC configured"
else
    skip "Cisco FMC"
fi
echo ""

# --- Palo Alto Panorama ---
if yesno "Do you have a Palo Alto Panorama instance?"; then
    echo ""
    echo -e "  Panorama MCP covers device groups, templates, security policy, NAT, and commit validation."
    echo ""
    prompt PANORAMA_HOST "Panorama Hostname (panorama.example.com)" ""
    prompt_secret PANORAMA_KEY "Panorama API Key"
    [ -n "$PANORAMA_HOST" ] && set_env "PANOS_HOSTNAME" "$PANORAMA_HOST"
    [ -n "$PANORAMA_KEY" ] && set_env "PANOS_API_KEY" "$PANORAMA_KEY"
    ok "Palo Alto Panorama configured"
else
    skip "Palo Alto Panorama"
fi
echo ""

# --- FortiManager ---
if yesno "Do you have a FortiManager instance?"; then
    echo ""
    echo -e "  FortiManager MCP covers ADOM inventory, policy packages, object search, and install preview."
    echo ""
    prompt FORTIMANAGER_HOST_VAL "FortiManager Hostname (fortimanager.example.com)" ""
    prompt_secret FORTIMANAGER_TOKEN_VAL "FortiManager API Token"
    [ -n "$FORTIMANAGER_HOST_VAL" ] && set_env "FORTIMANAGER_HOST" "$FORTIMANAGER_HOST_VAL"
    [ -n "$FORTIMANAGER_TOKEN_VAL" ] && set_env "FORTIMANAGER_API_TOKEN" "$FORTIMANAGER_TOKEN_VAL"
    ok "FortiManager configured"
else
    skip "FortiManager"
fi
echo ""

# --- Ansible Automation Platform (AAP) ---
if yesno "Do you have a Red Hat Ansible Automation Platform instance?"; then
    echo ""
    echo -e "  AAP MCP provides 4 servers: Controller (45 tools), EDA (12 tools), ansible-lint (9 tools), Red Hat docs."
    echo -e "  Get your API token from: ${BOLD}AAP → Settings → Tokens → Create (Write scope)${NC}"
    echo ""
    prompt AAP_URL_VAL "AAP Controller API URL (https://aap.example.com/api/controller/v2)" ""
    prompt_secret AAP_TOKEN_VAL "AAP API Token"
    prompt EDA_URL_VAL "EDA API URL (https://aap.example.com/api/eda/v1)" ""
    prompt_secret EDA_TOKEN_VAL "EDA API Token (or same as AAP token)"
    [ -n "$AAP_URL_VAL" ] && set_env "AAP_URL" "$AAP_URL_VAL"
    [ -n "$AAP_TOKEN_VAL" ] && set_env "AAP_TOKEN" "$AAP_TOKEN_VAL"
    [ -n "$EDA_URL_VAL" ] && set_env "EDA_URL" "$EDA_URL_VAL"
    [ -n "$EDA_TOKEN_VAL" ] && set_env "EDA_TOKEN" "$EDA_TOKEN_VAL"
    ok "Ansible Automation Platform configured"
else
    skip "Ansible Automation Platform"
fi
echo ""

# --- Cisco ThousandEyes ---
if yesno "Do you have a Cisco ThousandEyes account? (network monitoring, path visualization, BGP)"; then
    echo ""
    echo -e "  ThousandEyes uses two MCP servers:"
    echo -e "    Community (local, 9 tools) — tests, agents, path vis, dashboards"
    echo -e "    Official (remote, ~20 tools) — alerts, outages, BGP, instant tests, endpoint agents"
    echo -e "  Both use the same API token."
    echo -e "  Get your token from: ${BOLD}ThousandEyes → Account Settings → Users & Roles → OAuth Bearer Token${NC}"
    echo ""
    prompt_secret TE_KEY "ThousandEyes API v7 OAuth Bearer Token"
    [ -n "$TE_KEY" ] && set_env "TE_TOKEN" "$TE_KEY"
    ok "Cisco ThousandEyes configured (both community and official servers)"
else
    skip "Cisco ThousandEyes"
fi
echo ""

# --- Cisco RADKit ---
if yesno "Do you have a Cisco RADKit service instance? (cloud-relayed remote device access)"; then
    echo ""
    echo -e "  RADKit provides cloud-relayed access to on-premises network devices."
    echo -e "  Your RADKit service must be running and devices onboarded."
    echo -e "  Auth: certificate-based identity (generated during RADKit onboarding)."
    echo ""
    prompt RADKIT_ID "RADKit Identity (your email address)" ""
    prompt RADKIT_SERIAL "RADKit Service Serial (service instance identifier)" ""
    [ -n "$RADKIT_ID" ] && set_env "RADKIT_IDENTITY" "$RADKIT_ID"
    [ -n "$RADKIT_SERIAL" ] && set_env "RADKIT_DEFAULT_SERVICE_SERIAL" "$RADKIT_SERIAL"
    ok "Cisco RADKit configured"
    echo -e "  ${DIM}Note: Certificate files are auto-detected from ~/.radkit/identities/${NC}"
    echo -e "  ${DIM}For container deployment, set RADKIT_CERT_B64, RADKIT_KEY_B64, RADKIT_CA_B64${NC}"
else
    skip "Cisco RADKit"
fi
echo ""

# --- ContainerLab ---
if yesno "Do you have a ContainerLab API server running?"; then
    echo ""
    echo -e "  ContainerLab MCP lets NetClaw deploy and manage containerized network labs."
    echo -e "  Requires a running ContainerLab API server (clab-api-server)."
    echo ""
    echo -e "  ${BOLD}Prerequisite:${NC} A Linux user must exist on the ContainerLab host."
    echo -e "  The API server authenticates via PAM. Run this on the clab host first:"
    echo ""
    echo -e "    ${DIM}sudo groupadd -f clab_admins && sudo groupadd -f clab_api${NC}"
    echo -e "    ${DIM}sudo useradd -m -s /bin/bash netclaw 2>/dev/null || true${NC}"
    echo -e "    ${DIM}sudo usermod -aG clab_admins netclaw && sudo passwd netclaw${NC}"
    echo ""
    echo -e "  ${BOLD}If clab-api-server runs in Docker:${NC} restart it after creating the user:"
    echo -e "    ${DIM}docker restart clab-api-server${NC}"
    echo ""
    prompt CLAB_URL "ContainerLab API Server URL" "http://localhost:8080"
    prompt CLAB_USER "ContainerLab Username" "netclaw"
    prompt_secret CLAB_PASS "ContainerLab Password"
    [ -n "$CLAB_URL" ] && set_env "CLAB_API_SERVER_URL" "$CLAB_URL"
    [ -n "$CLAB_USER" ] && set_env "CLAB_API_USERNAME" "$CLAB_USER"
    [ -n "$CLAB_PASS" ] && set_env "CLAB_API_PASSWORD" "$CLAB_PASS"
    ok "ContainerLab configured"
else
    skip "ContainerLab"
fi
echo ""

# --- HumanRail ---
if yesno "Do you have a HumanRail account? (human-in-the-loop escalation for AI agents — free while in beta)"; then
    echo ""
    echo -e "  HumanRail routes agent decisions to human engineers when confidence is low,"
    echo -e "  a destructive operation needs sign-off, or an ambiguous ticket needs triage."
    echo -e "  Workers are paid via Lightning Network. Free while building the network."
    echo -e "  Get your API key at: ${BOLD}https://humanrail.dev${NC}"
    echo ""
    prompt_secret HR_KEY "HumanRail API Key (ek_live_... or ek_test_...)"
    prompt HR_URL "HumanRail MCP URL" "http://127.0.0.1:8100/mcp"
    [ -n "$HR_KEY" ] && set_env "HUMANRAIL_API_KEY" "$HR_KEY"
    [ -n "$HR_URL" ] && set_env "HUMANRAIL_MCP_URL" "$HR_URL"
    ok "HumanRail configured"
else
    skip "HumanRail"
fi
echo ""

# --- Cisco WebEx ---
if yesno "Do you have a Cisco WebEx account? (alerts, incidents, reports via WebEx spaces)"; then
    echo ""
    echo -e "  WebEx skills let NetClaw post alerts, manage incidents, and deliver reports to WebEx spaces."
    echo -e "  Create a Bot at: ${BOLD}https://developer.webex.com/my-apps${NC} → Create a New App → Bot"
    echo -e "  The bot token is long-lived (does not expire)."
    echo ""
    prompt_secret WEBEX_TOKEN "WebEx Bot Access Token"
    [ -n "$WEBEX_TOKEN" ] && set_env "WEBEX_BOT_TOKEN" "$WEBEX_TOKEN"
    echo ""
    echo -e "  ${DIM}Optional: Pre-configure default WebEx spaces for alert routing.${NC}"
    echo -e "  ${DIM}Get Room IDs from: WebEx Developer API → Rooms → List Rooms${NC}"
    echo ""
    prompt WEBEX_ALERTS "Alerts Space Room ID (for CRITICAL/HIGH alerts)" ""
    prompt WEBEX_REPORTS "Reports Space Room ID (for scheduled reports)" ""
    [ -n "$WEBEX_ALERTS" ] && set_env "WEBEX_ALERTS_ROOM_ID" "$WEBEX_ALERTS"
    [ -n "$WEBEX_REPORTS" ] && set_env "WEBEX_REPORTS_ROOM_ID" "$WEBEX_REPORTS"
    echo ""
    echo -e "  ${BOLD}Bidirectional WebEx (inbound @mentions):${NC}"
    echo -e "  To receive messages FROM WebEx, you need a public webhook URL."
    echo -e "  Development: ${BOLD}ngrok http 18789${NC} → copy the https URL"
    echo -e "  Production:  your public HTTPS domain"
    echo -e "  The webhook path is: {base_url}/webhooks/webex/default"
    echo ""
    prompt WEBEX_WEBHOOK "Webhook URL (e.g. https://abc123.ngrok-free.app/webhooks/webex/default)" ""
    [ -n "$WEBEX_WEBHOOK" ] && set_env "WEBEX_WEBHOOK_URL" "$WEBEX_WEBHOOK"
    prompt WEBEX_SECRET "Webhook Secret (optional, for HMAC signature verification)" ""
    [ -n "$WEBEX_SECRET" ] && set_env "WEBEX_WEBHOOK_SECRET" "$WEBEX_SECRET"
    ok "Cisco WebEx configured (outbound + inbound)"
else
    skip "Cisco WebEx"
fi
echo ""

# ───────────────────────────────────────────
# Twilio Voice
# ───────────────────────────────────────────

echo -e "${BOLD}Twilio Voice Integration${NC}"
echo "  Bidirectional voice calling: emergency alerts, on-demand status, inbound commands"
echo ""
if yesno "Configure Twilio Voice?"; then
    echo ""
    echo -e "  Get credentials from ${CYAN}https://console.twilio.com${NC}"
    echo "  1. Account → Account SID (starts with AC)"
    echo "  2. Account → API Keys → Create Key"
    echo "     - Save API Key SID (starts with SK)"
    echo "     - Save API Key Secret"
    echo "  3. Phone Numbers → Buy a number (for inbound calls)"
    echo ""
    prompt TWILIO_SID "Account SID (ACxxxxxxxx)" ""
    set_env "TWILIO_ACCOUNT_SID" "$TWILIO_SID"
    prompt TWILIO_KEY "API Key SID (SKxxxxxxxx)" ""
    set_env "TWILIO_API_KEY_SID" "$TWILIO_KEY"
    prompt_secret TWILIO_SECRET "API Key Secret"
    set_env "TWILIO_API_SECRET" "$TWILIO_SECRET"
    prompt TWILIO_PHONE "Twilio Phone Number (+1XXXXXXXXXX)" ""
    set_env "TWILIO_PHONE_NUMBER" "$TWILIO_PHONE"
    echo ""
    echo -e "  For inbound calls, you need a public webhook URL."
    echo -e "  Development: ${CYAN}ngrok http 5001${NC}"
    echo -e "  Production:  your public HTTPS domain"
    echo -e "  The webhook path is: {base_url}/webhooks/twilio/voice"
    echo ""
    prompt TWILIO_WEBHOOK "Webhook URL (e.g. https://abc123.ngrok-free.app/webhooks/twilio/voice)" ""
    [ -n "$TWILIO_WEBHOOK" ] && set_env "TWILIO_WEBHOOK_URL" "$TWILIO_WEBHOOK"
    echo ""
    echo -e "  ${BOLD}Claude AI Integration (Full Agentic Mode)${NC}"
    echo "  For intelligent voice commands, provide your Anthropic API key."
    echo -e "  Get one from ${CYAN}https://console.anthropic.com/settings/keys${NC}"
    echo ""
    prompt_secret ANTHROPIC_KEY "Anthropic API Key (sk-ant-...) [optional]"
    [ -n "$ANTHROPIC_KEY" ] && set_env "ANTHROPIC_API_KEY" "$ANTHROPIC_KEY"
    echo ""
    echo -e "  ${BOLD}Whitelist Configuration${NC}"
    echo "  Only whitelisted numbers can receive/make calls."
    prompt TWILIO_WHITELIST_PHONE "Your mobile number (+1XXXXXXXXXX)" ""
    prompt TWILIO_WHITELIST_NAME "Label for this number" "John Mobile"
    if [ -n "$TWILIO_WHITELIST_PHONE" ]; then
        # Create config directory if needed
        mkdir -p "$NETCLAW_DIR/config"
        TWILIO_CONFIG="$NETCLAW_DIR/config/twilio-voice.json"
        cat > "$TWILIO_CONFIG" << TWILIOEOF
{
  "whitelist": [
    {
      "phone_number": "$TWILIO_WHITELIST_PHONE",
      "label": "$TWILIO_WHITELIST_NAME",
      "can_receive_calls": true,
      "can_initiate_calls": true,
      "added_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "added_by": "setup.sh"
    }
  ],
  "quiet_hours": [
    {
      "id": "default",
      "start_time": "22:00",
      "end_time": "07:00",
      "timezone": "America/Toronto",
      "days_of_week": [],
      "p1_override": true,
      "enabled": true
    }
  ],
  "emergency_categories": [
    {
      "category_name": "pagerduty_p1",
      "description": "PagerDuty P1 Critical Incidents",
      "source": "pagerduty",
      "match_pattern": "severity:P1",
      "enabled": true
    },
    {
      "category_name": "core_device_down",
      "description": "Core router, firewall, or WAN link failure",
      "source": "netclaw_monitoring",
      "match_pattern": "device_type:(core_router|firewall|wan_link) AND status:down",
      "enabled": true
    }
  ],
  "rate_limits": {
    "hourly_max": 3,
    "daily_max": 10
  },
  "voice": "Polly.Matthew"
}
TWILIOEOF
        ok "Whitelist configured: $TWILIO_WHITELIST_NAME ($TWILIO_WHITELIST_PHONE)"
    fi
    ok "Twilio Voice configured"
else
    skip "Twilio Voice"
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
grep -q "^NAUTOBOT_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Nautobot" || skip "Nautobot"
grep -q "^INFRAHUB_ADDRESS=" "$OPENCLAW_ENV" 2>/dev/null && ok "OpsMill Infrahub" || skip "OpsMill Infrahub"
grep -q "^INFOBLOX_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && ok "Infoblox DDI" || skip "Infoblox DDI"
grep -q "^ITENTIAL_MCP_PLATFORM_HOST=" "$OPENCLAW_ENV" 2>/dev/null && ok "Itential IAP" || skip "Itential IAP"
grep -q "^JUNOS_DEVICES_FILE=" "$OPENCLAW_ENV" 2>/dev/null && ok "Juniper JunOS" || skip "Juniper JunOS"
grep -q "^CVP=" "$OPENCLAW_ENV" 2>/dev/null && ok "Arista CloudVision" || skip "Arista CloudVision"
grep -q "^SERVICENOW_INSTANCE_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "ServiceNow" || skip "ServiceNow"
grep -q "^APIC_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco ACI" || skip "Cisco ACI"
grep -q "^ISE_BASE=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco ISE" || skip "Cisco ISE"
grep -q "^F5_IP_ADDRESS=" "$OPENCLAW_ENV" 2>/dev/null && ok "F5 BIG-IP" || skip "F5 BIG-IP"
grep -q "^CCC_HOST=" "$OPENCLAW_ENV" 2>/dev/null && ok "Catalyst Center" || skip "Catalyst Center"
grep -q "^NVD_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && ok "NVD CVE Scanning" || skip "NVD CVE Scanning"
grep -q "^AZURE_TENANT_ID=" "$OPENCLAW_ENV" 2>/dev/null && ok "Microsoft Graph (Office 365)" || skip "Microsoft Graph (Office 365)"
grep -q "^GITHUB_PERSONAL_ACCESS_TOKEN=" "$OPENCLAW_ENV" 2>/dev/null && ok "GitHub" || skip "GitHub"
grep -q "^CML_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco CML" || skip "Cisco CML"
grep -q "^NSO_ADDRESS=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco NSO" || skip "Cisco NSO"
grep -q "^AWS_ACCESS_KEY_ID=" "$OPENCLAW_ENV" 2>/dev/null && ok "AWS Cloud" || skip "AWS Cloud"
grep -q "^GCP_PROJECT_ID=" "$OPENCLAW_ENV" 2>/dev/null && ok "Google Cloud" || skip "Google Cloud"
grep -q "^MERAKI_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco Meraki" || skip "Cisco Meraki"
grep -q "^FMC_BASE_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco FMC" || skip "Cisco FMC"
grep -q "^PANOS_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && ok "Palo Alto Panorama" || skip "Palo Alto Panorama"
grep -q "^FORTIMANAGER_API_TOKEN=" "$OPENCLAW_ENV" 2>/dev/null && ok "FortiManager" || skip "FortiManager"
grep -q "^AAP_TOKEN=" "$OPENCLAW_ENV" 2>/dev/null && ok "Ansible Automation Platform" || skip "Ansible Automation Platform"
grep -q "^TE_TOKEN=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco ThousandEyes" || skip "Cisco ThousandEyes"
grep -q "^RADKIT_IDENTITY=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco RADKit" || skip "Cisco RADKit"
[ -d "$NETCLAW_DIR/mcp-servers/uml-mcp" ] && ok "UML Diagrams (Kroki — no credentials required)" || skip "UML Diagrams"
grep -q "^CLAB_API_SERVER_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "ContainerLab" || skip "ContainerLab"
grep -q "^VMANAGE_IP=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco SD-WAN" || skip "Cisco SD-WAN"
grep -q "^GRAFANA_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Grafana" || skip "Grafana"
grep -q "^PROMETHEUS_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Prometheus" || skip "Prometheus"
grep -q "^KUBESHARK_MCP_URL=" "$OPENCLAW_ENV" 2>/dev/null && ok "Kubeshark" || skip "Kubeshark"
grep -q "^NETCLAW_ROUTER_ID=" "$OPENCLAW_ENV" 2>/dev/null && ok "Protocol Participation (BGP/OSPF/GRE)" || skip "Protocol Participation"
grep -q "^HUMANRAIL_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && ok "HumanRail (human-in-the-loop escalation)" || skip "HumanRail"
grep -q "^WEBEX_BOT_TOKEN=" "$OPENCLAW_ENV" 2>/dev/null && ok "Cisco WebEx" || skip "Cisco WebEx"
grep -q "^TWILIO_ACCOUNT_SID=" "$OPENCLAW_ENV" 2>/dev/null && ok "Twilio Voice" || skip "Twilio Voice"

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
