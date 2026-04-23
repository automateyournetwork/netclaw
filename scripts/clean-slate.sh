#!/usr/bin/env bash
# NetClaw Clean Slate — remove all OpenClaw state for a fresh bare-metal install
#
# Usage:
#   ./scripts/clean-slate.sh          # interactive — asks before deleting
#   ./scripts/clean-slate.sh --force  # no prompts — nukes everything
#
# What it removes:
#   ~/.openclaw/              — all OpenClaw state (sessions, config, workspace, logs, memory)
#   .venv/                    — Python virtual environment (bare-metal install)
#   Docker containers         — stops netclaw-convergence and orphan MCP containers
#   Docker volumes            — removes openclaw-data persistent volume
#
# What it does NOT remove:
#   .env                      — your credentials (you'll need these for reinstall)
#   workspace-override/       — your private workspace files
#   mcp-servers/              — MCP server source code
#   The project directory itself

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_DIR="$HOME/.openclaw"
VENV_DIR="$NETCLAW_DIR/.venv"
FORCE=false

if [ "${1:-}" = "--force" ]; then
    FORCE=true
fi

confirm() {
    if $FORCE; then return 0; fi
    read -rp "$1 [y/N] " answer
    [[ "$answer" =~ ^[Yy] ]]
}

echo ""
echo -e "${RED}=========================================${NC}"
echo -e "${RED}  NetClaw Clean Slate${NC}"
echo -e "${RED}=========================================${NC}"
echo ""
echo "  This will remove:"
echo "    ~/.openclaw/          (sessions, config, workspace, logs)"
[ -d "$VENV_DIR" ] && echo "    .venv/                (Python virtual environment)"
echo "    Docker containers     (netclaw-convergence + orphans)"
echo "    Docker volume         (openclaw-data)"
echo ""
echo "  This will NOT remove:"
echo "    .env                  (your credentials)"
echo "    workspace-override/   (your private files)"
echo ""

if ! confirm "Proceed with clean slate?"; then
    echo "Aborted."
    exit 0
fi

echo ""

# Stop Docker containers
if command -v docker &> /dev/null; then
    echo -e "${YELLOW}[1/5]${NC} Stopping Docker containers..."
    
    # Stop netclaw-convergence
    docker stop netclaw-convergence 2>/dev/null && echo "  Stopped netclaw-convergence" || true
    docker rm netclaw-convergence 2>/dev/null && echo "  Removed netclaw-convergence" || true
    
    # Stop any orphan github-mcp containers
    for cid in $(docker ps -aq --filter "ancestor=ghcr.io/github/github-mcp-server" 2>/dev/null); do
        docker stop "$cid" 2>/dev/null && docker rm "$cid" 2>/dev/null && echo "  Removed orphan github-mcp ($cid)" || true
    done
    
    # Remove docker compose project containers
    if [ -f "$NETCLAW_DIR/docker-compose.yml" ]; then
        cd "$NETCLAW_DIR"
        docker compose down --remove-orphans 2>/dev/null && echo "  Docker compose down" || true
    fi
else
    echo -e "${YELLOW}[1/5]${NC} Docker not found — skipping container cleanup"
fi

# Remove Docker volume
if command -v docker &> /dev/null; then
    echo -e "${YELLOW}[2/5]${NC} Removing Docker volumes..."
    docker volume rm openclaw-data 2>/dev/null && echo "  Removed openclaw-data volume" || echo "  No openclaw-data volume found"
    docker volume rm netclaw_openclaw-data 2>/dev/null && echo "  Removed netclaw_openclaw-data volume" || true
else
    echo -e "${YELLOW}[2/5]${NC} Docker not found — skipping volume cleanup"
fi

# Remove OpenClaw state directory
echo -e "${YELLOW}[3/5]${NC} Removing OpenClaw state..."
if [ -d "$OPENCLAW_DIR" ]; then
    rm -rf "$OPENCLAW_DIR"
    echo "  Removed $OPENCLAW_DIR"
else
    echo "  $OPENCLAW_DIR not found — already clean"
fi

# Remove Python venv
echo -e "${YELLOW}[4/5]${NC} Removing Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    echo "  Removed $VENV_DIR"
else
    echo "  $VENV_DIR not found — already clean"
fi

# Kill any running openclaw processes
echo -e "${YELLOW}[5/5]${NC} Killing OpenClaw processes..."
pkill -f "openclaw gateway" 2>/dev/null && echo "  Killed openclaw gateway" || echo "  No gateway process found"
pkill -f "openclaw tui" 2>/dev/null && echo "  Killed openclaw tui" || true

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Clean slate complete${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "  To reinstall:"
echo "    ./scripts/install-bare-metal.sh"
echo ""
echo "  To reinstall Docker:"
echo "    docker compose up -d --build"
echo ""
