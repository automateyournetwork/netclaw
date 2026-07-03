#!/usr/bin/env bash
# memory-enable.sh - Enable Memory MCP Server for existing NetClaw installations
#
# Usage: ./scripts/memory-enable.sh
#
# This script:
# 1. Installs the memory-mcp package via uvx
# 2. Creates the data directory (~/.openclaw/memory/)
# 3. Updates openclaw.json with the MCP server configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OPENCLAW_DIR="${HOME}/.openclaw"
MEMORY_DIR="${OPENCLAW_DIR}/memory"
CONFIG_FILE="${OPENCLAW_DIR}/config/openclaw.json"

echo "=== Memory MCP Server Enable Script ==="
echo ""

# Check for uv/uvx
if ! command -v uvx &> /dev/null; then
    echo "ERROR: uvx not found. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create memory data directory
echo "Creating memory data directory: ${MEMORY_DIR}"
mkdir -p "${MEMORY_DIR}"

# Install the memory-mcp package
echo "Installing netclaw-memory-mcp via uvx..."
cd "${REPO_ROOT}/mcp-servers/memory-mcp"
uv pip install -e . --quiet 2>/dev/null || {
    echo "Installing dependencies (this may take a moment for torch/chromadb)..."
    uv pip install -e .
}

# Check if openclaw.json exists
if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "WARNING: ${CONFIG_FILE} not found."
    echo "Please add the following to your MCP configuration manually:"
    echo ""
    cat << 'EOF'
{
  "mcpServers": {
    "memory": {
      "command": "uvx",
      "args": ["--from", "netclaw-memory-mcp", "memory-mcp-server"],
      "env": {
        "MEMORY_DATA_DIR": "${HOME}/.openclaw/memory"
      }
    }
  }
}
EOF
    echo ""
else
    echo "Found openclaw.json at ${CONFIG_FILE}"
    echo "Please add the memory MCP server configuration if not already present."
fi

echo ""
echo "=== Memory MCP Server Enabled ==="
echo ""
echo "Data directory: ${MEMORY_DIR}"
echo "To test: uvx --from netclaw-memory-mcp memory-mcp-server --help"
echo ""
echo "Note: First run will download the embedding model (~80MB)."
