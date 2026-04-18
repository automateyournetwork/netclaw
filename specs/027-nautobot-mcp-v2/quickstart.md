# Quickstart: Enhanced Nautobot MCP Server v2

**Feature**: 027-nautobot-mcp-v2
**Date**: 2026-04-09

## Prerequisites

1. A running Nautobot 3.1.0 instance with GraphQL and REST API enabled
2. A valid Nautobot API token with read+write permissions
3. Python 3.10+
4. Network connectivity from the MCP server host to the Nautobot instance

## Setup

### 1. Install dependencies

```bash
cd mcp-servers/nautobot-mcp-v2/
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
export NAUTOBOT_URL="https://192.168.3.253"
export NAUTOBOT_TOKEN="your-nautobot-api-token"

# Optional
export NAUTOBOT_VERIFY_SSL="false"     # Set to false for self-signed certs
export NAUTOBOT_TIMEOUT="30"           # Query timeout in seconds
export ITSM_ENABLED="false"           # Enable ITSM gating for writes
export ITSM_LAB_MODE="true"           # Bypass ITSM in lab environments
```

### 3. Register in openclaw.json

Replace the existing `nautobot-mcp` entry in `config/openclaw.json`:

```json
{
  "nautobot-mcp": {
    "command": "python3",
    "args": ["-u", "mcp-servers/nautobot-mcp-v2/server.py"],
    "env": {
      "NAUTOBOT_URL": "${NAUTOBOT_URL}",
      "NAUTOBOT_TOKEN": "${NAUTOBOT_TOKEN}",
      "NAUTOBOT_VERIFY_SSL": "${NAUTOBOT_VERIFY_SSL:-false}",
      "NAUTOBOT_TIMEOUT": "${NAUTOBOT_TIMEOUT:-30}",
      "ITSM_ENABLED": "${ITSM_ENABLED:-false}",
      "ITSM_LAB_MODE": "${ITSM_LAB_MODE:-true}"
    }
  }
}
```

### 4. Run the server (standalone test)

```bash
python3 -u mcp-servers/nautobot-mcp-v2/server.py
```

The server communicates via stdio. It will wait for JSON-RPC messages on stdin.

## Usage Examples

Once registered with an MCP client (OpenClaw TUI, Slack, Discord):

**Read queries (GraphQL)**:
- "Show me all devices in Nautobot"
- "What interfaces does HomeSwitch01 have?"
- "Show VLANs at location House"
- "What IP addresses are assigned to HomeSwitch02?"
- "Show me all cables"
- "What prefixes are in Nautobot?"

**Raw GraphQL**:
- "Run this GraphQL query: { bgp_routing_instances { device { name } router_id } }"

**Write operations (REST API)**:
- "Create VLAN 200 named Guest at location House"
- "Add IP address 10.0.1.50/24 to HomeSwitch01 GigabitEthernet1/0/48"
- "Update the description on HomeSwitch01 GigabitEthernet1/0/4 to 'Server port'"

**Reconciliation**:
- "Reconcile HomeSwitch01 interfaces against Nautobot"
- "Compare live state of HomeSwitch02 with the source of truth"

## Verification

1. Test connection: the `nautobot_test_connection` tool should return connected=true
2. Query devices: `nautobot_get_devices()` should return HomeSwitch01, HomeSwitch02, pfSense-FW01
3. Query interfaces: `nautobot_get_interfaces(device="HomeSwitch01")` should return all switch interfaces
4. Query VLANs: `nautobot_get_vlans()` should return 34 VLANs
5. Check stderr output for connection and query logs

## Docker Usage

In the Docker container, the server runs via the openclaw.json registration. The environment variables are passed from the host `.env` file through `docker-compose.yml`.

```bash
# Rebuild after adding v2 server
docker compose up -d --build

# Test via TUI
docker compose exec -it netclaw openclaw tui
# Then ask: "Show me all devices in Nautobot"
```
