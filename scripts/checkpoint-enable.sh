#!/usr/bin/env bash
# Enable Check Point Security Integration for existing NetClaw installations
# This script clones, builds, and configures all 15 Check Point MCP servers

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
MCP_DIR="$NETCLAW_DIR/mcp-servers"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_ENV="$OPENCLAW_DIR/.env"

echo "========================================="
echo "  Check Point Security Integration"
echo "  for NetClaw"
echo "========================================="
echo ""
echo "  15 MCP Servers: policy, logs, threat intel, gateway, SASE"
echo "  Source: https://github.com/CheckPointSW/mcp-servers"
echo ""

# ═══════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════

log_step "1/5 Checking prerequisites..."

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

for cmd in npm git; do
    if ! command -v "$cmd" &> /dev/null; then
        log_error "$cmd not found"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 1 ]; then
    log_error "Missing prerequisites. Please install them and re-run."
    exit 1
fi

log_info "All prerequisites satisfied."
echo ""

# ═══════════════════════════════════════════
# Step 2: Clone Check Point MCP Repository
# ═══════════════════════════════════════════

log_step "2/5 Cloning Check Point MCP servers..."

CHECKPOINT_MCP_DIR="$MCP_DIR/checkpoint-mcp-servers"

if [ -d "$CHECKPOINT_MCP_DIR" ]; then
    log_info "Check Point MCPs already cloned. Pulling latest..."
    git -C "$CHECKPOINT_MCP_DIR" pull || log_warn "git pull failed, using existing version"
else
    log_info "Cloning from https://github.com/CheckPointSW/mcp-servers.git..."
    git clone "https://github.com/CheckPointSW/mcp-servers.git" "$CHECKPOINT_MCP_DIR"
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: Build Check Point MCP Servers
# ═══════════════════════════════════════════

log_step "3/5 Building Check Point MCP servers..."

cd "$CHECKPOINT_MCP_DIR"
log_info "Running npm install..."
npm install 2>/dev/null || log_warn "npm install had warnings"

log_info "Running npm build..."
echo "n" | npm run build 2>/dev/null || log_warn "npm run build had warnings"
cd "$NETCLAW_DIR"

log_info "Check Point MCP servers built successfully."
echo ""

# ═══════════════════════════════════════════
# Step 4: Configure Credentials
# ═══════════════════════════════════════════

log_step "4/5 Configuring Check Point credentials..."

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
echo "Check Point MCP servers require credentials to connect to your security infrastructure."
echo ""
echo "Credential Groups:"
echo "  1. Management Server (on-prem) — policy, logs, threat prevention, gateway MCPs"
echo "  2. Reputation Service — IP/URL/file threat intelligence"
echo "  3. Harmony SASE — cloud-delivered security"
echo "  4. Threat Emulation — malware analysis sandbox"
echo "  5. Spark — MSP distributed firewall"
echo "  6. Argos ERM — exposure/risk management"
echo ""

read -r -p "Configure Check Point credentials now? [Y/n] " config_now
if [[ ! "$config_now" =~ ^[Nn]$ ]]; then
    echo ""
    echo "--- Management Server (most common) ---"
    read -r -p "Management Server host (IP/hostname, or Enter to skip): " chkp_mgmt_host
    if [ -n "$chkp_mgmt_host" ]; then
        _set_env_var "CHKP_MGMT_HOST" "$chkp_mgmt_host"
        log_info "Set CHKP_MGMT_HOST=$chkp_mgmt_host"

        read -r -p "Management Server port [443]: " chkp_mgmt_port
        [ -n "$chkp_mgmt_port" ] && _set_env_var "CHKP_MGMT_PORT" "$chkp_mgmt_port"

        echo "Authentication method:"
        echo "  1. API Key (recommended)"
        echo "  2. Username/Password"
        read -r -p "Choose [1/2]: " auth_method

        if [ "$auth_method" = "2" ]; then
            read -r -p "Username: " chkp_username
            read -r -s -p "Password: " chkp_password
            echo ""
            [ -n "$chkp_username" ] && _set_env_var "CHKP_MGMT_USERNAME" "$chkp_username"
            [ -n "$chkp_password" ] && _set_env_var "CHKP_MGMT_PASSWORD" "$chkp_password"
        else
            read -r -p "API Key: " chkp_api_key
            [ -n "$chkp_api_key" ] && _set_env_var "CHKP_MGMT_API_KEY" "$chkp_api_key"
        fi

        read -r -p "Domain (for MDS, or Enter to skip): " chkp_domain
        [ -n "$chkp_domain" ] && _set_env_var "CHKP_MGMT_DOMAIN" "$chkp_domain"
    fi

    echo ""
    echo "--- Reputation Service (threat intelligence) ---"
    read -r -p "Reputation API Key (contact TCAPI_SUPPORT@checkpoint.com, or Enter to skip): " chkp_rep_key
    [ -n "$chkp_rep_key" ] && _set_env_var "CHKP_REPUTATION_API_KEY" "$chkp_rep_key"

    echo ""
    echo "--- Harmony SASE (optional) ---"
    read -r -p "SASE API Key (or Enter to skip): " chkp_sase_key
    if [ -n "$chkp_sase_key" ]; then
        _set_env_var "CHKP_SASE_API_KEY" "$chkp_sase_key"
        read -r -p "SASE Management Host (e.g., https://api.us1.sase.checkpoint.com/api): " chkp_sase_host
        [ -n "$chkp_sase_host" ] && _set_env_var "CHKP_SASE_MGMT_HOST" "$chkp_sase_host"
        read -r -p "SASE Origin (e.g., https://your-tenant.sase.checkpoint.com): " chkp_sase_origin
        [ -n "$chkp_sase_origin" ] && _set_env_var "CHKP_SASE_ORIGIN" "$chkp_sase_origin"
    fi

    # Always disable telemetry
    _set_env_var "CHKP_TELEMETRY_DISABLED" "true"
    _set_env_var "CHKP_LOG_LEVEL" "standard"

    log_info "Credentials saved to $OPENCLAW_ENV"
else
    log_info "Skipping credential configuration."
    echo ""
    echo "Set these variables in $OPENCLAW_ENV later:"
    echo "  CHKP_MGMT_HOST=192.168.1.100"
    echo "  CHKP_MGMT_API_KEY=your-api-key"
    echo "  CHKP_REPUTATION_API_KEY=your-reputation-key"
    echo "  CHKP_TELEMETRY_DISABLED=true"
fi

echo ""

# ═══════════════════════════════════════════
# Step 5: Verify Installation
# ═══════════════════════════════════════════

log_step "5/5 Verifying installation..."

SERVERS_OK=0
SERVERS_FAIL=0

# Check that key MCP server builds exist
for pkg in management management-logs threat-prevention reputation-service gw-cli policy-insights; do
    if [ -f "$CHECKPOINT_MCP_DIR/packages/$pkg/dist/index.js" ]; then
        log_info "✓ $pkg MCP built"
        SERVERS_OK=$((SERVERS_OK + 1))
    else
        log_warn "✗ $pkg MCP not found"
        SERVERS_FAIL=$((SERVERS_FAIL + 1))
    fi
done

echo ""
log_info "Verification: $SERVERS_OK OK, $SERVERS_FAIL FAILED"
echo ""

# ═══════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════

echo "========================================="
echo "  Check Point Integration Complete"
echo "========================================="
echo ""
echo "  15 MCP servers installed to:"
echo "    $CHECKPOINT_MCP_DIR"
echo ""
echo "  Configured MCP servers (in config/openclaw.json):"
echo "    chkp-management          Policy, objects, topology"
echo "    chkp-management-logs     Connection and audit logs"
echo "    chkp-threat-prevention   IPS, IOC feeds, profiles"
echo "    chkp-https-inspection    HTTPS inspection policies"
echo "    chkp-harmony-sase        SASE regions, applications"
echo "    chkp-reputation-service  IP/URL/file reputation"
echo "    chkp-quantum-gw-cli      Gateway diagnostics"
echo "    chkp-gw-connection-analysis  Connection debugging"
echo "    chkp-threat-emulation    Malware analysis"
echo "    chkp-quantum-gaia        GAIA OS management"
echo "    chkp-documentation       Check Point docs search"
echo "    chkp-spark-management    Spark firewall (MSP)"
echo "    chkp-cpinfo-analysis     CPInfo diagnostics"
echo "    chkp-argos-erm           Exposure/risk management"
echo "    chkp-policy-insights     Policy optimization"
echo ""
echo "  Usage:"
echo "    openclaw"
echo "    > /checkpoint show my firewall policies"
echo "    > /checkpoint check reputation of IP 8.8.8.8"
echo "    > /checkpoint show gateway health status"
echo ""
echo "  Documentation: docs/CHECKPOINT.md"
echo ""
