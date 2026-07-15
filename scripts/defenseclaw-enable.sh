#!/usr/bin/env bash
# DefenseClaw Enable Script
# Enables DefenseClaw enterprise security for existing NetClaw installations
#
# Usage: ./scripts/defenseclaw-enable.sh
#
# Prerequisites:
#   - Docker installed and running
#   - Python 3.10+
#   - Go 1.25+ (for gateway)
#   - Node.js 20+ (for TypeScript plugin)

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
echo "  NetClaw - Enable DefenseClaw + OpenShell"
echo "  Enterprise Security Layer"
echo "========================================="
echo ""

# ═══════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════

log_step "1/6 Checking prerequisites..."

PREREQ_FAIL=0

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is required for DefenseClaw."
    log_error "Install Docker: https://docs.docker.com/get-docker/"
    PREREQ_FAIL=1
elif ! docker info &> /dev/null 2>&1; then
    log_error "Docker daemon is not running."
    log_error "Start Docker and try again."
    PREREQ_FAIL=1
else
    log_info "Docker found and running."
fi

# Check Python 3.10+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        log_info "Python $PYTHON_VERSION found."
    else
        log_error "Python 3.10+ required. Found: $PYTHON_VERSION"
        PREREQ_FAIL=1
    fi
else
    log_error "Python 3 is required."
    PREREQ_FAIL=1
fi

# Check Go 1.25+
if command -v go &> /dev/null; then
    GO_VERSION=$(go version | grep -oE 'go[0-9]+\.[0-9]+' | sed 's/go//')
    GO_MAJOR=$(echo "$GO_VERSION" | cut -d. -f1)
    GO_MINOR=$(echo "$GO_VERSION" | cut -d. -f2)
    if [ "$GO_MAJOR" -ge 1 ] && [ "$GO_MINOR" -ge 25 ]; then
        log_info "Go $GO_VERSION found."
    else
        log_warn "Go 1.25+ recommended. Found: $GO_VERSION"
        log_warn "DefenseClaw gateway may not build correctly."
    fi
else
    log_warn "Go not found. DefenseClaw gateway may not build."
fi

# Check Node.js 20+
if command -v node &> /dev/null; then
    NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VER" -ge 20 ]; then
        log_info "Node.js v$NODE_VER found."
    else
        log_warn "Node.js 20+ recommended. Found: v$NODE_VER"
        log_warn "DefenseClaw TypeScript plugin may not build correctly."
    fi
else
    log_warn "Node.js not found. DefenseClaw plugin may not build."
fi

if [ "$PREREQ_FAIL" -eq 1 ]; then
    log_error ""
    log_error "Prerequisites not met. Please install missing dependencies and try again."
    exit 1
fi

echo ""

# ═══════════════════════════════════════════
# Step 2: Backup Current Configuration
# ═══════════════════════════════════════════

log_step "2/6 Backing up configuration..."

if [ -f "$OPENCLAW_CONFIG" ]; then
    BACKUP_FILE="$OPENCLAW_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$OPENCLAW_CONFIG" "$BACKUP_FILE"
    log_info "Configuration backed up to: $BACKUP_FILE"
else
    log_warn "No existing openclaw.json found. Will create new one."
    mkdir -p "$(dirname "$OPENCLAW_CONFIG")"
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: Install DefenseClaw
# ═══════════════════════════════════════════

log_step "3/6 Installing DefenseClaw..."

# Check if already installed
if command -v defenseclaw &> /dev/null; then
    CURRENT_VERSION=$(defenseclaw --version 2>/dev/null || echo "unknown")
    log_info "DefenseClaw already installed: $CURRENT_VERSION"
    read -rp "Reinstall/upgrade? [y/N] " REINSTALL
    if [[ ! "$REINSTALL" =~ ^[Yy] ]]; then
        log_info "Skipping reinstall."
    else
        log_info "Reinstalling DefenseClaw..."
        curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash
    fi
else
    log_info "Installing DefenseClaw from Cisco AI Defense..."
    if curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash; then
        log_info "DefenseClaw installed successfully."
    else
        log_error "DefenseClaw installation failed."
        log_error "Try manual install: curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash"
        exit 1
    fi
fi

echo ""

# ═══════════════════════════════════════════
# Step 4: Initialize and Enable
# ═══════════════════════════════════════════

log_step "4/6 Initializing DefenseClaw..."

# Initialize guardrails
if command -v defenseclaw &> /dev/null; then
    log_info "Enabling guardrails (observe mode)..."
    defenseclaw init --enable-guardrail 2>/dev/null || log_warn "Guardrail init may have failed - check manually"
else
    # Try with explicit path
    if [ -x "$HOME/.local/bin/defenseclaw" ]; then
        log_info "Enabling guardrails (observe mode)..."
        "$HOME/.local/bin/defenseclaw" init --enable-guardrail 2>/dev/null || log_warn "Guardrail init may have failed"
    else
        log_warn "defenseclaw not in PATH. Add ~/.local/bin to PATH"
        log_warn "Then run: defenseclaw init --enable-guardrail"
    fi
fi

# Update openclaw.json
log_info "Updating openclaw.json..."
python3 -c "
import json
import os

config_path = os.path.expanduser('$OPENCLAW_CONFIG')

try:
    with open(config_path) as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
except json.JSONDecodeError:
    config = {}

# Set security mode to defenseclaw
if 'security' not in config:
    config['security'] = {}
config['security']['mode'] = 'defenseclaw'

# Remove old netshell config if present
config.pop('netshell', None)

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print('Configuration updated.')
"

# ═══════════════════════════════════════════
# Step 5: Install NVIDIA OpenShell
# ═══════════════════════════════════════════

log_step "5/6 Installing NVIDIA OpenShell sandbox..."

if command -v openshell &> /dev/null; then
    CURRENT_VERSION=$(openshell --version 2>/dev/null || echo "unknown")
    log_info "OpenShell already installed: $CURRENT_VERSION"
else
    log_info "Installing OpenShell from NVIDIA..."
    if curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh; then
        log_info "OpenShell installed successfully."
    else
        log_warn "OpenShell installation failed."
        log_warn "Try manual install: curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh"
    fi
fi

# Start OpenShell gateway if not running
if command -v openshell &> /dev/null; then
    log_info "Starting OpenShell gateway..."
    openshell gateway start 2>/dev/null || log_warn "OpenShell gateway may already be running"
fi

echo ""

# ═══════════════════════════════════════════
# Step 6: Register NetClaw MCP Servers
# ═══════════════════════════════════════════

log_step "6/6 Registering NetClaw MCP servers with DefenseClaw..."

DEFENSECLAW_CMD="defenseclaw"
if ! command -v defenseclaw &> /dev/null; then
    DEFENSECLAW_CMD="$HOME/.local/bin/defenseclaw"
fi

# Register MCP servers from openclaw.json
MCP_REGISTERED=0
MCP_SKIPPED=0
MCP_FAILED=0

# Extract and register MCP servers
python3 -c "
import json
import os
import subprocess
import sys

config_path = os.path.expanduser('$OPENCLAW_CONFIG')
netclaw_dir = '$NETCLAW_DIR'
defenseclaw = '$DEFENSECLAW_CMD'

try:
    with open(config_path) as f:
        config = json.load(f)
except:
    print('Could not read openclaw.json')
    sys.exit(1)

mcp_servers = config.get('mcpServers', {})
if not mcp_servers:
    print('No MCP servers found in openclaw.json')
    sys.exit(0)

registered = 0
skipped = 0
failed = 0

for name, server_config in sorted(mcp_servers.items()):
    # Skip remote MCP servers (mcp:// URLs)
    if 'url' in server_config and server_config['url'].startswith('mcp://'):
        print(f'  SKIP: {name} (remote MCP)')
        skipped += 1
        continue

    # Skip URL-only servers without command
    if 'url' in server_config and 'command' not in server_config:
        if not server_config['url'].startswith('http'):
            print(f'  SKIP: {name} (no command)')
            skipped += 1
            continue

    # Build command
    cmd = [defenseclaw, 'mcp', 'set', name, '--skip-scan']

    if 'command' in server_config:
        cmd.extend(['--command', server_config['command']])

        if 'args' in server_config:
            args = server_config['args']
            if isinstance(args, list):
                cmd.extend(['--args', json.dumps(args)])
            else:
                cmd.extend(['--args', str(args)])

    if 'url' in server_config:
        url = server_config['url']
        # Expand env vars if present
        if '\${' in url:
            print(f'  SKIP: {name} (env var URL)')
            skipped += 1
            continue
        cmd.extend(['--url', url])

    # Try to register
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f'  OK: {name}')
            registered += 1
        else:
            print(f'  FAIL: {name} - {result.stderr.strip()[:50]}')
            failed += 1
    except Exception as e:
        print(f'  ERROR: {name} - {e}')
        failed += 1

print(f'')
print(f'MCP Registration: {registered} registered, {skipped} skipped, {failed} failed')
" 2>&1

echo ""
echo "========================================="
echo "  DefenseClaw + OpenShell Enabled!"
echo "========================================="
echo ""
echo "  ┌─────────────────────────────────────────────────────────────┐"
echo "  │  ENTERPRISE SECURITY STACK                                   │"
echo "  ├─────────────────────────────────────────────────────────────┤"
echo "  │  OpenShell:    ~/.local/bin/openshell                       │"
echo "  │  DefenseClaw:  ~/.defenseclaw/                              │"
echo "  │  Audit DB:     ~/.defenseclaw/audit.db                      │"
echo "  └─────────────────────────────────────────────────────────────┘"
echo ""
echo "  ════════════════════════════════════════════════════════════"
echo "  HOW TO RUN NETCLAW SECURELY"
echo "  ════════════════════════════════════════════════════════════"
echo ""
echo "  Option 1: Full Sandbox Mode (Recommended for Production)"
echo "  ---------------------------------------------------------"
echo "    # Start OpenShell gateway (Docker-based)"
echo "    openshell gateway start"
echo ""
echo "    # Create a NetClaw sandbox"
echo "    openshell sandbox create netclaw"
echo ""
echo "    # Run NetClaw inside the sandbox"
echo "    openshell run netclaw -- claw"
echo ""
echo "  Option 2: DefenseClaw Only (Guardrails without Container)"
echo "  ----------------------------------------------------------"
echo "    # Start DefenseClaw gateway"
echo "    defenseclaw-gateway &"
echo ""
echo "    # Enable blocking mode"
echo "    defenseclaw setup guardrail --mode action"
echo ""
echo "    # Run OpenClaw normally (DefenseClaw intercepts)"
echo "    openclaw gateway &"
echo "    claw"
echo ""
echo "  ════════════════════════════════════════════════════════════"
echo "  KEY COMMANDS"
echo "  ════════════════════════════════════════════════════════════"
echo ""
echo "  OpenShell:"
echo "    openshell --version                # Check version"
echo "    openshell gateway status           # Gateway status"
echo "    openshell sandbox list             # List sandboxes"
echo "    openshell sandbox create <name>    # Create sandbox"
echo "    openshell run <name> -- <cmd>      # Run in sandbox"
echo ""
echo "  DefenseClaw:"
echo "    defenseclaw --version              # Check version"
echo "    defenseclaw mcp list               # List registered MCPs"
echo "    defenseclaw skill scan <name>      # Scan a skill"
echo "    defenseclaw mcp scan <name>        # Scan an MCP"
echo "    defenseclaw tool block <tool>      # Block a tool"
echo "    defenseclaw alerts                 # View security alerts"
echo "    defenseclaw setup guardrail --mode action  # Enable blocking"
echo ""
echo "  Documentation:"
echo "    Full guide:      docs/DEFENSECLAW.md"
echo "    Security SOUL:   docs/SOUL-DEFENSE.md"
echo ""
echo "  To disable: ./scripts/defenseclaw-disable.sh"
echo ""
