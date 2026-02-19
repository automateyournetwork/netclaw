#!/usr/bin/env bash
# NetClaw Installation Script
# Clones, builds, and configures all 5 MCP servers for the NetClaw agent

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

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_DIR="$NETCLAW_DIR/mcp-servers"

echo "========================================="
echo "  NetClaw - Network Automation Agent"
echo "  Installation Script"
echo "========================================="
echo ""
echo "  Project: $NETCLAW_DIR"
echo ""

# ═══════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════

log_step "1/8 Checking prerequisites..."

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

if ! check_command npm; then
    log_error "npm is required"
    MISSING=1
fi

if ! check_command npx; then
    log_error "npx is required (comes with npm)"
    MISSING=1
fi

if ! check_command python3; then
    log_error "Python 3 is required for pyATS MCP server"
    MISSING=1
else
    log_info "Python version: $(python3 --version)"
fi

if ! check_command pip3; then
    if ! check_command pip; then
        log_error "pip3 is required for Python package installation"
        MISSING=1
    fi
fi

if ! check_command git; then
    log_error "git is required to clone MCP server repos"
    MISSING=1
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

log_step "2/9 Installing OpenClaw..."

if command -v openclaw &> /dev/null; then
    log_info "OpenClaw already installed: $(openclaw --version 2>/dev/null || echo 'version unknown')"
else
    log_info "Installing OpenClaw via npm..."
    npm install -g openclaw@latest
    if command -v openclaw &> /dev/null; then
        log_info "OpenClaw installed successfully"
    else
        log_warn "openclaw not found on PATH after install"
        log_warn "You may need to restart your terminal or add npm global bin to PATH"
        log_warn "Try: export PATH=\"$(npm config get prefix)/bin:\$PATH\""
    fi
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: Create mcp-servers directory
# ═══════════════════════════════════════════

log_step "3/9 Setting up MCP servers directory..."

mkdir -p "$MCP_DIR"
log_info "MCP servers directory: $MCP_DIR"
echo ""

# ═══════════════════════════════════════════
# Step 4: pyATS MCP (clone + pip install)
# ═══════════════════════════════════════════

log_step "4/9 Installing pyATS MCP Server..."
echo "  Source: https://github.com/automateyournetwork/pyATS_MCP"
echo "  Requires: clone + pip install"

PYATS_MCP_DIR="$MCP_DIR/pyATS_MCP"

if [ -d "$PYATS_MCP_DIR" ]; then
    log_info "pyATS MCP already cloned. Pulling latest..."
    git -C "$PYATS_MCP_DIR" pull || log_warn "git pull failed, using existing version"
else
    log_info "Cloning pyATS MCP..."
    git clone https://github.com/automateyournetwork/pyATS_MCP.git "$PYATS_MCP_DIR"
fi

log_info "Installing Python dependencies (pyats[full], mcp, pydantic, python-dotenv)..."
pip3 install -r "$PYATS_MCP_DIR/requirements.txt" || {
    log_warn "requirements.txt install failed. Trying individual packages..."
    pip3 install "pyats[full]" mcp pydantic python-dotenv
}

# Verify the server script exists
if [ -f "$PYATS_MCP_DIR/pyats_mcp_server.py" ]; then
    log_info "pyATS MCP server script: $PYATS_MCP_DIR/pyats_mcp_server.py"
else
    log_error "pyats_mcp_server.py not found in $PYATS_MCP_DIR"
    log_error "Check the repo structure and try again"
fi

echo ""

# ═══════════════════════════════════════════
# Step 4: Markmap MCP (clone + npm build + npm link)
# ═══════════════════════════════════════════

log_step "5/9 Installing Markmap MCP Server..."
echo "  Source: https://github.com/automateyournetwork/markmap_mcp"
echo "  Requires: clone + npm install + npm run build + npm link"

MARKMAP_MCP_DIR="$MCP_DIR/markmap_mcp"

if [ -d "$MARKMAP_MCP_DIR" ]; then
    log_info "Markmap MCP already cloned. Pulling latest..."
    git -C "$MARKMAP_MCP_DIR" pull || log_warn "git pull failed, using existing version"
else
    log_info "Cloning Markmap MCP..."
    git clone https://github.com/automateyournetwork/markmap_mcp.git "$MARKMAP_MCP_DIR"
fi

# The repo has a nested structure: markmap_mcp/markmap-mcp/
MARKMAP_INNER="$MARKMAP_MCP_DIR/markmap-mcp"

if [ -d "$MARKMAP_INNER" ]; then
    log_info "Building Markmap MCP (in nested markmap_mcp/markmap-mcp/ directory)..."
    cd "$MARKMAP_INNER"
    npm install
    npm run build
    npm link
    cd "$NETCLAW_DIR"

    if command -v markmap-mcp &> /dev/null; then
        log_info "markmap-mcp command available globally: $(which markmap-mcp)"
    else
        log_warn "npm link succeeded but markmap-mcp not on PATH"
        log_warn "Falling back to direct node path in config"
        log_info "Will use: node $MARKMAP_INNER/dist/index.js"
    fi
else
    log_warn "Expected nested directory not found at $MARKMAP_INNER"
    log_warn "Trying top-level directory instead..."
    cd "$MARKMAP_MCP_DIR"
    npm install
    npm run build
    npm link || true
    cd "$NETCLAW_DIR"
fi

echo ""

# ═══════════════════════════════════════════
# Step 5: Draw.io MCP (npx only - no install needed)
# ═══════════════════════════════════════════

log_step "6/9 Caching Draw.io MCP Server..."
echo "  Source: https://github.com/jgraph/drawio-mcp"
echo "  Requires: npx @drawio/mcp (no clone needed)"

log_info "Pre-downloading @drawio/mcp npm package..."
npm cache add @drawio/mcp 2>/dev/null || log_warn "Could not pre-cache @drawio/mcp (will download on first use)"
log_info "Draw.io MCP ready (runs via: npx @drawio/mcp)"

echo ""

# ═══════════════════════════════════════════
# Step 6: RFC MCP (npx only - no install needed)
# ═══════════════════════════════════════════

log_step "7/9 Caching RFC MCP Server..."
echo "  Source: https://github.com/mjpitz/mcp-rfc"
echo "  Requires: npx @mjpitz/mcp-rfc (no clone needed)"

log_info "Pre-downloading @mjpitz/mcp-rfc npm package..."
npm cache add @mjpitz/mcp-rfc 2>/dev/null || log_warn "Could not pre-cache @mjpitz/mcp-rfc (will download on first use)"
log_info "RFC MCP ready (runs via: npx @mjpitz/mcp-rfc)"

echo ""

# ═══════════════════════════════════════════
# Step 7: NVD CVE MCP (npx only - no install needed)
# ═══════════════════════════════════════════

log_step "8/9 Caching NVD CVE MCP Server..."
echo "  Source: https://github.com/SOCTeam-ai/nvd-cve-mcp-server"
echo "  Requires: npx nvd-cve-mcp-server (no clone needed)"

log_info "Pre-downloading nvd-cve-mcp-server npm package..."
npm cache add nvd-cve-mcp-server 2>/dev/null || log_warn "Could not pre-cache nvd-cve-mcp-server (will download on first use)"
log_info "NVD CVE MCP ready (runs via: npx -y nvd-cve-mcp-server)"

echo ""

# ═══════════════════════════════════════════
# Step 8: Generate openclaw.json with real paths
# ═══════════════════════════════════════════

log_step "9/9 Deploying skills and configuration..."

# Update pyats skill with real paths for this installation
PYATS_SCRIPT="$PYATS_MCP_DIR/pyats_mcp_server.py"
TESTBED_PATH="$NETCLAW_DIR/testbed/testbed.yaml"

# Skills use $PYATS_MCP_SCRIPT and $PYATS_TESTBED_PATH as shell variable
# references. These are resolved at runtime from the OpenClaw .env file.
# No sed replacement needed — the variables are exported by OpenClaw.
log_info "pyATS skill files use \$PYATS_MCP_SCRIPT and \$PYATS_TESTBED_PATH env vars"

# Deploy skills to OpenClaw workspace
OPENCLAW_DIR="$HOME/.openclaw"
if [ -d "$OPENCLAW_DIR" ]; then
    mkdir -p "$OPENCLAW_DIR/workspace/skills"
    cp -r "$NETCLAW_DIR/workspace/skills/"* "$OPENCLAW_DIR/workspace/skills/"
    log_info "Deployed skills to $OPENCLAW_DIR/workspace/skills/"

    # Set pyATS environment variables in OpenClaw .env
    OPENCLAW_ENV="$OPENCLAW_DIR/.env"
    if [ ! -f "$OPENCLAW_ENV" ]; then
        touch "$OPENCLAW_ENV"
    fi
    grep -q "^PYATS_TESTBED_PATH=" "$OPENCLAW_ENV" || \
        echo "PYATS_TESTBED_PATH=$TESTBED_PATH" >> "$OPENCLAW_ENV"
    grep -q "^PYATS_MCP_SCRIPT=" "$OPENCLAW_ENV" || \
        echo "PYATS_MCP_SCRIPT=$PYATS_SCRIPT" >> "$OPENCLAW_ENV"
    log_info "Set PYATS_TESTBED_PATH and PYATS_MCP_SCRIPT in $OPENCLAW_ENV"
else
    log_warn "OpenClaw directory not found at $OPENCLAW_DIR"
    log_warn "Run 'openclaw onboard --install-daemon' first"
fi

# Create .env if it doesn't exist
ENV_FILE="$NETCLAW_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    cp "$NETCLAW_DIR/.env.example" "$ENV_FILE"
    log_info "Created .env from template"
    log_warn "Edit $ENV_FILE with your actual device credentials"
fi

echo ""

# ═══════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════

echo "========================================="
echo "  NetClaw Installation Complete"
echo "========================================="
echo ""

echo "Tools Installed:"
echo "  ┌─────────────────────────────────────────────────────────────"
echo "  │ pyATS         [clone+pip]  $PYATS_MCP_DIR"
echo "  │ Markmap       [clone+npm]  $MARKMAP_MCP_DIR/markmap-mcp"
echo "  │ Draw.io       [npx]        npx @drawio/mcp"
echo "  │ RFC           [npx]        npx @mjpitz/mcp-rfc"
echo "  │ NVD CVE       [npx]        npx -y nvd-cve-mcp-server"
echo "  └─────────────────────────────────────────────────────────────"
echo ""
echo "Skills Deployed (11):"
echo "  ┌─────────────────────────────────────────────────────────────"
echo "  │ pyATS Skills (7):"
echo "  │   pyats-network       Core device automation (8 MCP tools)"
echo "  │   pyats-health-check  CPU, memory, interfaces, NTP, logs"
echo "  │   pyats-routing       OSPF, BGP, EIGRP, IS-IS analysis"
echo "  │   pyats-security      ACL, AAA, CoPP, hardening audit"
echo "  │   pyats-topology      CDP/LLDP discovery, subnet mapping"
echo "  │   pyats-config-mgmt   Change control, baseline, rollback"
echo "  │   pyats-troubleshoot  OSI-layer troubleshooting methodology"
echo "  │ Tool Skills (4):"
echo "  │   markmap-viz         Mind map visualization"
echo "  │   drawio-diagram      Draw.io network diagrams"
echo "  │   rfc-lookup          IETF RFC search and retrieval"
echo "  │   nvd-cve             NVD vulnerability database search"
echo "  └─────────────────────────────────────────────────────────────"
echo ""

log_info "Next steps:"
echo "  1. Copy .env.example to .env and set your device credentials"
echo "  2. Edit testbed/testbed.yaml with your network devices"
echo "  3. Restart the gateway: openclaw gateway (foreground)"
echo "  4. Chat: openclaw chat"
echo ""
