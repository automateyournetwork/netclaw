#!/usr/bin/env bash
# Enable IP Fabric Network Assurance Integration for existing NetClaw installations
# This script configures the IP Fabric MCP Server connection (remote HTTP via mcp-remote)
#
# Developed in collaboration with:
#   - Daren Fulwell (Field CTO, IP Fabric)
#   - John Capobianco (Creator, NetClaw)
#
# IP Fabric MCP is built into IP Fabric appliances - no clone/build steps required

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

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_ENV="$OPENCLAW_DIR/.env"
OPENCLAW_CONFIG="$OPENCLAW_DIR/openclaw.json"

echo "========================================="
echo "  IP Fabric Network Assurance Integration"
echo "  for NetClaw"
echo "========================================="
echo ""
echo "  10 MCP Tools: health assessment, path analysis, diagrams"
echo "  Documentation: https://docs.ipfabric.io/latest/IP_Fabric_Settings/integration/mcp/"
echo ""
echo "  Partnership: Daren Fulwell (IP Fabric) + John Capobianco (NetClaw)"
echo ""

# ═══════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════

log_step "1/4 Checking prerequisites..."

MISSING=0

if ! command -v node &> /dev/null; then
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

if ! command -v npx &> /dev/null; then
    log_error "npx not found (required for mcp-remote proxy)"
    MISSING=1
fi

if [ "$MISSING" -eq 1 ]; then
    log_error "Missing prerequisites. Please install them and re-run."
    exit 1
fi

log_info "All prerequisites satisfied."
echo ""

# ═══════════════════════════════════════════
# Step 2: Configure Credentials
# ═══════════════════════════════════════════

log_step "2/4 Configuring IP Fabric credentials..."

# Ensure OpenClaw directory exists
mkdir -p "$OPENCLAW_DIR"
[ -f "$OPENCLAW_ENV" ] || touch "$OPENCLAW_ENV"

# Helper function to set env vars
_set_env_var() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        sed -i.bak "s|^${key}=.*|${key}=${val}|" "$OPENCLAW_ENV" && rm -f "$OPENCLAW_ENV.bak"
    else
        echo "${key}=${val}" >> "$OPENCLAW_ENV"
    fi
}

echo ""
echo "IP Fabric MCP Server requires:"
echo "  1. IP Fabric appliance URL (e.g., https://ipfabric.example.com)"
echo "  2. API token with RBAC permissions"
echo ""
echo "Generate API token in IP Fabric UI: Settings → API Tokens"
echo ""

read -r -p "Configure IP Fabric credentials now? [Y/n] " config_now
if [[ ! "$config_now" =~ ^[Nn]$ ]]; then
    echo ""
    read -r -p "IP Fabric host URL (e.g., https://ipfabric.example.com): " ipfabric_host

    if [ -n "$ipfabric_host" ]; then
        # Remove trailing slash if present
        ipfabric_host="${ipfabric_host%/}"
        _set_env_var "IPFABRIC_HOST" "$ipfabric_host"
        log_info "Set IPFABRIC_HOST=$ipfabric_host"

        read -r -sp "IP Fabric API token: " ipfabric_token
        echo ""

        if [ -n "$ipfabric_token" ]; then
            _set_env_var "IPFABRIC_API_TOKEN" "$ipfabric_token"
            log_info "Set IPFABRIC_API_TOKEN=***"
        else
            log_warn "No token provided. Set IPFABRIC_API_TOKEN in $OPENCLAW_ENV later."
            _set_env_var "IPFABRIC_API_TOKEN" "your-api-token-here"
        fi
    else
        log_warn "No host provided. Setting placeholder values."
        _set_env_var "IPFABRIC_HOST" "https://ipfabric.example.com"
        _set_env_var "IPFABRIC_API_TOKEN" "your-api-token-here"
    fi

    log_info "Credentials saved to $OPENCLAW_ENV"
else
    log_info "Skipping credential configuration."
    echo ""
    echo "Set these variables in $OPENCLAW_ENV later:"
    echo "  IPFABRIC_HOST=https://ipfabric.example.com"
    echo "  IPFABRIC_API_TOKEN=your-api-token"

    # Set placeholders
    _set_env_var "IPFABRIC_HOST" "https://ipfabric.example.com"
    _set_env_var "IPFABRIC_API_TOKEN" "your-api-token-here"
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: Verify MCP Connectivity
# ═══════════════════════════════════════════

log_step "3/4 Verifying IP Fabric MCP connectivity..."

# Load the configured values
source "$OPENCLAW_ENV" 2>/dev/null || true

if [ "${IPFABRIC_HOST:-}" != "https://ipfabric.example.com" ] && [ "${IPFABRIC_API_TOKEN:-}" != "your-api-token-here" ]; then
    # Try to reach the MCP endpoint
    MCP_URL="${IPFABRIC_HOST}/mcp"
    log_info "Testing connection to $MCP_URL..."

    if curl -sf --max-time 10 -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${IPFABRIC_API_TOKEN}" \
        "$MCP_URL" 2>/dev/null | grep -q "^[23]"; then
        log_info "✓ Successfully connected to IP Fabric MCP endpoint"
    else
        log_warn "Could not verify MCP endpoint (may require specific MCP request format)"
        log_info "Connection will be verified when OpenClaw starts"
    fi
else
    log_warn "Placeholder credentials detected - skipping connectivity test"
    log_info "Update credentials in $OPENCLAW_ENV and restart OpenClaw"
fi

echo ""

# ═══════════════════════════════════════════
# Step 4: Verify Configuration
# ═══════════════════════════════════════════

log_step "4/4 Verifying configuration..."

# Check if MCP config exists in openclaw.json
if [ -f "$OPENCLAW_CONFIG" ]; then
    if grep -q "ipfabric-mcp" "$OPENCLAW_CONFIG" 2>/dev/null; then
        log_info "✓ IP Fabric MCP already registered in openclaw.json"
    else
        log_warn "IP Fabric MCP not found in openclaw.json"
        log_info "The MCP will be registered when you run install.sh or add manually"
        echo ""
        echo "Add to $OPENCLAW_CONFIG under mcp.servers:"
        echo '  "ipfabric-mcp": {'
        echo '    "command": "npx",'
        echo '    "args": ["-y", "mcp-remote", "${IPFABRIC_HOST}/mcp", "--header", "Authorization:${IPFABRIC_AUTH_HEADER}"],'
        echo '    "env": { "IPFABRIC_AUTH_HEADER": "Bearer ${IPFABRIC_API_TOKEN}" }'
        echo '  }'
    fi
else
    log_warn "openclaw.json not found at $OPENCLAW_CONFIG"
    log_info "Run install.sh to complete NetClaw setup"
fi

echo ""

# ═══════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════

echo "========================================="
echo "  IP Fabric Integration Complete"
echo "========================================="
echo ""
echo "  Environment variables saved to:"
echo "    $OPENCLAW_ENV"
echo ""
echo "  MCP Tools Available:"
echo "    ipf_network_health_assess    - Network health overview"
echo "    ipf_pathlookup_unicast       - Trace path between IPs"
echo "    ipf_pathlookup_host-to-gateway - Trace host to gateway"
echo "    ipf_pathlookup_multicast     - Trace multicast paths"
echo "    ipf_png_pathlookup_*         - Path diagrams (PNG)"
echo "    ipf_api_endpoint_search      - API endpoint discovery"
echo "    ipf_api_endpoint_details     - API endpoint details"
echo "    api_invoke                   - Execute custom API calls"
echo ""
echo "  Usage:"
echo "    openclaw"
echo "    > /ipfabric check network health"
echo "    > /ipfabric show path from 10.0.1.5 to 10.0.2.10 with diagram"
echo "    > /ipfabric show BGP neighbors not Established"
echo ""
echo "  Next Steps:"
echo "    1. Restart OpenClaw gateway: systemctl --user restart openclaw-gateway.service"
echo "    2. Verify MCP: openclaw mcp list | grep ipfabric"
echo "    3. Try a query: /ipfabric check network health"
echo ""
echo "  Documentation: docs/IPFABRIC.md"
echo ""
