#!/usr/bin/env bash
# DefenseClaw Disable Script
# Disables DefenseClaw and switches NetClaw to hobby mode
#
# Usage: ./scripts/defenseclaw-disable.sh
#
# Note: This does NOT uninstall DefenseClaw, just disables it for NetClaw.
# DefenseClaw remains installed at ~/.defenseclaw for future re-enablement.

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
OPENCLAW_CONFIG="$HOME/.openclaw/config/openclaw.json"

echo "========================================="
echo "  NetClaw - Disable DefenseClaw"
echo "  Switch to Hobby Mode"
echo "========================================="
echo ""

echo -e "${YELLOW}Warning:${NC} Disabling DefenseClaw removes enterprise security features:"
echo "  - No sandbox isolation"
echo "  - No component scanning before execution"
echo "  - No runtime guardrails"
echo "  - No audit logging"
echo ""
read -rp "Are you sure you want to disable DefenseClaw? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
    log_info "Cancelled. DefenseClaw remains enabled."
    exit 0
fi

echo ""

# ═══════════════════════════════════════════
# Step 1: Stop DefenseClaw Gateway
# ═══════════════════════════════════════════

log_step "1/2 Stopping DefenseClaw gateway..."

# Kill gateway process if running
if pgrep -f "defenseclaw-gateway" > /dev/null 2>&1; then
    log_info "Stopping defenseclaw-gateway process..."
    pkill -f "defenseclaw-gateway" 2>/dev/null || true
    sleep 1
    if pgrep -f "defenseclaw-gateway" > /dev/null 2>&1; then
        log_warn "Could not stop gateway. Kill manually: pkill -f defenseclaw-gateway"
    else
        log_info "Gateway stopped."
    fi
else
    log_info "No gateway process running."
fi

echo ""

# ═══════════════════════════════════════════
# Step 2: Update Configuration
# ═══════════════════════════════════════════

log_step "2/2 Updating configuration..."

if [ -f "$OPENCLAW_CONFIG" ]; then
    python3 -c "
import json
import os

config_path = os.path.expanduser('$OPENCLAW_CONFIG')

try:
    with open(config_path) as f:
        config = json.load(f)
except:
    config = {}

# Set security mode to hobby
if 'security' not in config:
    config['security'] = {}
config['security']['mode'] = 'hobby'

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print('Configuration updated.')
"
    log_info "openclaw.json updated: security.mode = 'hobby'"
else
    log_warn "No openclaw.json found. Creating with hobby mode."
    mkdir -p "$(dirname "$OPENCLAW_CONFIG")"
    echo '{"security": {"mode": "hobby"}}' > "$OPENCLAW_CONFIG"
fi

echo ""
echo "========================================="
echo "  DefenseClaw Disabled"
echo "========================================="
echo ""
echo "  NetClaw is now in hobby mode (no security layer)."
echo ""
echo "  Note: DefenseClaw is NOT uninstalled."
echo "  Re-enable anytime: ./scripts/defenseclaw-enable.sh"
echo ""
echo "  To fully uninstall DefenseClaw:"
echo "    rm -rf ~/.defenseclaw"
echo "    rm ~/.local/bin/defenseclaw*"
echo ""
