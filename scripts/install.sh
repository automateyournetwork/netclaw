#!/usr/bin/env bash
# NetClaw Installation Script
# Clones, builds, and configures all MCP servers for the NetClaw CCIE agent

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_DIR="$NETCLAW_DIR/mcp-servers"
TOTAL_STEPS=19

echo "========================================="
echo "  NetClaw - CCIE Network Agent"
echo "  Full Installation"
echo "========================================="
echo ""
echo "  Project: $NETCLAW_DIR"
echo ""

# ═══════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════

log_step "1/$TOTAL_STEPS Checking prerequisites..."

MISSING=0

if ! check_command node; then
    log_error "Node.js is required (>= 18). Install from https://nodejs.org/"
    MISSING=1
else
    NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        log_error "Node.js >= 18 required. Found: $(node --version)"
        MISSING=1
    else
        log_info "Node.js version: $(node --version)"
    fi
fi

for cmd in npm npx python3 git; do
    if ! check_command "$cmd"; then
        MISSING=1
    fi
done

if ! check_command pip3; then
    if ! check_command pip; then
        log_error "pip3 is required for Python package installation"
        MISSING=1
    fi
fi

if [ "$MISSING" -eq 1 ]; then
    log_error "Missing prerequisites. Please install them and re-run this script."
    exit 1
fi

log_info "All prerequisites satisfied."
echo ""

# ═══════════════════════════════════════════
# Step 2: Install OpenClaw
# ═══════════════════════════════════════════

log_step "2/$TOTAL_STEPS Installing OpenClaw..."

if command -v openclaw &> /dev/null; then
    log_info "OpenClaw already installed: $(openclaw --version 2>/dev/null || echo 'version unknown')"
else
    log_info "Installing OpenClaw via npm..."
    npm install -g openclaw@latest
    if command -v openclaw &> /dev/null; then
        log_info "OpenClaw installed successfully"
    else
        log_warn "openclaw not found on PATH after install"
        log_warn "Try: export PATH=\"$(npm config get prefix)/bin:\$PATH\""
    fi
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: Create mcp-servers directory
# ═══════════════════════════════════════════

log_step "3/$TOTAL_STEPS Setting up MCP servers directory..."

mkdir -p "$MCP_DIR"
log_info "MCP servers directory: $MCP_DIR"
echo ""

# ═══════════════════════════════════════════
# Step 4: pyATS MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "4/$TOTAL_STEPS Installing pyATS MCP Server..."
echo "  Source: https://github.com/automateyournetwork/pyATS_MCP"

PYATS_MCP_DIR="$MCP_DIR/pyATS_MCP"
clone_or_pull "$PYATS_MCP_DIR" "https://github.com/automateyournetwork/pyATS_MCP.git"

log_info "Installing Python dependencies..."
pip3 install -r "$PYATS_MCP_DIR/requirements.txt" 2>/dev/null || \
    pip3 install "pyats[full]" mcp pydantic python-dotenv

[ -f "$PYATS_MCP_DIR/pyats_mcp_server.py" ] && \
    log_info "pyATS MCP ready: $PYATS_MCP_DIR/pyats_mcp_server.py" || \
    log_error "pyats_mcp_server.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 5: Markmap MCP (clone + npm build)
# ═══════════════════════════════════════════

log_step "5/$TOTAL_STEPS Installing Markmap MCP Server..."
echo "  Source: https://github.com/automateyournetwork/markmap_mcp"

MARKMAP_MCP_DIR="$MCP_DIR/markmap_mcp"
clone_or_pull "$MARKMAP_MCP_DIR" "https://github.com/automateyournetwork/markmap_mcp.git"

MARKMAP_INNER="$MARKMAP_MCP_DIR/markmap-mcp"
if [ -d "$MARKMAP_INNER" ]; then
    log_info "Building Markmap MCP..."
    cd "$MARKMAP_INNER" && npm install && npm run build && cd "$NETCLAW_DIR"
    log_info "Markmap MCP ready: node $MARKMAP_INNER/dist/index.js"
else
    log_warn "Nested markmap-mcp/ not found, trying top-level..."
    cd "$MARKMAP_MCP_DIR" && npm install && npm run build && cd "$NETCLAW_DIR"
fi

echo ""

# ═══════════════════════════════════════════
# Step 6: GAIT MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "6/$TOTAL_STEPS Installing GAIT MCP Server..."
echo "  Source: https://github.com/automateyournetwork/gait_mcp"

GAIT_MCP_DIR="$MCP_DIR/gait_mcp"
clone_or_pull "$GAIT_MCP_DIR" "https://github.com/automateyournetwork/gait_mcp.git"

log_info "Installing GAIT dependencies..."
pip3 install mcp fastmcp gait-ai 2>/dev/null || log_warn "Some GAIT deps failed"

[ -f "$GAIT_MCP_DIR/gait_mcp.py" ] && \
    log_info "GAIT MCP ready: $GAIT_MCP_DIR/gait_mcp.py (runs via gait-stdio.py wrapper)" || \
    log_error "gait_mcp.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 7: NetBox MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "7/$TOTAL_STEPS Installing NetBox MCP Server..."
echo "  Source: https://github.com/netboxlabs/netbox-mcp-server"

NETBOX_MCP_DIR="$MCP_DIR/netbox-mcp-server"
clone_or_pull "$NETBOX_MCP_DIR" "https://github.com/netboxlabs/netbox-mcp-server.git"

log_info "Installing NetBox dependencies..."
pip3 install httpx "fastmcp>=2.14.0,<3" requests pydantic pydantic-settings 2>/dev/null || \
    log_warn "Some NetBox deps failed"

log_info "NetBox MCP ready: python3 -m netbox_mcp_server.server"

echo ""

# ═══════════════════════════════════════════
# Step 8: ServiceNow MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "8/$TOTAL_STEPS Installing ServiceNow MCP Server..."
echo "  Source: https://github.com/echelon-ai-labs/servicenow-mcp"

SERVICENOW_MCP_DIR="$MCP_DIR/servicenow-mcp"
clone_or_pull "$SERVICENOW_MCP_DIR" "https://github.com/echelon-ai-labs/servicenow-mcp.git"

log_info "Installing ServiceNow dependencies..."
pip3 install "mcp[cli]>=1.3.0" requests "pydantic>=2.0.0" python-dotenv starlette uvicorn httpx PyYAML 2>/dev/null || \
    log_warn "Some ServiceNow deps failed"

log_info "ServiceNow MCP ready"

echo ""

# ═══════════════════════════════════════════
# Step 9: ACI MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "9/$TOTAL_STEPS Installing Cisco ACI MCP Server..."
echo "  Source: https://github.com/automateyournetwork/ACI_MCP"

ACI_MCP_DIR="$MCP_DIR/ACI_MCP"
clone_or_pull "$ACI_MCP_DIR" "https://github.com/automateyournetwork/ACI_MCP.git"

log_info "Installing ACI dependencies..."
pip3 install requests pydantic python-dotenv fastmcp 2>/dev/null || \
    log_warn "Some ACI deps failed"

[ -f "$ACI_MCP_DIR/aci_mcp/main.py" ] && \
    log_info "ACI MCP ready: $ACI_MCP_DIR/aci_mcp/main.py" || \
    log_error "aci_mcp/main.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 10: ISE MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "10/$TOTAL_STEPS Installing Cisco ISE MCP Server..."
echo "  Source: https://github.com/automateyournetwork/ISE_MCP"

ISE_MCP_DIR="$MCP_DIR/ISE_MCP"
clone_or_pull "$ISE_MCP_DIR" "https://github.com/automateyournetwork/ISE_MCP.git"

log_info "Installing ISE dependencies..."
pip3 install pydantic python-dotenv fastmcp httpx aiocache aiolimiter 2>/dev/null || \
    log_warn "Some ISE deps failed"

[ -f "$ISE_MCP_DIR/src/ise_mcp_server/server.py" ] && \
    log_info "ISE MCP ready: $ISE_MCP_DIR/src/ise_mcp_server/server.py" || \
    log_error "ISE server.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 11: Wikipedia MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "11/$TOTAL_STEPS Installing Wikipedia MCP Server..."
echo "  Source: https://github.com/automateyournetwork/Wikipedia_MCP"

WIKIPEDIA_MCP_DIR="$MCP_DIR/Wikipedia_MCP"
clone_or_pull "$WIKIPEDIA_MCP_DIR" "https://github.com/automateyournetwork/Wikipedia_MCP.git"

log_info "Installing Wikipedia dependencies..."
pip3 install fastmcp wikipedia pydantic 2>/dev/null || \
    log_warn "Some Wikipedia deps failed"

[ -f "$WIKIPEDIA_MCP_DIR/main.py" ] && \
    log_info "Wikipedia MCP ready: $WIKIPEDIA_MCP_DIR/main.py" || \
    log_error "Wikipedia main.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 12: NVD CVE MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "12/$TOTAL_STEPS Installing NVD CVE MCP Server..."
echo "  Source: https://github.com/marcoeg/mcp-nvd"

NVD_MCP_DIR="$MCP_DIR/mcp-nvd"
clone_or_pull "$NVD_MCP_DIR" "https://github.com/marcoeg/mcp-nvd.git"

log_info "Installing NVD dependencies..."
cd "$NVD_MCP_DIR" && pip3 install -e . 2>/dev/null && cd "$NETCLAW_DIR" || \
    log_warn "NVD MCP install failed"

log_info "NVD CVE MCP ready: python3 -m mcp_nvd.main"

echo ""

# ═══════════════════════════════════════════
# Step 13: Subnet Calculator MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "13/$TOTAL_STEPS Installing Subnet Calculator MCP Server..."
echo "  Source: https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension"

SUBNET_MCP_DIR="$MCP_DIR/subnet-calculator-mcp"
clone_or_pull "$SUBNET_MCP_DIR" "https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension.git"

log_info "Installing Subnet Calculator dependencies..."
pip3 install pydantic python-dotenv mcp 2>/dev/null || \
    log_warn "Some Subnet Calculator deps failed"

[ -f "$SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py" ] && \
    log_info "Subnet Calculator MCP ready: $SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py" || \
    log_error "subnetcalculator_mcp.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 14: F5 BIG-IP MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "14/$TOTAL_STEPS Installing F5 BIG-IP MCP Server..."
echo "  Source: https://github.com/czirakim/F5.MCP.server"

F5_MCP_DIR="$MCP_DIR/f5-mcp-server"
clone_or_pull "$F5_MCP_DIR" "https://github.com/czirakim/F5.MCP.server.git"

log_info "Installing F5 dependencies..."
pip3 install -r "$F5_MCP_DIR/requirements.txt" 2>/dev/null || \
    pip3 install requests mcp python-dotenv

[ -f "$F5_MCP_DIR/F5MCPserver.py" ] && \
    log_info "F5 MCP ready: $F5_MCP_DIR/F5MCPserver.py" || \
    log_error "F5MCPserver.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 15: Catalyst Center MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "15/$TOTAL_STEPS Installing Catalyst Center MCP Server..."
echo "  Source: https://github.com/richbibby/catalyst-center-mcp"

CATC_MCP_DIR="$MCP_DIR/catalyst-center-mcp"
clone_or_pull "$CATC_MCP_DIR" "https://github.com/richbibby/catalyst-center-mcp.git"

log_info "Installing Catalyst Center dependencies..."
pip3 install -r "$CATC_MCP_DIR/requirements.txt" 2>/dev/null || \
    pip3 install fastmcp requests urllib3 python-dotenv

[ -f "$CATC_MCP_DIR/catalyst-center-mcp.py" ] && \
    log_info "Catalyst Center MCP ready: $CATC_MCP_DIR/catalyst-center-mcp.py" || \
    log_error "catalyst-center-mcp.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 16: npx MCP servers (Draw.io, RFC)
# ═══════════════════════════════════════════

log_step "16/$TOTAL_STEPS Caching npx-based MCP servers..."

for pkg in "@drawio/mcp" "@mjpitz/mcp-rfc"; do
    log_info "Pre-caching $pkg..."
    npm cache add "$pkg" 2>/dev/null || log_warn "Could not pre-cache $pkg"
done

echo ""

# ═══════════════════════════════════════════
# Step 17: Deploy skills and set environment
# ═══════════════════════════════════════════

log_step "17/$TOTAL_STEPS Deploying skills and configuration..."

PYATS_SCRIPT="$PYATS_MCP_DIR/pyats_mcp_server.py"
TESTBED_PATH="$NETCLAW_DIR/testbed/testbed.yaml"

# Deploy skills to OpenClaw workspace
OPENCLAW_DIR="$HOME/.openclaw"
if [ -d "$OPENCLAW_DIR" ]; then
    mkdir -p "$OPENCLAW_DIR/workspace/skills"
    cp -r "$NETCLAW_DIR/workspace/skills/"* "$OPENCLAW_DIR/workspace/skills/"
    log_info "Deployed skills to $OPENCLAW_DIR/workspace/skills/"

    # Deploy OpenClaw workspace MD files (SOUL, AGENTS, IDENTITY, USER, TOOLS, HEARTBEAT)
    for mdfile in SOUL.md AGENTS.md IDENTITY.md USER.md TOOLS.md HEARTBEAT.md; do
        if [ -f "$NETCLAW_DIR/$mdfile" ]; then
            cp "$NETCLAW_DIR/$mdfile" "$OPENCLAW_DIR/workspace/$mdfile"
            log_info "Deployed $mdfile to workspace"
        fi
    done
    log_info "Deployed workspace files to $OPENCLAW_DIR/workspace/"

    # Set ALL environment variables in OpenClaw .env
    OPENCLAW_ENV="$OPENCLAW_DIR/.env"
    [ -f "$OPENCLAW_ENV" ] || touch "$OPENCLAW_ENV"

    declare -A ENV_VARS=(
        ["PYATS_TESTBED_PATH"]="$TESTBED_PATH"
        ["PYATS_MCP_SCRIPT"]="$PYATS_SCRIPT"
        ["MCP_CALL"]="$NETCLAW_DIR/scripts/mcp-call.py"
        ["MARKMAP_MCP_SCRIPT"]="$MARKMAP_INNER/dist/index.js"
        ["GAIT_MCP_SCRIPT"]="$NETCLAW_DIR/scripts/gait-stdio.py"
        ["NETBOX_MCP_SCRIPT"]="$NETBOX_MCP_DIR/src/netbox_mcp_server/server.py"
        ["SERVICENOW_MCP_SCRIPT"]="$SERVICENOW_MCP_DIR/src/servicenow_mcp/cli.py"
        ["ACI_MCP_SCRIPT"]="$ACI_MCP_DIR/aci_mcp/main.py"
        ["ISE_MCP_SCRIPT"]="$ISE_MCP_DIR/src/ise_mcp_server/server.py"
        ["WIKIPEDIA_MCP_SCRIPT"]="$WIKIPEDIA_MCP_DIR/main.py"
        ["NVD_MCP_SCRIPT"]="$NVD_MCP_DIR/mcp_nvd/main.py"
        ["SUBNET_MCP_SCRIPT"]="$SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py"
        ["F5_MCP_SCRIPT"]="$F5_MCP_DIR/F5MCPserver.py"
        ["CATC_MCP_SCRIPT"]="$CATC_MCP_DIR/catalyst-center-mcp.py"
    )

    for key in "${!ENV_VARS[@]}"; do
        if grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
            sed -i "s|^${key}=.*|${key}=${ENV_VARS[$key]}|" "$OPENCLAW_ENV"
        else
            echo "${key}=${ENV_VARS[$key]}" >> "$OPENCLAW_ENV"
        fi
    done

    log_info "Set ${#ENV_VARS[@]} environment variables in $OPENCLAW_ENV"
else
    log_warn "OpenClaw directory not found at $OPENCLAW_DIR"
    log_warn "Run 'openclaw onboard --install-daemon' first"
fi

# Create .env if it doesn't exist
ENV_FILE="$NETCLAW_DIR/.env"
if [ ! -f "$ENV_FILE" ] && [ -f "$NETCLAW_DIR/.env.example" ]; then
    cp "$NETCLAW_DIR/.env.example" "$ENV_FILE"
    log_info "Created .env from template"
    log_warn "Edit $ENV_FILE with your actual credentials"
fi

echo ""

# ═══════════════════════════════════════════
# Step 18: Verify installation
# ═══════════════════════════════════════════

log_step "18/$TOTAL_STEPS Verifying installation..."

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

verify_file "pyATS MCP" "$PYATS_MCP_DIR/pyats_mcp_server.py"
verify_file "Markmap MCP" "$MARKMAP_INNER/dist/index.js"
verify_file "GAIT MCP" "$GAIT_MCP_DIR/gait_mcp.py"
verify_file "GAIT stdio wrapper" "$NETCLAW_DIR/scripts/gait-stdio.py"
verify_file "NetBox MCP" "$NETBOX_MCP_DIR/src/netbox_mcp_server/server.py"
verify_file "ServiceNow MCP" "$SERVICENOW_MCP_DIR/src/servicenow_mcp/cli.py"
verify_file "ACI MCP" "$ACI_MCP_DIR/aci_mcp/main.py"
verify_file "ISE MCP" "$ISE_MCP_DIR/src/ise_mcp_server/server.py"
verify_file "Wikipedia MCP" "$WIKIPEDIA_MCP_DIR/main.py"
verify_file "NVD CVE MCP" "$NVD_MCP_DIR/mcp_nvd/main.py"
verify_file "Subnet Calculator MCP" "$SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py"
verify_file "F5 BIG-IP MCP" "$F5_MCP_DIR/F5MCPserver.py"
verify_file "Catalyst Center MCP" "$CATC_MCP_DIR/catalyst-center-mcp.py"
verify_file "MCP Call Script" "$NETCLAW_DIR/scripts/mcp-call.py"

echo ""
log_info "Verification: $SERVERS_OK OK, $SERVERS_FAIL FAILED"
echo ""

# ═══════════════════════════════════════════
# Step 19: Summary
# ═══════════════════════════════════════════

log_step "19/$TOTAL_STEPS Installation Summary"
echo ""
echo "========================================="
echo "  NetClaw Installation Complete"
echo "========================================="
echo ""

SKILL_COUNT=$(ls -d "$NETCLAW_DIR/workspace/skills/"*/ 2>/dev/null | wc -l)

echo "MCP Servers Installed (15):"
echo "  ┌─────────────────────────────────────────────────────────────"
echo "  │ NETWORK DEVICE AUTOMATION:"
echo "  │   pyATS              Cisco device CLI, Genie parsers"
echo "  │   F5 BIG-IP          iControl REST API (virtuals, pools, iRules)"
echo "  │   Catalyst Center    DNA Center / CatC API (devices, clients, sites)"
echo "  │"
echo "  │ INFRASTRUCTURE PLATFORMS:"
echo "  │   Cisco ACI           APIC / ACI fabric management"
echo "  │   Cisco ISE           Identity, posture, TrustSec"
echo "  │   NetBox              DCIM/IPAM source of truth (read-only)"
echo "  │   ServiceNow          ITSM: incidents, changes, CMDB"
echo "  │"
echo "  │ SECURITY & COMPLIANCE:"
echo "  │   NVD CVE             NIST vulnerability database (Python)"
echo "  │"
echo "  │ UTILITIES:"
echo "  │   Subnet Calculator   IPv4 + IPv6 CIDR calculator"
echo "  │   GAIT                Git-based AI audit trail"
echo "  │   Wikipedia           Technology context & history"
echo "  │   Markmap             Mind map visualization"
echo "  │"
echo "  │ NPX (no install):"
echo "  │   Draw.io             Network topology diagrams"
echo "  │   RFC                 IETF standards reference"
echo "  └─────────────────────────────────────────────────────────────"
echo ""
echo "Skills Deployed ($SKILL_COUNT):"
echo "  ┌─────────────────────────────────────────────────────────────"
echo "  │ pyATS Skills:"
echo "  │   pyats-network          Core device automation (8 MCP tools)"
echo "  │   pyats-health-check     CPU, memory, interfaces, NTP + NetBox"
echo "  │   pyats-routing          OSPF, BGP, EIGRP, IS-IS analysis"
echo "  │   pyats-security         Security audit + ISE + NVD CVE"
echo "  │   pyats-topology         Discovery + NetBox reconciliation"
echo "  │   pyats-config-mgmt      Change control + ServiceNow + GAIT"
echo "  │   pyats-troubleshoot     OSI-layer troubleshooting"
echo "  │   pyats-dynamic-test     pyATS aetest script generation"
echo "  │   pyats-parallel-ops     Fleet-wide pCall operations"
echo "  │"
echo "  │ F5 BIG-IP Skills:"
echo "  │   f5-health-check        Virtual server & pool monitoring"
echo "  │   f5-config-mgmt         Safe F5 object lifecycle"
echo "  │   f5-troubleshoot        F5 troubleshooting workflows"
echo "  │"
echo "  │ Catalyst Center Skills:"
echo "  │   catc-inventory         Device inventory & site management"
echo "  │   catc-client-ops        Client monitoring & analytics"
echo "  │   catc-troubleshoot      CatC troubleshooting workflows"
echo "  │"
echo "  │ Domain Skills:"
echo "  │   netbox-reconcile       Source of truth drift detection"
echo "  │   aci-fabric-audit       ACI fabric health & policy audit"
echo "  │   aci-change-deploy      Safe ACI policy changes"
echo "  │   ise-posture-audit      ISE posture & TrustSec audit"
echo "  │   ise-incident-response  Endpoint investigation & quarantine"
echo "  │   servicenow-change-workflow  Full ITSM change lifecycle"
echo "  │   gait-session-tracking  Mandatory audit trail"
echo "  │"
echo "  │ Reference & Utility Skills:"
echo "  │   nvd-cve                NVD vulnerability search (Python)"
echo "  │   subnet-calculator      IPv4 + IPv6 subnet calculator"
echo "  │   wikipedia-research     Protocol history & context"
echo "  │   markmap-viz            Mind map visualization"
echo "  │   drawio-diagram         Draw.io network diagrams"
echo "  │   rfc-lookup             IETF RFC search"
echo "  │"
echo "  │ Slack Integration Skills:"
echo "  │   slack-network-alerts   Alert formatting & delivery"
echo "  │   slack-report-delivery  Report formatting for Slack"
echo "  │   slack-incident-workflow Incident response in Slack"
echo "  │   slack-user-context     User-aware interactions"
echo "  └─────────────────────────────────────────────────────────────"
echo ""

log_info "Next steps:"
echo "  1. Edit .env with your credentials:"
echo "     - PYATS_TESTBED_PATH (network devices)"
echo "     - NVD_API_KEY (NVD vulnerability database)"
echo "     - NETBOX_URL, NETBOX_TOKEN (NetBox)"
echo "     - SERVICENOW_INSTANCE_URL, USERNAME, PASSWORD (ServiceNow)"
echo "     - APIC_URL, USERNAME, PASSWORD (Cisco ACI)"
echo "     - ISE_BASE, USERNAME, PASSWORD (Cisco ISE)"
echo "     - F5_IP_ADDRESS, F5_AUTH_STRING (F5 BIG-IP)"
echo "     - CCC_HOST, CCC_USER, CCC_PWD (Catalyst Center)"
echo "  2. Edit testbed/testbed.yaml with your network devices"
echo "  3. Restart the gateway: openclaw gateway"
echo "  4. Chat: openclaw chat"
echo ""
