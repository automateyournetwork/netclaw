#!/usr/bin/env bash
# Enable Forward MCP integration for existing NetClaw installations.

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
FORWARD_MCP_DIR="$MCP_DIR/forward-mcp"
FORWARD_MCP_BIN="$FORWARD_MCP_DIR/forward-mcp"
FORWARD_MCP_REPO="${FORWARD_MCP_REPO:-https://github.com/forwardnetworks/forward-mcp.git}"
FORWARD_MCP_REF="${FORWARD_MCP_REF:-netclaw}"
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_ENV="$OPENCLAW_DIR/.env"
OPENCLAW_CONFIG="$OPENCLAW_DIR/openclaw.json"
FORWARD_STATE_DIR="$OPENCLAW_DIR/forward"
FORWARD_LOCK_DIR="$FORWARD_STATE_DIR/locks"
FORWARD_BLOOM_INDEX_PATH="$FORWARD_STATE_DIR/bloom-indexes"
FORWARD_CACHE_PATH="$FORWARD_STATE_DIR/cache"

set_env_var() {
    local key="$1" val="$2"
    local tmp
    [ -z "$val" ] && return
    tmp="$(mktemp)"
    grep -v "^${key}=" "$OPENCLAW_ENV" > "$tmp" 2>/dev/null || true
    printf '%s=%s\n' "$key" "$val" >> "$tmp"
    mv "$tmp" "$OPENCLAW_ENV"
}

set_env_placeholder() {
    local key="$1" val="$2"
    if ! grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        set_env_var "$key" "$val"
    fi
}

go_major() {
    go version | awk '{print $3}' | sed 's/^go//' | cut -d. -f1
}

go_minor() {
    go version | awk '{print $3}' | sed 's/^go//' | cut -d. -f2
}

checkout_forward_ref() {
    local dir="$1" repo="$2" ref="$3"
    if [ -d "$dir/.git" ]; then
        log_info "Updating existing checkout at $dir"
        git -C "$dir" remote set-url origin "$repo"
        git -C "$dir" fetch origin --tags
    else
        log_info "Cloning forward-mcp into $dir"
        git clone "$repo" "$dir"
    fi

    if git -C "$dir" rev-parse --verify --quiet "origin/$ref" >/dev/null; then
        git -C "$dir" checkout -B "$ref" "origin/$ref"
    else
        git -C "$dir" checkout "$ref"
    fi
}

echo "========================================="
echo "  Forward MCP Integration"
echo "  for NetClaw"
echo "========================================="
echo ""
echo "  Source: https://github.com/forwardnetworks/forward-mcp"
echo "  Ref: $FORWARD_MCP_REF"
echo ""

log_step "1/5 Checking prerequisites..."

missing=0
for bin in git go; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        log_error "$bin is required."
        missing=1
    fi
done

if command -v go >/dev/null 2>&1; then
    major="$(go_major)"
    minor="$(go_minor)"
    if [ "$major" -lt 1 ] || { [ "$major" -eq 1 ] && [ "$minor" -lt 25 ]; }; then
        log_error "Go 1.25 or later is required. Found: $(go version)"
        missing=1
    else
        log_info "Go version: $(go version)"
    fi
fi

if [ "$(go env CGO_ENABLED)" = "0" ]; then
    log_error "CGO must be enabled for forward-mcp."
    missing=1
fi

if [ "$missing" -eq 1 ]; then
    log_error "Install missing prerequisites and re-run."
    exit 1
fi

log_step "2/5 Installing forward-mcp..."
mkdir -p "$MCP_DIR" "$OPENCLAW_DIR" "$FORWARD_LOCK_DIR" "$FORWARD_BLOOM_INDEX_PATH" "$FORWARD_CACHE_PATH"
[ -f "$OPENCLAW_ENV" ] || touch "$OPENCLAW_ENV"

log_info "Using forward-mcp repo: $FORWARD_MCP_REPO"
log_info "Using forward-mcp ref: $FORWARD_MCP_REF"
checkout_forward_ref "$FORWARD_MCP_DIR" "$FORWARD_MCP_REPO" "$FORWARD_MCP_REF"

log_info "Building forward-mcp binary"
CGO_ENABLED=1 go -C "$FORWARD_MCP_DIR" build -o "$FORWARD_MCP_BIN" ./cmd/server

log_step "3/5 Configuring environment..."

set_env_var "FORWARD_LOCK_DIR" "$FORWARD_LOCK_DIR"
set_env_var "FORWARD_BLOOM_ENABLED" "${FORWARD_BLOOM_ENABLED:-true}"
set_env_var "FORWARD_BLOOM_INDEX_PATH" "$FORWARD_BLOOM_INDEX_PATH"
set_env_var "FORWARD_SEMANTIC_CACHE_ENABLED" "${FORWARD_SEMANTIC_CACHE_ENABLED:-true}"
set_env_var "FORWARD_SEMANTIC_CACHE_DISK_PATH" "$FORWARD_CACHE_PATH"

read -r -p "Configure Forward credentials now? [Y/n] " config_now
if [[ ! "$config_now" =~ ^[Nn]$ ]]; then
    read -r -p "Forward API base URL (e.g., https://fwd.app): " forward_url
    if [ -n "$forward_url" ]; then
        set_env_var "FORWARD_API_BASE_URL" "${forward_url%/}"
    fi

    read -r -p "Forward API key or username: " forward_key
    if [ -n "$forward_key" ]; then
        set_env_var "FORWARD_API_KEY" "$forward_key"
    fi

    read -r -sp "Forward API secret or password: " forward_secret
    echo ""
    if [ -n "$forward_secret" ]; then
        set_env_var "FORWARD_API_SECRET" "$forward_secret"
    fi

    read -r -p "Default Forward network ID (optional): " forward_network
    set_env_var "FORWARD_DEFAULT_NETWORK_ID" "$forward_network"

    read -r -p "Default Forward snapshot ID (optional): " forward_snapshot
    set_env_var "FORWARD_DEFAULT_SNAPSHOT_ID" "$forward_snapshot"

    read -r -p "Forward collection/admin network ID (optional): " forward_collection_network
    set_env_var "FORWARD_COLLECTION_NETWORK_ID" "$forward_collection_network"

    read -r -p "Forward instance ID for local cache partitioning (optional): " forward_instance
    set_env_var "FORWARD_INSTANCE_ID" "$forward_instance"

    read -r -p "Custom CA certificate path (optional): " forward_ca
    set_env_var "FORWARD_CA_CERT_PATH" "$forward_ca"
else
    log_info "Skipping credential prompts. Set FORWARD_API_* in $OPENCLAW_ENV later."
    set_env_placeholder "FORWARD_API_BASE_URL" "https://fwd.example.com"
    set_env_placeholder "FORWARD_API_KEY" "your-api-key-or-username"
    set_env_placeholder "FORWARD_API_SECRET" "your-api-secret-or-password"
    set_env_placeholder "FORWARD_INSTANCE_ID" "default"
fi

log_step "4/5 Checking NetClaw config..."
if [ -f "$OPENCLAW_CONFIG" ]; then
    if grep -q '"forward-mcp"' "$OPENCLAW_CONFIG"; then
        log_info "forward-mcp is present in $OPENCLAW_CONFIG"
    else
        log_warn "forward-mcp is not present in $OPENCLAW_CONFIG"
        log_info "Copy config/openclaw.json or add the forward-mcp block from this repo."
    fi
else
    log_warn "$OPENCLAW_CONFIG not found. Run ./scripts/install.sh first."
fi

log_step "5/5 Running local smoke test..."
if python3 "$NETCLAW_DIR/scripts/mcp-call.py" \
    "FORWARD_LOCK_DIR=$FORWARD_LOCK_DIR FORWARD_BLOOM_ENABLED=false FORWARD_SEMANTIC_CACHE_ENABLED=false $FORWARD_MCP_BIN" \
    get_default_settings '{}' >/dev/null; then
    log_info "forward-mcp responded to get_default_settings"
else
    log_warn "Smoke test failed. Check $FORWARD_MCP_BIN and Forward environment variables."
fi

echo ""
echo "Forward MCP integration is installed."
echo ""
echo "Next steps:"
echo "  1. Restart the OpenClaw gateway."
echo "  2. Verify MCP registration with your OpenClaw MCP list command."
echo "  3. Try: /forward list networks"
echo ""
