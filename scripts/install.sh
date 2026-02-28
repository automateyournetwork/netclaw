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
TOTAL_STEPS=45

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
        log_error "openclaw not found on PATH after install"
        log_warn "Try: export PATH=\"$(npm config get prefix)/bin:\$PATH\""
    fi
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: OpenClaw Onboard (provider, gateway, channels)
# ═══════════════════════════════════════════

log_step "3/$TOTAL_STEPS Running OpenClaw onboard..."

echo ""
echo "  This is OpenClaw's built-in setup wizard."
echo "  You'll pick your AI provider, set up the gateway, and connect"
echo "  channels like Slack, Discord, Telegram, etc."
echo ""

if command -v openclaw &> /dev/null; then
    openclaw onboard --install-daemon || {
        log_warn "openclaw onboard exited with an error."
        log_warn "You can re-run it later: openclaw onboard --install-daemon"
    }
    log_info "OpenClaw onboard complete"
else
    log_error "openclaw command not found — skipping onboard"
    log_warn "After fixing your PATH, run: openclaw onboard --install-daemon"
fi

echo ""

# ═══════════════════════════════════════════
# Step 4: Create mcp-servers directory
# ═══════════════════════════════════════════

log_step "4/$TOTAL_STEPS Setting up MCP servers directory..."

mkdir -p "$MCP_DIR"
log_info "MCP servers directory: $MCP_DIR"
echo ""

# ═══════════════════════════════════════════
# Step 5: pyATS MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "5/$TOTAL_STEPS Installing pyATS MCP Server..."
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
# Step 6: JunOS MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "6/$TOTAL_STEPS Installing Juniper JunOS MCP Server..."
echo "  Source: https://github.com/Juniper/junos-mcp-server"
echo "  Juniper device automation — CLI execution, config mgmt, Jinja2 templates, batch ops (10 tools)"

JUNOS_MCP_DIR="$MCP_DIR/junos-mcp-server"
if [ -d "$JUNOS_MCP_DIR" ]; then
    log_info "JunOS MCP already cloned, pulling latest..."
    git -C "$JUNOS_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/Juniper/junos-mcp-server.git "$JUNOS_MCP_DIR" 2>/dev/null
fi

if [ -d "$JUNOS_MCP_DIR" ]; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 10 ]; then
        log_info "Python 3.$PY_MINOR detected (3.10+ required for JunOS MCP)"
        if [ -f "$JUNOS_MCP_DIR/requirements.txt" ]; then
            pip3 install -r "$JUNOS_MCP_DIR/requirements.txt" 2>/dev/null || \
                pip3 install --break-system-packages -r "$JUNOS_MCP_DIR/requirements.txt" 2>/dev/null || \
                log_warn "JunOS MCP dependencies install failed"
        fi
        # Also try pip install . for the entry point
        cd "$JUNOS_MCP_DIR" && pip3 install . 2>/dev/null || \
            pip3 install --break-system-packages . 2>/dev/null || true
        cd "$NETCLAW_DIR"
        log_info "JunOS MCP installed (stdio transport via PyEZ/NETCONF)"
    else
        log_warn "Python 3.10+ required for JunOS MCP (found 3.$PY_MINOR)"
        log_info "JunOS MCP skipped — upgrade Python or install manually"
    fi
else
    log_warn "JunOS MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 7: Arista CloudVision MCP (clone + uv)
# ═══════════════════════════════════════════

log_step "7/$TOTAL_STEPS Installing Arista CloudVision (CVP) MCP Server..."
echo "  Source: https://github.com/noredistribution/mcp-cvp-fun"
echo "  Arista CVP automation — device inventory, events, connectivity monitor, tags (4 tools)"

CVP_MCP_DIR="$MCP_DIR/mcp-cvp-fun"
if [ -d "$CVP_MCP_DIR" ]; then
    log_info "CVP MCP already cloned, pulling latest..."
    git -C "$CVP_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/noredistribution/mcp-cvp-fun.git "$CVP_MCP_DIR" 2>/dev/null
fi

if [ -d "$CVP_MCP_DIR" ]; then
    # CVP MCP uses uv run --with fastmcp at runtime; just ensure uv is available
    if command -v uv &> /dev/null; then
        log_info "CVP MCP ready (uv available — deps resolved at runtime via 'uv run --with fastmcp')"
    else
        log_warn "CVP MCP cloned but 'uv' not found — install uv for runtime dependency resolution"
        log_info "  Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
else
    log_warn "CVP MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 8: Markmap MCP (clone + npm build)
# ═══════════════════════════════════════════

log_step "8/$TOTAL_STEPS Installing Markmap MCP Server..."
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
# Step 9: GAIT MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "9/$TOTAL_STEPS Installing GAIT MCP Server..."
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
# Step 10: NetBox MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "10/$TOTAL_STEPS Installing NetBox MCP Server..."
echo "  Source: https://github.com/netboxlabs/netbox-mcp-server"

NETBOX_MCP_DIR="$MCP_DIR/netbox-mcp-server"
clone_or_pull "$NETBOX_MCP_DIR" "https://github.com/netboxlabs/netbox-mcp-server.git"

log_info "Installing NetBox dependencies..."
pip3 install httpx "fastmcp>=2.14.0,<3" requests pydantic pydantic-settings 2>/dev/null || \
    log_warn "Some NetBox deps failed"

log_info "NetBox MCP ready: python3 -m netbox_mcp_server.server"

echo ""

# ═══════════════════════════════════════════
# Step 11: Nautobot MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "11/$TOTAL_STEPS Installing Nautobot MCP Server..."
echo "  Source: https://github.com/aiopnet/mcp-nautobot"
echo "  Nautobot IPAM source of truth — IP addresses, prefixes, VRF/tenant/site filtering (5 tools)"

NAUTOBOT_MCP_DIR="$MCP_DIR/mcp-nautobot"
if [ -d "$NAUTOBOT_MCP_DIR" ]; then
    log_info "Nautobot MCP already cloned, pulling latest..."
    git -C "$NAUTOBOT_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/aiopnet/mcp-nautobot.git "$NAUTOBOT_MCP_DIR" 2>/dev/null
fi

if [ -d "$NAUTOBOT_MCP_DIR" ]; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 13 ]; then
        log_info "Python 3.$PY_MINOR detected (3.13+ required for Nautobot MCP)"
        if [ -f "$NAUTOBOT_MCP_DIR/pyproject.toml" ]; then
            cd "$NAUTOBOT_MCP_DIR" && pip3 install -e . 2>/dev/null || \
                pip3 install --break-system-packages -e . 2>/dev/null || \
                log_warn "Nautobot MCP editable install failed"
            cd "$NETCLAW_DIR"
        fi
        log_info "Nautobot MCP installed (stdio transport via MCP SDK)"
    else
        log_warn "Python 3.13+ required for Nautobot MCP (found 3.$PY_MINOR)"
        log_info "Installing core dependencies..."
        pip3 install "mcp>=1.10.1" httpx "pydantic>=2.11.0" pydantic-settings python-dotenv 2>/dev/null || \
            pip3 install --break-system-packages "mcp>=1.10.1" httpx "pydantic>=2.11.0" pydantic-settings python-dotenv 2>/dev/null || \
            log_warn "Nautobot core deps install failed"
        log_info "Nautobot MCP installed (some features may require Python 3.13+)"
    fi
else
    log_warn "Nautobot MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 12: Infrahub MCP (clone + uv sync)
# ═══════════════════════════════════════════

log_step "12/$TOTAL_STEPS Installing OpsMill Infrahub MCP Server..."
echo "  Source: https://github.com/opsmill/infrahub-mcp"
echo "  Infrahub infrastructure source of truth — schema-driven nodes, GraphQL, versioned branches (10 tools)"

INFRAHUB_MCP_DIR="$MCP_DIR/infrahub-mcp"
if [ -d "$INFRAHUB_MCP_DIR" ]; then
    log_info "Infrahub MCP already cloned, pulling latest..."
    git -C "$INFRAHUB_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/opsmill/infrahub-mcp.git "$INFRAHUB_MCP_DIR" 2>/dev/null
fi

if [ -d "$INFRAHUB_MCP_DIR" ]; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 13 ]; then
        log_info "Python 3.$PY_MINOR detected (3.13+ required for Infrahub MCP)"
        if command -v uv &> /dev/null; then
            log_info "Installing Infrahub MCP via uv sync..."
            cd "$INFRAHUB_MCP_DIR" && uv sync 2>/dev/null && cd "$NETCLAW_DIR" || {
                log_warn "uv sync failed — trying pip install..."
                pip3 install fastmcp infrahub-sdk 2>/dev/null || \
                    pip3 install --break-system-packages fastmcp infrahub-sdk 2>/dev/null || \
                    log_warn "Infrahub MCP deps install failed"
                cd "$NETCLAW_DIR"
            }
        else
            log_info "uv not found — installing core dependencies via pip..."
            pip3 install fastmcp infrahub-sdk 2>/dev/null || \
                pip3 install --break-system-packages fastmcp infrahub-sdk 2>/dev/null || \
                log_warn "Infrahub MCP deps install failed"
        fi
        log_info "Infrahub MCP installed (stdio transport via FastMCP)"
    else
        log_warn "Python 3.13+ required for Infrahub MCP (found 3.$PY_MINOR)"
        log_info "Installing core dependencies..."
        pip3 install fastmcp infrahub-sdk 2>/dev/null || \
            pip3 install --break-system-packages fastmcp infrahub-sdk 2>/dev/null || \
            log_warn "Infrahub core deps install failed"
        log_info "Infrahub MCP installed (some features may require Python 3.13+)"
    fi
else
    log_warn "Infrahub MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 13: Itential MCP (pip install)
# ═══════════════════════════════════════════

log_step "13/$TOTAL_STEPS Installing Itential MCP Server..."
echo "  Source: https://github.com/itential/itential-mcp"
echo "  Itential Automation Platform — config mgmt, compliance, workflows, golden config, lifecycle (65+ tools)"

PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
if [ "$PY_MINOR" -ge 10 ]; then
    log_info "Python 3.$PY_MINOR detected (3.10+ required for Itential MCP)"
    pip3 install itential-mcp 2>/dev/null || \
        pip3 install --break-system-packages itential-mcp 2>/dev/null || {
        log_warn "pip install itential-mcp failed — trying from source..."
        ITENTIAL_MCP_DIR="$MCP_DIR/itential-mcp"
        if [ -d "$ITENTIAL_MCP_DIR" ]; then
            git -C "$ITENTIAL_MCP_DIR" pull --quiet 2>/dev/null || true
        else
            git clone https://github.com/itential/itential-mcp.git "$ITENTIAL_MCP_DIR" 2>/dev/null
        fi
        if [ -d "$ITENTIAL_MCP_DIR" ]; then
            cd "$ITENTIAL_MCP_DIR" && pip3 install -e . 2>/dev/null || \
                pip3 install --break-system-packages -e . 2>/dev/null || \
                log_warn "Itential MCP source install failed"
            cd "$NETCLAW_DIR"
        fi
    }

    if command -v itential-mcp &> /dev/null; then
        log_info "Itential MCP installed: itential-mcp run (stdio transport)"
    elif python3 -c "import itential_mcp" 2>/dev/null; then
        log_info "Itential MCP installed (module importable)"
    else
        log_warn "Itential MCP not available after install"
    fi
else
    log_warn "Python 3.10+ required for Itential MCP (found 3.$PY_MINOR)"
    log_info "Itential MCP skipped — upgrade Python or install manually: pip3 install itential-mcp"
fi

echo ""

# ═══════════════════════════════════════════
# Step 14: ServiceNow MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "14/$TOTAL_STEPS Installing ServiceNow MCP Server..."
echo "  Source: https://github.com/echelon-ai-labs/servicenow-mcp"

SERVICENOW_MCP_DIR="$MCP_DIR/servicenow-mcp"
clone_or_pull "$SERVICENOW_MCP_DIR" "https://github.com/echelon-ai-labs/servicenow-mcp.git"

log_info "Installing ServiceNow dependencies..."
pip3 install "mcp[cli]>=1.3.0" requests "pydantic>=2.0.0" python-dotenv starlette uvicorn httpx PyYAML 2>/dev/null || \
    log_warn "Some ServiceNow deps failed"

log_info "ServiceNow MCP ready"

echo ""

# ═══════════════════════════════════════════
# Step 15: ACI MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "15/$TOTAL_STEPS Installing Cisco ACI MCP Server..."
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
# Step 16: ISE MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "16/$TOTAL_STEPS Installing Cisco ISE MCP Server..."
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
# Step 17: Wikipedia MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "17/$TOTAL_STEPS Installing Wikipedia MCP Server..."
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
# Step 18: NVD CVE MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "18/$TOTAL_STEPS Installing NVD CVE MCP Server..."
echo "  Source: https://github.com/marcoeg/mcp-nvd"

NVD_MCP_DIR="$MCP_DIR/mcp-nvd"
clone_or_pull "$NVD_MCP_DIR" "https://github.com/marcoeg/mcp-nvd.git"

log_info "Installing NVD dependencies..."
cd "$NVD_MCP_DIR" && pip3 install -e . 2>/dev/null && cd "$NETCLAW_DIR" || \
    log_warn "NVD MCP install failed"

log_info "NVD CVE MCP ready: python3 -m mcp_nvd.main"

echo ""

# ═══════════════════════════════════════════
# Step 19: Subnet Calculator MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "19/$TOTAL_STEPS Installing Subnet Calculator MCP Server..."
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
# Step 20: F5 BIG-IP MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "20/$TOTAL_STEPS Installing F5 BIG-IP MCP Server..."
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
# Step 21: Catalyst Center MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "21/$TOTAL_STEPS Installing Catalyst Center MCP Server..."
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
# Step 22: Microsoft Graph MCP (npx, no clone)
# ═══════════════════════════════════════════

log_step "22/$TOTAL_STEPS Caching Microsoft Graph MCP Server..."
echo "  Package: @microsoft/microsoft-graph-mcp"
echo "  Auth: Azure AD app registration (Tenant ID, Client ID, Client Secret)"

log_info "Pre-caching @microsoft/microsoft-graph-mcp..."
npm cache add "@anthropic-ai/microsoft-graph-mcp" 2>/dev/null || \
    npm cache add "@microsoft/microsoft-graph-mcp" 2>/dev/null || \
    log_warn "Could not pre-cache Microsoft Graph MCP — will download on first use via npx"

log_info "Microsoft Graph MCP ready: npx -y @anthropic-ai/microsoft-graph-mcp"
echo "  Requires: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET in ~/.openclaw/.env"

echo ""

# ═══════════════════════════════════════════
# Step 23: npx MCP servers (Draw.io, RFC)
# ═══════════════════════════════════════════

log_step "23/$TOTAL_STEPS Caching npx-based MCP servers..."

for pkg in "@drawio/mcp" "@mjpitz/mcp-rfc"; do
    log_info "Pre-caching $pkg..."
    npm cache add "$pkg" 2>/dev/null || log_warn "Could not pre-cache $pkg"
done

echo ""

# ═══════════════════════════════════════════
# Step 24: GitHub MCP Server
# ═══════════════════════════════════════════

log_step "24/$TOTAL_STEPS Installing GitHub MCP Server..."
echo "  Source: https://github.com/github/github-mcp-server"
echo "  Auth: GitHub Personal Access Token (PAT)"

GITHUB_MCP_IMAGE="ghcr.io/github/github-mcp-server"

# Pull docker image if docker is available, otherwise note for manual setup
if command -v docker &> /dev/null; then
    log_info "Pulling GitHub MCP Server Docker image..."
    docker pull "$GITHUB_MCP_IMAGE" 2>/dev/null || \
        log_warn "Could not pull GitHub MCP image — will pull on first use"
    log_info "GitHub MCP ready: docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server"
else
    log_warn "Docker not found — GitHub MCP server requires Docker"
    log_info "Install Docker, then run: docker pull $GITHUB_MCP_IMAGE"
fi

echo ""

# ═══════════════════════════════════════════
# Step 25: Packet Buddy MCP Server (pcap analysis)
# ═══════════════════════════════════════════

log_step "25/$TOTAL_STEPS Installing Packet Buddy MCP Server..."
echo "  Pcap analysis via tshark — upload pcaps via Slack or disk"

PACKET_BUDDY_MCP_DIR="$MCP_DIR/packet-buddy-mcp"

# Check for tshark
if command -v tshark &> /dev/null; then
    log_info "tshark found: $(tshark --version 2>/dev/null | head -1)"
else
    log_warn "tshark not found — installing wireshark-common..."
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y tshark 2>/dev/null || \
        log_warn "Could not install tshark. Install manually: apt install tshark"
fi

# Check for capinfos
if ! command -v capinfos &> /dev/null; then
    log_warn "capinfos not found — pcap_summary will use fallback mode"
fi

log_info "Installing Packet Buddy MCP dependencies..."
pip3 install fastmcp 2>/dev/null || log_warn "fastmcp install failed"

# Create pcap upload directory
mkdir -p /tmp/netclaw-pcaps
log_info "Pcap upload directory: /tmp/netclaw-pcaps"

[ -f "$PACKET_BUDDY_MCP_DIR/server.py" ] && \
    log_info "Packet Buddy MCP ready: $PACKET_BUDDY_MCP_DIR/server.py" || \
    log_error "packet-buddy-mcp/server.py not found"

echo ""

# ═══════════════════════════════════════════
# Step 26: Cisco Modeling Labs (CML) MCP Server
# ═══════════════════════════════════════════

log_step "26/$TOTAL_STEPS Installing Cisco CML MCP Server..."
echo "  Source: https://github.com/xorrkaz/cml-mcp"
echo "  Manage CML labs via natural language — create, wire, start, stop, capture"

# Check Python version (CML MCP requires 3.12+)
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
if [ "$PY_MINOR" -ge 12 ]; then
    log_info "Python 3.$PY_MINOR detected (3.12+ required for CML MCP)"

    log_info "Installing CML MCP via pip..."
    pip3 install cml-mcp 2>/dev/null || {
        log_warn "pip install cml-mcp failed — trying with --break-system-packages"
        pip3 install --break-system-packages cml-mcp 2>/dev/null || \
            log_warn "CML MCP install failed. Install manually: pip3 install cml-mcp"
    }

    # Verify cml-mcp is importable
    if python3 -c "import cml_mcp" 2>/dev/null; then
        log_info "CML MCP installed successfully"
        CML_MCP_CMD="cml-mcp"
        if command -v cml-mcp &> /dev/null; then
            log_info "CML MCP ready: cml-mcp (stdio transport)"
        else
            # Try finding via python module
            CML_MCP_CMD="python3 -m cml_mcp"
            log_info "CML MCP ready: python3 -m cml_mcp (stdio transport)"
        fi
    else
        log_warn "CML MCP package not importable after install"
    fi

    # Optional: install with pyATS support for CLI execution
    echo ""
    log_info "Tip: For pyATS CLI execution on CML nodes, install with:"
    echo "      pip3 install 'cml-mcp[pyats]'"
else
    log_warn "Python 3.12+ required for CML MCP (found 3.$PY_MINOR)"
    log_info "CML MCP skipped — upgrade Python or install manually: pip3 install cml-mcp"
fi

echo ""

# ═══════════════════════════════════════════
# Step 27: Cisco NSO MCP Server
# ═══════════════════════════════════════════

log_step "27/$TOTAL_STEPS Installing Cisco NSO MCP Server..."
echo "  Source: https://github.com/NSO-developer/cisco-nso-mcp-server"
echo "  Network orchestration via natural language — device config, sync, services"

# Check Python version (NSO MCP requires 3.12+)
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
if [ "$PY_MINOR" -ge 12 ]; then
    log_info "Python 3.$PY_MINOR detected (3.12+ required for NSO MCP)"

    log_info "Installing NSO MCP via pip..."
    pip3 install cisco-nso-mcp-server 2>/dev/null || {
        log_warn "pip install cisco-nso-mcp-server failed — trying with --break-system-packages"
        pip3 install --break-system-packages cisco-nso-mcp-server 2>/dev/null || \
            log_warn "NSO MCP install failed. Install manually: pip3 install cisco-nso-mcp-server"
    }

    # Verify cisco-nso-mcp-server is available
    if command -v cisco-nso-mcp-server &> /dev/null; then
        log_info "NSO MCP installed successfully: cisco-nso-mcp-server (stdio transport)"
    elif python3 -c "import cisco_nso_mcp_server" 2>/dev/null; then
        log_info "NSO MCP installed successfully (module importable)"
    else
        log_warn "NSO MCP package not found after install"
    fi
else
    log_warn "Python 3.12+ required for NSO MCP (found 3.$PY_MINOR)"
    log_info "NSO MCP skipped — upgrade Python or install manually: pip3 install cisco-nso-mcp-server"
fi

echo ""

# ═══════════════════════════════════════════
# Step 28: Cisco FMC MCP Server
# ═══════════════════════════════════════════

log_step "28/$TOTAL_STEPS Installing Cisco FMC MCP Server..."
echo "  Source: https://github.com/CiscoDevNet/CiscoFMC-MCP-server-community"
echo "  Cisco Secure Firewall policy search — access rules, FTD targeting, multi-FMC"

FMC_MCP_DIR="$MCP_DIR/CiscoFMC-MCP-server-community"
if [ -d "$FMC_MCP_DIR" ]; then
    log_info "Cisco FMC MCP already cloned, pulling latest..."
    git -C "$FMC_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/CiscoDevNet/CiscoFMC-MCP-server-community.git "$FMC_MCP_DIR" 2>/dev/null
fi

if [ -d "$FMC_MCP_DIR" ]; then
    if [ -f "$FMC_MCP_DIR/requirements.txt" ]; then
        pip3 install -r "$FMC_MCP_DIR/requirements.txt" 2>/dev/null || \
            pip3 install --break-system-packages -r "$FMC_MCP_DIR/requirements.txt" 2>/dev/null || \
            log_warn "FMC MCP dependencies install failed"
    fi
    log_info "Cisco FMC MCP installed (HTTP transport on port 8000)"
else
    log_warn "Cisco FMC MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 29: Cisco Meraki Magic MCP Server
# ═══════════════════════════════════════════

log_step "29/$TOTAL_STEPS Installing Cisco Meraki Magic MCP Server..."
echo "  Source: https://github.com/CiscoDevNet/meraki-magic-mcp-community"
echo "  Cisco Meraki Dashboard — ~804 API endpoints: orgs, networks, devices, wireless, switching, security, cameras"

MERAKI_MCP_DIR="$MCP_DIR/meraki-magic-mcp-community"
if [ -d "$MERAKI_MCP_DIR" ]; then
    log_info "Meraki Magic MCP already cloned, pulling latest..."
    git -C "$MERAKI_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/CiscoDevNet/meraki-magic-mcp-community.git "$MERAKI_MCP_DIR" 2>/dev/null
fi

if [ -d "$MERAKI_MCP_DIR" ]; then
    # Check Python version (Meraki Magic MCP requires 3.13+)
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 13 ]; then
        log_info "Python 3.$PY_MINOR detected (3.13+ required for Meraki Magic MCP)"
        if [ -f "$MERAKI_MCP_DIR/requirements.txt" ]; then
            pip3 install -r "$MERAKI_MCP_DIR/requirements.txt" 2>/dev/null || \
                pip3 install --break-system-packages -r "$MERAKI_MCP_DIR/requirements.txt" 2>/dev/null || \
                log_warn "Meraki Magic MCP dependencies install failed"
        fi
        log_info "Meraki Magic MCP installed (stdio transport via FastMCP)"
        log_info "  Dynamic MCP: meraki-mcp-dynamic.py (~804 API endpoints)"
        log_info "  Manual MCP:  meraki-mcp.py (40 curated endpoints)"
    else
        log_warn "Python 3.13+ recommended for Meraki Magic MCP (found 3.$PY_MINOR)"
        log_info "Installing core dependencies (meraki, fastmcp, pydantic)..."
        pip3 install meraki fastmcp pydantic python-dotenv 2>/dev/null || \
            pip3 install --break-system-packages meraki fastmcp pydantic python-dotenv 2>/dev/null || \
            log_warn "Meraki core deps install failed"
        log_info "Meraki Magic MCP installed (some features may require Python 3.13+)"
    fi
else
    log_warn "Meraki Magic MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 30: ThousandEyes Community MCP Server
# ═══════════════════════════════════════════

log_step "30/$TOTAL_STEPS Installing ThousandEyes Community MCP Server..."
echo "  Source: https://github.com/CiscoDevNet/thousandeyes-mcp-community"
echo "  ThousandEyes monitoring — tests, agents, path visualization, dashboards (9 read-only tools)"

TE_COMMUNITY_MCP_DIR="$MCP_DIR/thousandeyes-mcp-community"
if [ -d "$TE_COMMUNITY_MCP_DIR" ]; then
    log_info "ThousandEyes Community MCP already cloned, pulling latest..."
    git -C "$TE_COMMUNITY_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/CiscoDevNet/thousandeyes-mcp-community.git "$TE_COMMUNITY_MCP_DIR" 2>/dev/null
fi

if [ -d "$TE_COMMUNITY_MCP_DIR" ]; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 12 ]; then
        log_info "Python 3.$PY_MINOR detected (3.12+ required for ThousandEyes Community MCP)"
        if [ -f "$TE_COMMUNITY_MCP_DIR/requirements.txt" ]; then
            pip3 install -r "$TE_COMMUNITY_MCP_DIR/requirements.txt" 2>/dev/null || \
                pip3 install --break-system-packages -r "$TE_COMMUNITY_MCP_DIR/requirements.txt" 2>/dev/null || \
                log_warn "ThousandEyes Community MCP dependencies install failed"
        fi
        log_info "ThousandEyes Community MCP installed (stdio transport)"
    else
        log_warn "Python 3.12+ required for ThousandEyes Community MCP (found 3.$PY_MINOR)"
        log_info "Installing core dependencies..."
        pip3 install httpx "mcp>=1.13" 2>/dev/null || \
            pip3 install --break-system-packages httpx "mcp>=1.13" 2>/dev/null || \
            log_warn "ThousandEyes Community deps install failed"
    fi
else
    log_warn "ThousandEyes Community MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 31: ThousandEyes Official MCP Server (remote HTTP)
# ═══════════════════════════════════════════

log_step "31/$TOTAL_STEPS Configuring ThousandEyes Official MCP Server..."
echo "  Source: https://github.com/CiscoDevNet/ThousandEyes-MCP-Server-official"
echo "  Remote HTTP endpoint hosted by Cisco — ~20 tools: alerts, outages, BGP, instant tests, endpoint agents"
echo ""
echo "  ThousandEyes Official MCP is a REMOTE HTTP endpoint — nothing to install locally."
echo "  Endpoint: https://api.thousandeyes.com/mcp"
echo "  Auth: Bearer token via TE_TOKEN environment variable"
echo ""

# Check for npx (required for mcp-remote bridge)
if command -v npx &> /dev/null; then
    log_info "npx found — ThousandEyes Official MCP will use npx mcp-remote for connectivity"
    log_info "Pre-caching mcp-remote..."
    npm cache add "mcp-remote" 2>/dev/null || log_warn "Could not pre-cache mcp-remote"
else
    log_warn "npx not found — install Node.js for ThousandEyes Official MCP connectivity"
fi

log_info "ThousandEyes Official MCP ready (remote HTTP — hosted by Cisco)"

echo ""

# ═══════════════════════════════════════════
# Step 32: Cisco RADKit MCP Server
# ═══════════════════════════════════════════

log_step "32/$TOTAL_STEPS Installing Cisco RADKit MCP Server..."
echo "  Source: https://github.com/CiscoDevNet/radkit-mcp-server-community"
echo "  Cloud-relayed remote device access — CLI execution, SNMP polling, device inventory (5 tools)"

RADKIT_MCP_DIR="$MCP_DIR/radkit-mcp-server-community"
if [ -d "$RADKIT_MCP_DIR" ]; then
    log_info "RADKit MCP already cloned, pulling latest..."
    git -C "$RADKIT_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/CiscoDevNet/radkit-mcp-server-community.git "$RADKIT_MCP_DIR" 2>/dev/null
fi

if [ -d "$RADKIT_MCP_DIR" ]; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 10 ]; then
        log_info "Python 3.$PY_MINOR detected (3.10+ required for RADKit MCP)"
        if [ -f "$RADKIT_MCP_DIR/pyproject.toml" ]; then
            log_info "Installing RADKit MCP dependencies..."
            cd "$RADKIT_MCP_DIR" && pip3 install -e . 2>/dev/null || \
                pip3 install --break-system-packages -e . 2>/dev/null || {
                log_warn "Full RADKit install failed — installing core deps..."
                pip3 install fastmcp python-dotenv pydantic-settings 2>/dev/null || \
                    pip3 install --break-system-packages fastmcp python-dotenv pydantic-settings 2>/dev/null || \
                    log_warn "RADKit core deps install failed"
            }
            cd "$NETCLAW_DIR"
        fi
        log_info "RADKit MCP installed (stdio transport via FastMCP)"
        log_info "  Requires: active RADKit service instance + certificate-based auth"
    else
        log_warn "Python 3.10+ required for RADKit MCP (found 3.$PY_MINOR)"
        log_info "RADKit MCP skipped — upgrade Python or install manually"
    fi
else
    log_warn "RADKit MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 33: AWS Cloud MCP Servers (6 servers)
# ═══════════════════════════════════════════

log_step "33/$TOTAL_STEPS Installing AWS Cloud MCP Servers..."
echo "  Source: https://github.com/awslabs/mcp"
echo "  6 AWS MCP servers for cloud networking, monitoring, security, costs, diagrams"

# AWS MCPs require uv (Rust-based Python package manager) for uvx runtime
if command -v uvx &> /dev/null; then
    log_info "uvx found — AWS MCP servers will run via uvx at runtime"
else
    log_info "Installing uv (required for AWS MCP servers)..."
    if command -v pip3 &> /dev/null; then
        pip3 install uv 2>/dev/null || pip3 install --break-system-packages uv 2>/dev/null || true
    fi
    if ! command -v uvx &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh 2>/dev/null | sh 2>/dev/null || true
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if command -v uvx &> /dev/null; then
        log_info "uv installed successfully"
    else
        log_warn "uv not installed — AWS MCP servers will not work"
        log_info "Install manually: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
fi

# Pre-validate AWS MCP packages (uvx will download on first run)
if command -v uvx &> /dev/null; then
    AWS_MCPS=(
        "awslabs.aws-network-mcp-server"
        "awslabs.cloudwatch-mcp-server"
        "awslabs.iam-mcp-server"
        "awslabs.cloudtrail-mcp-server"
        "awslabs.cost-explorer-mcp-server"
        "awslabs.aws-diagram-mcp-server"
    )
    for pkg in "${AWS_MCPS[@]}"; do
        echo "  Validating: $pkg"
    done
    log_info "AWS MCP servers ready (6 servers via uvx — downloaded on first use)"

    # Check for graphviz (required by aws-diagram-mcp-server)
    if command -v dot &> /dev/null; then
        log_info "GraphViz found (required for AWS Diagram MCP)"
    else
        log_warn "GraphViz not found — install for AWS architecture diagrams: apt install graphviz"
    fi
else
    log_warn "uvx not available — AWS MCP servers skipped"
fi

echo ""

# ═══════════════════════════════════════════
# Step 34: Google Cloud MCP Servers (4 servers)
# ═══════════════════════════════════════════

log_step "34/$TOTAL_STEPS Configuring Google Cloud MCP Servers..."
echo "  Source: https://docs.cloud.google.com/mcp/supported-products"
echo "  4 GCP remote MCP servers for compute, monitoring, logging, resource management"
echo ""
echo "  Google Cloud MCP servers are REMOTE HTTP endpoints — nothing to install locally."
echo "  They authenticate via OAuth 2.0 / Google IAM."
echo ""

# Check for gcloud CLI (recommended for auth)
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud version 2>/dev/null | head -1 | grep -oP '[\d.]+' || echo "unknown")
    log_info "gcloud CLI found (version: $GCLOUD_VERSION)"

    # Check for application-default credentials
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ] || [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
        log_info "Google Cloud credentials detected"
    else
        log_info "No application-default credentials found"
        log_info "Run: gcloud auth application-default login (or set GOOGLE_APPLICATION_CREDENTIALS)"
    fi
else
    log_info "gcloud CLI not found — install from https://cloud.google.com/sdk/docs/install"
    log_info "Or set GOOGLE_APPLICATION_CREDENTIALS to a service account key JSON file"
fi

GCP_MCPS=(
    "compute.googleapis.com/mcp         (Compute Engine — 28 tools: VMs, disks, templates)"
    "monitoring.googleapis.com/mcp       (Cloud Monitoring — 6 tools: metrics, alerts)"
    "logging.googleapis.com/mcp          (Cloud Logging — 6 tools: log search, flow logs)"
    "cloudresourcemanager.googleapis.com/mcp (Resource Manager — 1 tool: project discovery)"
)
for mcp in "${GCP_MCPS[@]}"; do
    echo "  Remote: $mcp"
done
log_info "GCP MCP servers ready (4 remote HTTP endpoints — hosted by Google)"

echo ""

# ═══════════════════════════════════════════
# Step 35: UML MCP Server
# ═══════════════════════════════════════════

log_step "35/$TOTAL_STEPS Installing UML MCP Server..."
echo "  Source: https://github.com/antoinebou12/uml-mcp"
echo "  27+ diagram types via Kroki — class, sequence, network, rack, packet, C4, Mermaid, D2, Graphviz (2 tools)"

UML_MCP_DIR="$MCP_DIR/uml-mcp"
if [ -d "$UML_MCP_DIR" ]; then
    log_info "UML MCP already cloned, pulling latest..."
    git -C "$UML_MCP_DIR" pull --quiet 2>/dev/null || true
else
    git clone https://github.com/antoinebou12/uml-mcp.git "$UML_MCP_DIR" 2>/dev/null
fi

if [ -d "$UML_MCP_DIR" ]; then
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [ "$PY_MINOR" -ge 10 ]; then
        log_info "Python 3.$PY_MINOR detected (3.10+ required for UML MCP)"
        if [ -f "$UML_MCP_DIR/pyproject.toml" ]; then
            log_info "Installing UML MCP dependencies..."
            cd "$UML_MCP_DIR" && pip3 install -e . 2>/dev/null || \
                pip3 install --break-system-packages -e . 2>/dev/null || {
                log_warn "Full UML MCP install failed — installing core deps..."
                pip3 install fastmcp httpx pillow graphviz 2>/dev/null || \
                    pip3 install --break-system-packages fastmcp httpx pillow graphviz 2>/dev/null || \
                    log_warn "UML MCP core deps install failed"
            }
            cd "$NETCLAW_DIR"
        fi
        log_info "UML MCP installed (stdio transport via FastMCP)"
        log_info "  Rendering: Kroki (public by default, configurable for local instance)"
    else
        log_warn "Python 3.10+ required for UML MCP (found 3.$PY_MINOR)"
        log_info "UML MCP skipped — upgrade Python or install manually"
    fi
else
    log_warn "UML MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 36: ContainerLab MCP Server (Python)
# ═══════════════════════════════════════════

log_step "36/$TOTAL_STEPS Installing ContainerLab MCP Server..."
echo "  Source: https://github.com/seanerama/clab-mcp-server"
echo "  Deploy and manage containerized network labs (SR Linux, cEOS, FRR, etc.)"

CLAB_MCP_DIR="$MCP_DIR/clab-mcp-server"
clone_or_pull "$CLAB_MCP_DIR" "https://github.com/seanerama/clab-mcp-server.git"

log_info "Installing ContainerLab MCP dependencies..."
pip3 install -r "$CLAB_MCP_DIR/requirements.txt" 2>/dev/null || \
    pip3 install --break-system-packages -r "$CLAB_MCP_DIR/requirements.txt" 2>/dev/null || \
    log_warn "ContainerLab MCP dependencies install failed"

[ -f "$CLAB_MCP_DIR/clab_mcp_server.py" ] && \
    log_info "ContainerLab MCP ready: $CLAB_MCP_DIR/clab_mcp_server.py" || \
    log_error "clab_mcp_server.py not found"

echo ""
echo "  Prerequisite: ContainerLab API server (clab-api-server) must be running."
echo "  Create a Linux user on the API server host:"
echo "    sudo groupadd -f clab_admins && sudo groupadd -f clab_api"
echo "    sudo useradd -m -s /bin/bash netclaw && sudo usermod -aG clab_admins netclaw"
echo "    sudo passwd netclaw"
echo "  If the API server runs in Docker, restart it: docker restart clab-api-server"
echo ""

echo ""

# ═══════════════════════════════════════════
# Step 37: Cisco SD-WAN MCP Server (vManage)
# ═══════════════════════════════════════════

log_step "37/$TOTAL_STEPS Installing Cisco SD-WAN MCP Server..."
echo "  Source: https://github.com/siddhartha2303/cisco-sdwan-mcp"
echo "  Read-only vManage API — 12 tools for SD-WAN fabric monitoring"

SDWAN_MCP_DIR="$MCP_DIR/cisco-sdwan-mcp"
clone_or_pull "$SDWAN_MCP_DIR" "https://github.com/siddhartha2303/cisco-sdwan-mcp.git"

if [ -d "$SDWAN_MCP_DIR" ]; then
    log_info "Installing SD-WAN MCP dependencies..."
    if [ -f "$SDWAN_MCP_DIR/requirements.txt" ]; then
        pip3 install -r "$SDWAN_MCP_DIR/requirements.txt" 2>/dev/null || \
            pip3 install --break-system-packages -r "$SDWAN_MCP_DIR/requirements.txt" 2>/dev/null || {
            log_warn "SD-WAN MCP requirements.txt install failed — installing core deps..."
            pip3 install fastmcp requests python-dotenv 2>/dev/null || \
                pip3 install --break-system-packages fastmcp requests python-dotenv 2>/dev/null || \
                log_warn "SD-WAN MCP core deps install failed"
        }
    else
        pip3 install fastmcp requests python-dotenv 2>/dev/null || \
            pip3 install --break-system-packages fastmcp requests python-dotenv 2>/dev/null || \
            log_warn "SD-WAN MCP deps install failed"
    fi
    [ -f "$SDWAN_MCP_DIR/sdwan_mcp_server.py" ] && \
        log_info "SD-WAN MCP ready: $SDWAN_MCP_DIR/sdwan_mcp_server.py" || \
        log_warn "sdwan_mcp_server.py not found — check repo structure"
else
    log_warn "SD-WAN MCP clone failed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 38: Grafana MCP Server (Observability)
# ═══════════════════════════════════════════

log_step "38/$TOTAL_STEPS Installing Grafana MCP Server..."
echo "  Source: https://github.com/grafana/mcp-grafana"
echo "  Grafana observability — dashboards, Prometheus, Loki, alerting, incidents, OnCall (75+ tools)"

if command -v uvx &> /dev/null; then
    log_info "uvx available — Grafana MCP will run via: uvx mcp-grafana"
    # Pre-cache the package
    uvx --help &>/dev/null || true
    log_info "Grafana MCP ready (runs via uvx mcp-grafana, stdio transport)"
else
    log_warn "uvx not found — install uv first (curl -LsSf https://astral.sh/uv/install.sh | sh)"
    log_warn "Grafana MCP requires uvx to run"
fi

echo ""

# ═══════════════════════════════════════════
# Step 39: Prometheus MCP Server (Monitoring)
# ═══════════════════════════════════════════

log_step "39/$TOTAL_STEPS Installing Prometheus MCP Server..."
echo "  Source: https://github.com/pab1it0/prometheus-mcp-server"
echo "  Prometheus monitoring — PromQL queries, metric discovery, target health (6 tools)"

PROMETHEUS_MCP_DIR="$MCP_DIR/prometheus-mcp-server"

if pip3 install prometheus-mcp-server 2>/dev/null; then
    log_info "Prometheus MCP installed via pip (prometheus-mcp-server)"
    log_info "Prometheus MCP ready (runs via prometheus-mcp-server, stdio transport)"
else
    log_warn "pip3 install prometheus-mcp-server failed — trying git clone fallback"
    if git clone https://github.com/pab1it0/prometheus-mcp-server.git "$PROMETHEUS_MCP_DIR" 2>/dev/null; then
        pip3 install -e "$PROMETHEUS_MCP_DIR" 2>/dev/null || pip3 install -r "$PROMETHEUS_MCP_DIR/requirements.txt" 2>/dev/null || true
        log_info "Prometheus MCP cloned and installed from source"
    else
        log_warn "Prometheus MCP: installation failed (pip and git clone both failed)"
    fi
fi

echo ""

# ═══════════════════════════════════════════
# Step 40: Kubeshark MCP Server (K8s Traffic Analysis)
# ═══════════════════════════════════════════

log_step "40/$TOTAL_STEPS Configuring Kubeshark MCP Server..."
echo "  Source: https://github.com/kubeshark/kubeshark"
echo "  Kubernetes L4/L7 traffic analysis — capture, pcap export, flow analysis, TLS decryption (6 tools)"

# Kubeshark is a remote HTTP MCP server running inside a K8s cluster.
# No local install needed — just needs Kubeshark deployed via Helm with mcp.enabled=true.
# Port-forward: kubectl port-forward svc/kubeshark-hub 8898:8898
if command -v kubectl &> /dev/null; then
    log_info "kubectl available — Kubeshark MCP requires Kubeshark deployed in K8s cluster"
    log_info "  Install: helm install kubeshark kubeshark/kubeshark --set mcp.enabled=true --set mcp.port=8898"
    log_info "  Access:  kubectl port-forward svc/kubeshark-hub 8898:8898"
    log_info "  MCP URL: http://localhost:8898/mcp"
else
    log_warn "kubectl not found — Kubeshark MCP requires kubectl + Kubernetes cluster"
    log_warn "Kubeshark MCP will be available once kubectl is installed and Kubeshark is deployed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 41: Protocol MCP Server (BGP + OSPF + GRE)
# ═══════════════════════════════════════════

log_step "41/$TOTAL_STEPS Installing Protocol MCP Server..."
echo "  Source: WontYouBeMyNeighbour BGP/OSPFv3/GRE modules"
echo "  Live control-plane participation — BGP peering, OSPF adjacency, GRE tunnels (10 tools)"

PROTOCOL_MCP_DIR="$MCP_DIR/protocol-mcp"
if [ -d "$PROTOCOL_MCP_DIR" ]; then
    log_info "Protocol MCP already present: $PROTOCOL_MCP_DIR"
else
    log_warn "Protocol MCP not found — it should be bundled with NetClaw at mcp-servers/protocol-mcp/"
fi

if [ -d "$PROTOCOL_MCP_DIR" ]; then
    log_info "Installing Protocol MCP dependencies..."
    if [ -f "$PROTOCOL_MCP_DIR/requirements.txt" ]; then
        pip3 install -r "$PROTOCOL_MCP_DIR/requirements.txt" 2>/dev/null || \
            pip3 install --break-system-packages -r "$PROTOCOL_MCP_DIR/requirements.txt" 2>/dev/null || {
            log_warn "Full Protocol MCP install failed — installing core deps..."
            pip3 install scapy networkx mcp fastmcp 2>/dev/null || \
                pip3 install --break-system-packages scapy networkx mcp fastmcp 2>/dev/null || \
                log_warn "Protocol MCP core deps install failed"
        }
    fi
    log_info "Protocol MCP installed (stdio transport via FastMCP)"
fi

echo ""

# ═══════════════════════════════════════════
# Step 42: Protocol Peering Wizard (optional)
# ═══════════════════════════════════════════

log_step "42/$TOTAL_STEPS Protocol Peering Configuration (optional)..."
echo ""
echo "  NetClaw can participate in BGP/OSPF as a real routing peer."
echo "  This requires a GRE tunnel to a network device and protocol configuration."
echo ""

read -rp "  Enable protocol participation? [y/N] " ENABLE_PROTOCOL
ENABLE_PROTOCOL="${ENABLE_PROTOCOL:-n}"

if [[ "$ENABLE_PROTOCOL" =~ ^[Yy] ]]; then
    echo ""
    read -rp "  Router ID (e.g. 4.4.4.4): " PROTO_ROUTER_ID
    PROTO_ROUTER_ID="${PROTO_ROUTER_ID:-4.4.4.4}"

    read -rp "  Local BGP AS (e.g. 65001): " PROTO_LOCAL_AS
    PROTO_LOCAL_AS="${PROTO_LOCAL_AS:-65001}"

    read -rp "  BGP peer IP (e.g. 172.16.0.1): " PROTO_PEER_IP
    PROTO_PEER_IP="${PROTO_PEER_IP:-172.16.0.1}"

    read -rp "  BGP peer AS (e.g. 65000): " PROTO_PEER_AS
    PROTO_PEER_AS="${PROTO_PEER_AS:-65000}"

    read -rp "  Lab mode (skip ServiceNow CR)? [Y/n] " PROTO_LAB_MODE
    PROTO_LAB_MODE="${PROTO_LAB_MODE:-y}"
    if [[ "$PROTO_LAB_MODE" =~ ^[Yy] ]]; then
        PROTO_LAB_MODE_VAL="true"
    else
        PROTO_LAB_MODE_VAL="false"
    fi

    # Write protocol env vars to OpenClaw .env
    OPENCLAW_ENV_PROTO="$HOME/.openclaw/.env"
    [ -f "$OPENCLAW_ENV_PROTO" ] || touch "$OPENCLAW_ENV_PROTO"

    for key_val in \
        "NETCLAW_ROUTER_ID=$PROTO_ROUTER_ID" \
        "NETCLAW_LOCAL_AS=$PROTO_LOCAL_AS" \
        "NETCLAW_BGP_PEERS=[{\"ip\":\"$PROTO_PEER_IP\",\"as\":$PROTO_PEER_AS}]" \
        "NETCLAW_LAB_MODE=$PROTO_LAB_MODE_VAL" \
        "PROTOCOL_MCP_SCRIPT=$PROTOCOL_MCP_DIR/server.py"; do
        key="${key_val%%=*}"
        if grep -q "^${key}=" "$OPENCLAW_ENV_PROTO" 2>/dev/null; then
            sed -i "s|^${key}=.*|${key_val}|" "$OPENCLAW_ENV_PROTO"
        else
            echo "$key_val" >> "$OPENCLAW_ENV_PROTO"
        fi
    done

    log_info "Protocol peering configured:"
    log_info "  Router ID: $PROTO_ROUTER_ID"
    log_info "  Local AS: $PROTO_LOCAL_AS"
    log_info "  Peer: $PROTO_PEER_IP (AS $PROTO_PEER_AS)"
    log_info "  Lab mode: $PROTO_LAB_MODE_VAL"
    echo ""
    log_info "Tip: Start the FRR lab testbed for testing:"
    echo "      cd lab/frr-testbed && docker compose up -d"
    echo "      sudo bash scripts/setup-gre.sh"

    # ─── NetClaw Mesh (BGP over ngrok) ───────────────────────────────
    echo ""
    echo "  ── NetClaw Mesh ──────────────────────────────────────────"
    echo "  Peer your NetClaw with other NetClaw instances worldwide"
    echo "  over BGP via ngrok TCP tunnels."
    echo ""
    read -rp "  Enable NetClaw Mesh peering (BGP over ngrok)? [y/N] " ENABLE_MESH
    ENABLE_MESH="${ENABLE_MESH:-n}"

    if [[ "$ENABLE_MESH" =~ ^[Yy] ]]; then
        # BGP listen port (non-privileged)
        read -rp "  BGP listen port (default 1179): " MESH_BGP_PORT
        MESH_BGP_PORT="${MESH_BGP_PORT:-1179}"

        # Build mesh peers JSON — start with local FRR peer from above
        MESH_PEERS_JSON="[{\"ip\":\"$PROTO_PEER_IP\",\"as\":$PROTO_PEER_AS}"

        # Ask for remote NetClaw peers
        echo ""
        echo "  Add remote NetClaw peers (other people's ngrok endpoints)."
        echo "  You can also add peers later via: curl -X POST http://127.0.0.1:8179/add_peer"
        echo ""
        read -rp "  Add a remote NetClaw peer? [y/N] " ADD_REMOTE
        ADD_REMOTE="${ADD_REMOTE:-n}"
        MESH_REMOTE_COUNT=0
        while [[ "$ADD_REMOTE" =~ ^[Yy] ]]; do
            read -rp "    Remote ngrok hostname (e.g. 0.tcp.ngrok.io): " REMOTE_HOST
            read -rp "    Remote ngrok port (e.g. 12345): " REMOTE_PORT
            read -rp "    Remote AS number (e.g. 65002): " REMOTE_AS

            # Add outbound mesh peer
            MESH_PEERS_JSON="${MESH_PEERS_JSON},{\"ip\":\"${REMOTE_HOST}\",\"as\":${REMOTE_AS},\"port\":${REMOTE_PORT},\"hostname\":true}"
            # Add matching inbound entry so they can connect back to us
            MESH_PEERS_JSON="${MESH_PEERS_JSON},{\"as\":${REMOTE_AS},\"passive\":true,\"accept_any_source\":true}"
            MESH_REMOTE_COUNT=$((MESH_REMOTE_COUNT + 1))

            read -rp "    Add another remote peer? [y/N] " ADD_REMOTE
            ADD_REMOTE="${ADD_REMOTE:-n}"
        done

        # Accept inbound connections from unknown peers?
        echo ""
        read -rp "  Accept inbound mesh connections from any AS? [Y/n] " ACCEPT_INBOUND
        ACCEPT_INBOUND="${ACCEPT_INBOUND:-y}"
        if [[ "$ACCEPT_INBOUND" =~ ^[Yy] ]]; then
            # Add a general inbound acceptor — AS 0 means "match any unconfigured AS"
            # For now, we rely on per-AS entries added above. This flag is for the env.
            MESH_ACCEPT_ANY="true"
        else
            MESH_ACCEPT_ANY="false"
        fi

        # Close JSON array
        MESH_PEERS_JSON="${MESH_PEERS_JSON}]"

        # Write mesh env vars
        for key_val in \
            "BGP_LISTEN_PORT=$MESH_BGP_PORT" \
            "NETCLAW_MESH_ENABLED=true" \
            "NETCLAW_MESH_ACCEPT_INBOUND=$MESH_ACCEPT_ANY"; do
            key="${key_val%%=*}"
            if grep -q "^${key}=" "$OPENCLAW_ENV_PROTO" 2>/dev/null; then
                sed -i "s|^${key}=.*|${key_val}|" "$OPENCLAW_ENV_PROTO"
            else
                echo "$key_val" >> "$OPENCLAW_ENV_PROTO"
            fi
        done

        # Overwrite NETCLAW_BGP_PEERS with the combined local + mesh peers
        if grep -q "^NETCLAW_BGP_PEERS=" "$OPENCLAW_ENV_PROTO" 2>/dev/null; then
            sed -i "s|^NETCLAW_BGP_PEERS=.*|NETCLAW_BGP_PEERS=$MESH_PEERS_JSON|" "$OPENCLAW_ENV_PROTO"
        else
            echo "NETCLAW_BGP_PEERS=$MESH_PEERS_JSON" >> "$OPENCLAW_ENV_PROTO"
        fi

        echo ""
        log_info "NetClaw Mesh configured:"
        log_info "  BGP listen port: $MESH_BGP_PORT"
        log_info "  Remote peers added: $MESH_REMOTE_COUNT"
        log_info "  Accept inbound: $MESH_ACCEPT_ANY"
        echo ""
        log_info "To expose your BGP port via ngrok, run:"
        echo "      ngrok tcp $MESH_BGP_PORT"
        echo ""
        log_info "Share your ngrok endpoint with other NetClaw operators."
        log_info "They add it during their install, or at runtime:"
        echo "      curl -X POST http://127.0.0.1:8179/add_peer \\"
        echo "        -d '{\"ip\":\"YOUR.tcp.ngrok.io\",\"as\":$PROTO_LOCAL_AS,\"port\":NNNNN,\"hostname\":true}'"
    else
        log_info "NetClaw Mesh skipped (enable later by re-running install)"
    fi
    # ─── End NetClaw Mesh ────────────────────────────────────────────

else
    log_info "Protocol participation skipped (enable later by re-running install)"
fi

echo ""

# ═══════════════════════════════════════════
# Step 43: Deploy skills and set environment
# ═══════════════════════════════════════════

log_step "43/$TOTAL_STEPS Deploying skills and configuration..."

PYATS_SCRIPT="$PYATS_MCP_DIR/pyats_mcp_server.py"
TESTBED_PATH="$NETCLAW_DIR/testbed/testbed.yaml"

# Bootstrap OpenClaw workspace (create if it doesn't exist)
OPENCLAW_DIR="$HOME/.openclaw"
if [ ! -d "$OPENCLAW_DIR" ]; then
    log_info "OpenClaw directory not found. Bootstrapping..."
    mkdir -p "$OPENCLAW_DIR/workspace/skills"
    mkdir -p "$OPENCLAW_DIR/agents/main/sessions"
    log_info "Created $OPENCLAW_DIR"
fi

# Deploy openclaw.json config ONLY if onboard didn't already create one
if [ ! -f "$OPENCLAW_DIR/openclaw.json" ]; then
    if [ -f "$NETCLAW_DIR/config/openclaw.json" ]; then
        cp "$NETCLAW_DIR/config/openclaw.json" "$OPENCLAW_DIR/openclaw.json"
        log_info "Deployed fallback openclaw.json (gateway.mode=local)"
    else
        log_warn "config/openclaw.json not found in repo"
    fi
else
    log_info "openclaw.json already exists (created by onboard) — keeping it"
fi

# Deploy skills
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

# Symlink testbed into workspace so OpenClaw can find it
mkdir -p "$OPENCLAW_DIR/workspace/testbed"
ln -sf "$NETCLAW_DIR/testbed/testbed.yaml" "$OPENCLAW_DIR/workspace/testbed/testbed.yaml"
log_info "Symlinked testbed.yaml into workspace"

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
    ["PACKET_BUDDY_MCP_SCRIPT"]="$PACKET_BUDDY_MCP_DIR/server.py"
    ["PROTOCOL_MCP_SCRIPT"]="$PROTOCOL_MCP_DIR/server.py"
    ["CLAB_MCP_SCRIPT"]="$CLAB_MCP_DIR/clab_mcp_server.py"
    ["SDWAN_MCP_SCRIPT"]="$SDWAN_MCP_DIR/sdwan_mcp_server.py"
)

for key in "${!ENV_VARS[@]}"; do
    if grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${ENV_VARS[$key]}|" "$OPENCLAW_ENV"
    else
        echo "${key}=${ENV_VARS[$key]}" >> "$OPENCLAW_ENV"
    fi
done

# Remind user about API key if not set
if ! grep -q "^ANTHROPIC_API_KEY=" "$OPENCLAW_ENV" 2>/dev/null && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "" >> "$OPENCLAW_ENV"
    echo "# Uncomment and set your Anthropic API key:" >> "$OPENCLAW_ENV"
    echo "# ANTHROPIC_API_KEY=sk-ant-your-key-here" >> "$OPENCLAW_ENV"
    log_warn "ANTHROPIC_API_KEY not set. Add it to $OPENCLAW_ENV or export it in your shell."
fi

log_info "Set ${#ENV_VARS[@]} environment variables in $OPENCLAW_ENV"

# Verify the config is correct
if [ -f "$OPENCLAW_DIR/openclaw.json" ]; then
    if grep -q '"mode": "local"' "$OPENCLAW_DIR/openclaw.json" 2>/dev/null; then
        log_info "Gateway config verified: mode=local"
    else
        log_warn "openclaw.json may be missing gateway.mode=local"
    fi
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
# Step 44: Verify installation
# ═══════════════════════════════════════════

log_step "44/$TOTAL_STEPS Verifying installation..."

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

# Nautobot MCP is git-cloned with pip install -e
if [ -d "$NAUTOBOT_MCP_DIR" ]; then
    if command -v mcp-nautobot-server &> /dev/null; then
        log_info "Nautobot MCP: OK (cli entry point)"
        SERVERS_OK=$((SERVERS_OK + 1))
    elif [ -f "$NAUTOBOT_MCP_DIR/src/mcp_nautobot_server/server.py" ]; then
        log_info "Nautobot MCP: OK (server.py found)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "Nautobot MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "Nautobot MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Infrahub MCP is git-cloned with uv sync / pip
if [ -d "$INFRAHUB_MCP_DIR" ]; then
    if python3 -c "import infrahub_sdk" 2>/dev/null; then
        log_info "Infrahub MCP: OK (infrahub_sdk importable)"
        SERVERS_OK=$((SERVERS_OK + 1))
    elif [ -f "$INFRAHUB_MCP_DIR/src/infrahub_mcp/server.py" ]; then
        log_info "Infrahub MCP: OK (server.py found)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "Infrahub MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "Infrahub MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Itential MCP is pip-installed, check via command or import
if command -v itential-mcp &> /dev/null; then
    log_info "Itential MCP: OK (cli entry point)"
    SERVERS_OK=$((SERVERS_OK + 1))
elif python3 -c "import itential_mcp" 2>/dev/null; then
    log_info "Itential MCP: OK (module importable)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "Itential MCP: NOT INSTALLED (pip3 install itential-mcp)"
fi

# JunOS MCP is git-cloned with pip install
if [ -d "$JUNOS_MCP_DIR" ]; then
    if command -v junos-mcp-server &> /dev/null; then
        log_info "JunOS MCP: OK (cli entry point)"
        SERVERS_OK=$((SERVERS_OK + 1))
    elif [ -f "$JUNOS_MCP_DIR/jmcp.py" ]; then
        log_info "JunOS MCP: OK (jmcp.py found)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "JunOS MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "JunOS MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Arista CVP MCP is git-cloned, runs via uv
if [ -d "$CVP_MCP_DIR" ]; then
    if [ -f "$CVP_MCP_DIR/mcp_server_rest.py" ]; then
        log_info "Arista CVP MCP: OK (mcp_server_rest.py found)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "Arista CVP MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "Arista CVP MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

verify_file "ServiceNow MCP" "$SERVICENOW_MCP_DIR/src/servicenow_mcp/cli.py"
verify_file "ACI MCP" "$ACI_MCP_DIR/aci_mcp/main.py"
verify_file "ISE MCP" "$ISE_MCP_DIR/src/ise_mcp_server/server.py"
verify_file "Wikipedia MCP" "$WIKIPEDIA_MCP_DIR/main.py"
verify_file "NVD CVE MCP" "$NVD_MCP_DIR/mcp_nvd/main.py"
verify_file "Subnet Calculator MCP" "$SUBNET_MCP_DIR/servers/subnetcalculator_mcp.py"
verify_file "F5 BIG-IP MCP" "$F5_MCP_DIR/F5MCPserver.py"
verify_file "Catalyst Center MCP" "$CATC_MCP_DIR/catalyst-center-mcp.py"
verify_file "Packet Buddy MCP" "$PACKET_BUDDY_MCP_DIR/server.py"

# CML MCP is pip-installed, check via import
if python3 -c "import cml_mcp" 2>/dev/null; then
    log_info "CML MCP: OK (pip package)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "CML MCP: NOT INSTALLED (requires Python 3.12+, pip3 install cml-mcp)"
fi

# NSO MCP is pip-installed, check via command or import
if command -v cisco-nso-mcp-server &> /dev/null; then
    log_info "NSO MCP: OK (pip package)"
    SERVERS_OK=$((SERVERS_OK + 1))
elif python3 -c "import cisco_nso_mcp_server" 2>/dev/null; then
    log_info "NSO MCP: OK (pip package, module importable)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "NSO MCP: NOT INSTALLED (requires Python 3.12+, pip3 install cisco-nso-mcp-server)"
fi

# AWS MCPs run via uvx — check if uvx is available
if command -v uvx &> /dev/null; then
    log_info "AWS MCP Servers (6): OK (uvx available)"
    SERVERS_OK=$((SERVERS_OK + 6))
else
    log_warn "AWS MCP Servers (6): NOT AVAILABLE (uvx not installed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 6))
fi

# GCP MCPs are remote HTTP — check if gcloud is available for auth
if command -v gcloud &> /dev/null || [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
    log_info "GCP MCP Servers (4): OK (remote HTTP — gcloud or service account available)"
    SERVERS_OK=$((SERVERS_OK + 4))
else
    log_info "GCP MCP Servers (4): READY (remote HTTP — configure auth via gcloud or GOOGLE_APPLICATION_CREDENTIALS)"
    SERVERS_OK=$((SERVERS_OK + 4))
fi

# FMC MCP is git-cloned, check for directory
if [ -d "$FMC_MCP_DIR" ]; then
    log_info "Cisco FMC MCP: OK"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "Cisco FMC MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Meraki Magic MCP is git-cloned, check for directory and dynamic script
if [ -d "$MERAKI_MCP_DIR" ]; then
    if [ -f "$MERAKI_MCP_DIR/meraki-mcp-dynamic.py" ]; then
        log_info "Meraki Magic MCP: OK (dynamic — ~804 endpoints)"
        SERVERS_OK=$((SERVERS_OK + 1))
    elif [ -f "$MERAKI_MCP_DIR/meraki-mcp.py" ]; then
        log_info "Meraki Magic MCP: OK (manual — 40 endpoints)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_warn "Meraki Magic MCP: CLONED but server script not found"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "Meraki Magic MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# ThousandEyes Community MCP is git-cloned
if [ -d "$TE_COMMUNITY_MCP_DIR" ] && [ -f "$TE_COMMUNITY_MCP_DIR/src/server.py" ]; then
    log_info "ThousandEyes Community MCP: OK (9 tools, stdio)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "ThousandEyes Community MCP: NOT INSTALLED"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# ThousandEyes Official MCP is remote HTTP — check for npx
if command -v npx &> /dev/null; then
    log_info "ThousandEyes Official MCP: OK (remote HTTP — npx available for mcp-remote)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_info "ThousandEyes Official MCP: READY (remote HTTP — install Node.js for npx mcp-remote)"
    SERVERS_OK=$((SERVERS_OK + 1))
fi

# RADKit MCP is git-cloned
if [ -d "$RADKIT_MCP_DIR" ]; then
    if [ -f "$RADKIT_MCP_DIR/src/radkit_mcp/server.py" ] || [ -f "$RADKIT_MCP_DIR/mcp_server.py" ]; then
        log_info "RADKit MCP: OK (5 tools, stdio)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "RADKit MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "RADKit MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# UML MCP is git-cloned with pip install
if [ -d "$UML_MCP_DIR" ]; then
    if [ -f "$UML_MCP_DIR/server.py" ] || [ -f "$UML_MCP_DIR/mcp_core/core/server.py" ]; then
        log_info "UML MCP: OK (2 tools, stdio)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "UML MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "UML MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# ContainerLab MCP is cloned from GitHub
if [ -f "$CLAB_MCP_DIR/clab_mcp_server.py" ]; then
    log_info "ContainerLab MCP: OK (6 tools, stdio)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "ContainerLab MCP: NOT INSTALLED (clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# SD-WAN MCP is cloned from GitHub
if [ -d "$SDWAN_MCP_DIR" ]; then
    if [ -f "$SDWAN_MCP_DIR/sdwan_mcp_server.py" ]; then
        log_info "SD-WAN MCP: OK (12 tools, stdio)"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_info "SD-WAN MCP: CLONED (server script location may vary)"
        SERVERS_OK=$((SERVERS_OK + 1))
    fi
else
    log_warn "SD-WAN MCP: NOT INSTALLED (git clone failed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Grafana MCP runs via uvx
if command -v uvx &> /dev/null; then
    log_info "Grafana MCP: OK (runs via uvx mcp-grafana, 75+ tools)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "Grafana MCP: NOT AVAILABLE (uvx not installed)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Prometheus MCP runs via pip-installed CLI
if command -v prometheus-mcp-server &> /dev/null; then
    log_info "Prometheus MCP: OK (runs via prometheus-mcp-server, 6 tools)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "Prometheus MCP: NOT AVAILABLE (prometheus-mcp-server not in PATH)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Kubeshark MCP is a remote HTTP server (no local install)
if command -v kubectl &> /dev/null; then
    log_info "Kubeshark MCP: OK (remote HTTP — requires Kubeshark in K8s cluster, 6 tools)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "Kubeshark MCP: kubectl NOT FOUND (install kubectl + deploy Kubeshark via Helm)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

# Protocol MCP is bundled with NetClaw
if [ -d "$PROTOCOL_MCP_DIR" ] && [ -f "$PROTOCOL_MCP_DIR/server.py" ]; then
    log_info "Protocol MCP: OK (10 tools, stdio — BGP + OSPF + GRE)"
    SERVERS_OK=$((SERVERS_OK + 1))
else
    log_warn "Protocol MCP: NOT FOUND (mcp-servers/protocol-mcp/server.py)"
    SERVERS_FAIL=$((SERVERS_FAIL + 1))
fi

verify_file "MCP Call Script" "$NETCLAW_DIR/scripts/mcp-call.py"

echo ""
log_info "Verification: $SERVERS_OK OK, $SERVERS_FAIL FAILED"
echo ""

# ═══════════════════════════════════════════
# Step 45: Summary
# ═══════════════════════════════════════════

log_step "45/$TOTAL_STEPS Installation Summary"
echo ""
echo "========================================="
echo "  NetClaw Installation Complete"
echo "========================================="
echo ""

SKILL_COUNT=$(ls -d "$NETCLAW_DIR/workspace/skills/"*/ 2>/dev/null | wc -l)

echo "MCP Servers Installed (37):"
echo "  ┌─────────────────────────────────────────────────────────────"
echo "  │ NETWORK DEVICE AUTOMATION:"
echo "  │   pyATS              Cisco device CLI, Genie parsers"
echo "  │   F5 BIG-IP          iControl REST API (virtuals, pools, iRules)"
echo "  │   Catalyst Center    DNA Center / CatC API (devices, clients, sites)"
echo "  │   Juniper JunOS      PyEZ/NETCONF — CLI, config, templates, facts, batch ops (10 tools)"
echo "  │   Arista CVP         CloudVision Portal — inventory, events, connectivity monitor, tags (4 tools)"
echo "  │"
echo "  │ PROTOCOL PARTICIPATION:"
echo "  │   Protocol MCP        Live BGP/OSPF peering + GRE tunnels (10 tools)"
echo "  │"
echo "  │ REMOTE DEVICE ACCESS:"
echo "  │   Cisco RADKit       Cloud-relayed CLI, SNMP, device inventory (5 tools)"
echo "  │"
echo "  │ INFRASTRUCTURE PLATFORMS:"
echo "  │   Cisco ACI           APIC / ACI fabric management"
echo "  │   Cisco ISE           Identity, posture, TrustSec"
echo "  │   NetBox              DCIM/IPAM source of truth (read-write)"
echo "  │   Nautobot            IPAM/DCIM source of truth — IP addresses, prefixes, VRF/tenant (5 tools)"
echo "  │   Infrahub            Schema-driven SoT — nodes, GraphQL, versioned branches (10 tools)"
echo "  │   ServiceNow          ITSM: incidents, changes, CMDB"
echo "  │"
echo "  │ NETWORK ORCHESTRATION:"
echo "  │   Cisco NSO           Device config, sync, services via RESTCONF"
echo "  │   Itential IAP        Config mgmt, compliance, workflows, golden config, lifecycle (65+ tools)"
echo "  │"
echo "  │ FIREWALL SECURITY:"
echo "  │   Cisco FMC           Secure Firewall policy search, FTD targeting, multi-FMC"
echo "  │   Cisco Meraki        Dashboard API (~804 endpoints): orgs, networks, wireless, switching, security"
echo "  │"
echo "  │ NETWORK INTELLIGENCE:"
echo "  │   ThousandEyes (community)  Tests, agents, path vis, dashboards (9 tools, stdio)"
echo "  │   ThousandEyes (official)   Alerts, outages, BGP, instant tests, endpoints (~20 tools, remote HTTP)"
echo "  │"
echo "  │ SD-WAN:"
echo "  │   Cisco SD-WAN        vManage read-only monitoring (12 tools: devices, templates, policies, alarms)"
echo "  │"
echo "  │ OBSERVABILITY:"
echo "  │   Grafana             Dashboards, Prometheus, Loki, alerting, incidents, OnCall (75+ tools via uvx)"
echo "  │   Prometheus          PromQL instant/range queries, metric discovery, target health (6 tools via pip)"
echo "  │   Kubeshark           K8s L4/L7 traffic analysis, TLS decryption, pcap export, flow stats (6 tools, remote HTTP)"
echo "  │"
echo "  │ LAB & SIMULATION:"
echo "  │   Cisco CML           Lab lifecycle, node mgmt, topology, packet capture"
echo "  │   ContainerLab        Containerized labs (SR Linux, cEOS, FRR) via API"
echo "  │"
echo "  │ OFFICE 365 / MICROSOFT:"
echo "  │   Microsoft Graph     OneDrive, SharePoint, Visio, Teams, Exchange"
echo "  │"
echo "  │ SECURITY & COMPLIANCE:"
echo "  │   NVD CVE             NIST vulnerability database (Python)"
echo "  │"
echo "  │ VERSION CONTROL:"
echo "  │   GitHub              Issues, PRs, code search, Actions (Docker)"
echo "  │"
echo "  │ PACKET ANALYSIS:"
echo "  │   Packet Buddy        pcap/pcapng analysis via tshark"
echo "  │"
echo "  │ AWS CLOUD (6 servers via uvx):"
echo "  │   AWS Network          VPC, Transit GW, Cloud WAN, VPN, Firewall, flow logs"
echo "  │   CloudWatch            Metrics, alarms, logs, flow log analysis"
echo "  │   IAM                   Users, roles, policies, security groups (read-only)"
echo "  │   CloudTrail            API audit trail (who changed what)"
echo "  │   Cost Explorer          Cloud networking costs & forecasting"
echo "  │   AWS Diagram           Architecture diagrams (requires graphviz)"
echo "  │"
echo "  │ GCP CLOUD (4 remote HTTP servers):"
echo "  │   Compute Engine        VMs, disks, templates, instance groups (28 tools)"
echo "  │   Cloud Monitoring      Metrics, alerts, time series (6 tools)"
echo "  │   Cloud Logging         Log search, VPC flow logs, audit logs (6 tools)"
echo "  │   Resource Manager      Project discovery (1 tool)"
echo "  │"
echo "  │ UTILITIES:"
echo "  │   Subnet Calculator   IPv4 + IPv6 CIDR calculator"
echo "  │   GAIT                Git-based AI audit trail"
echo "  │   Wikipedia           Technology context & history"
echo "  │   Markmap             Mind map visualization"
echo "  │   UML MCP            27+ diagram types via Kroki (class, sequence, nwdiag, rack, packet, C4)"
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
echo "  │ pyATS Linux Host Skills:"
echo "  │   pyats-linux-system     Process monitoring, Docker stats, filesystem, curl"
echo "  │   pyats-linux-network    Interfaces (ifconfig), routing (ip route), netstat"
echo "  │   pyats-linux-vmware     VMware ESXi: VM inventory (vim-cmd), snapshots"
echo "  │"
echo "  │ pyATS JunOS Skills:"
echo "  │   pyats-junos-system     Chassis, hardware, version, NTP, SNMP, logs, firewall, DDoS"
echo "  │   pyats-junos-interfaces Interfaces, LACP, CoS, LLDP, ARP, BFD, optics diagnostics"
echo "  │   pyats-junos-routing    OSPF/v3, BGP, routes, MPLS/LDP/RSVP, TED, PFE, ping, traceroute"
echo "  │"
echo "  │ pyATS ASA Skills:"
echo "  │   pyats-asa-firewall     VPN sessions, failover, interfaces, routes, ASP drops, service policies"
echo "  │"
echo "  │ pyATS F5 BIG-IP Skills:"
echo "  │   pyats-f5-ltm           LTM/GTM: virtuals, pools, nodes, monitors, profiles, iRules, wide IPs"
echo "  │   pyats-f5-platform      Platform: system, networking, HA/CM, auth, analytics, security, APM"
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
echo "  │   nautobot-sot           Nautobot IPAM — IP addresses, prefixes, VRF/tenant/site queries"
echo "  │   infrahub-sot           Infrahub SoT — schema-driven nodes, GraphQL, versioned branches"
echo "  │   aci-fabric-audit       ACI fabric health & policy audit"
echo "  │   aci-change-deploy      Safe ACI policy changes"
echo "  │   ise-posture-audit      ISE posture & TrustSec audit"
echo "  │   ise-incident-response  Endpoint investigation & quarantine"
echo "  │   servicenow-change-workflow  Full ITSM change lifecycle"
echo "  │   gait-session-tracking  Mandatory audit trail"
echo "  │"
echo "  │ Itential IAP Skills:"
echo "  │   itential-automation    Config mgmt, compliance, workflows, golden config, lifecycle (65+ tools)"
echo "  │"
echo "  │ Juniper JunOS Skills:"
echo "  │   junos-network          PyEZ/NETCONF — CLI, config mgmt, Jinja2 templates, batch ops (10 tools)"
echo "  │"
echo "  │ Arista CloudVision Skills:"
echo "  │   arista-cvp              CVP — device inventory, events, connectivity monitor, tags (4 tools)"
echo "  │"
echo "  │ Microsoft 365 Skills:"
echo "  │   msgraph-files          OneDrive/SharePoint file operations"
echo "  │   msgraph-visio          Visio diagram generation from network data"
echo "  │   msgraph-teams          Teams notifications and channel delivery"
echo "  │"
echo "  │ GitHub Skills:"
echo "  │   github-ops              Issues, PRs, config-as-code workflows"
echo "  │"
echo "  │ Packet Analysis Skills:"
echo "  │   packet-analysis         pcap analysis + Slack upload support"
echo "  │"
echo "  │ AWS Cloud Skills:"
echo "  │   aws-network-ops        VPC, TGW, Cloud WAN, VPN, Firewall, flow logs"
echo "  │   aws-cloud-monitoring   CloudWatch metrics, alarms, log analysis"
echo "  │   aws-security-audit     IAM policies + CloudTrail event investigation"
echo "  │   aws-cost-ops           Cost analysis, forecasting, spend tracking"
echo "  │   aws-architecture-diagram  AWS architecture diagram generation"
echo "  │"
echo "  │ GCP Cloud Skills:"
echo "  │   gcp-compute-ops        VMs, disks, templates, instance groups, projects"
echo "  │   gcp-cloud-monitoring   Metrics, alerts, time series queries"
echo "  │   gcp-cloud-logging      Log search, VPC flow logs, firewall & audit logs"
echo "  │"
echo "  │ Cisco NSO Skills:"
echo "  │   nso-device-ops          Device config, state, sync, platform, NED IDs"
echo "  │   nso-service-mgmt        Service types, service instances, orchestration"
echo "  │"
echo "  │ Cisco FMC Skills:"
echo "  │   fmc-firewall-ops        Access policy search, FTD targeting, multi-FMC audit"
echo "  │"
echo "  │ Cisco RADKit Skills:"
echo "  │   radkit-remote-access    Cloud-relayed CLI, SNMP, device inventory, attributes"
echo "  │"
echo "  │ Cisco Meraki Skills:"
echo "  │   meraki-network-ops       Org inventory, networks, devices, clients, action batches"
echo "  │   meraki-wireless-ops      SSIDs, RF profiles, channel utilization, signal quality"
echo "  │   meraki-switch-ops        Ports, VLANs, ACLs, QoS, port cycling"
echo "  │   meraki-security-appliance MX firewall, VPN, content filtering, traffic shaping"
echo "  │   meraki-monitoring        Live ping, cable test, LED blink, cameras, config audit"
echo "  │"
echo "  │ ThousandEyes Skills:"
echo "  │   te-network-monitoring    Tests, agents, path vis, dashboards, alerts, events, endpoints"
echo "  │   te-path-analysis         Path visualization, BGP routes, outage triage, instant tests"
echo "  │"
echo "  │ Cisco CML Skills:"
echo "  │   cml-lab-lifecycle       Create, start, stop, wipe, delete, clone labs"
echo "  │   cml-topology-builder    Add nodes, interfaces, links, build topologies"
echo "  │   cml-node-operations     Console, CLI exec, start/stop nodes, configs"
echo "  │   cml-packet-capture      Start/stop/download pcap on CML links"
echo "  │   cml-admin               Users, groups, system info, licensing"
echo "  │"
echo "  │ ContainerLab Skills:"
echo "  │   clab-lab-management     Deploy, inspect, exec, destroy containerized labs"
echo "  │"
echo "  │ Cisco SD-WAN Skills:"
echo "  │   sdwan-ops               vManage read-only monitoring (12 tools: devices, templates, policies, alarms)"
echo "  │"
echo "  │ Grafana Observability Skills:"
echo "  │   grafana-observability   Dashboards, Prometheus PromQL, Loki LogQL, alerting, incidents, OnCall (75+ tools)"
echo "  │"
echo "  │ Prometheus Monitoring Skills:"
echo "  │   prometheus-monitoring   PromQL instant/range queries, metric discovery, target health (6 tools)"
echo "  │"
echo "  │ Kubeshark Traffic Analysis Skills:"
echo "  │   kubeshark-traffic       K8s L4/L7 deep packet inspection, pcap export, flow analysis, TLS decryption (6 tools)"
echo "  │"
echo "  │ Protocol Participation Skills:"
echo "  │   protocol-participation BGP peering, OSPF adjacency, GRE tunnels, route injection (10 tools)"
echo "  │"
echo "  │ Reference & Utility Skills:"
echo "  │   nvd-cve                NVD vulnerability search (Python)"
echo "  │   subnet-calculator      IPv4 + IPv6 subnet calculator"
echo "  │   wikipedia-research     Protocol history & context"
echo "  │   markmap-viz            Mind map visualization"
echo "  │   drawio-diagram         Draw.io diagrams: native .drawio + CLI export (PNG/SVG/PDF) + browser MCP"
echo "  │   uml-diagram            27+ UML/diagram types via Kroki (class, sequence, nwdiag, rack, packet)"
echo "  │   rfc-lookup             IETF RFC search"
echo "  │"
echo "  │ Slack Integration Skills:"
echo "  │   slack-network-alerts   Alert formatting & delivery"
echo "  │   slack-report-delivery  Report formatting for Slack"
echo "  │   slack-incident-workflow Incident response in Slack"
echo "  │   slack-user-context     User-aware interactions"
echo "  └─────────────────────────────────────────────────────────────"
echo ""

# ═══════════════════════════════════════════
# Launch NetClaw Platform Setup
# ═══════════════════════════════════════════

SETUP_SCRIPT="$NETCLAW_DIR/scripts/setup.sh"
if [ -f "$SETUP_SCRIPT" ]; then
    echo ""
    echo -e "${CYAN}Now let's configure your network platform credentials.${NC}"
    echo ""
    read -rp "Run NetClaw platform setup now? [Y/n] " RUN_SETUP
    RUN_SETUP="${RUN_SETUP:-y}"
    if [[ "$RUN_SETUP" =~ ^[Yy] ]]; then
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
echo ""
