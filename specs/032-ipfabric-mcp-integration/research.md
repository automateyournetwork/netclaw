# Phase 0 Research: IP Fabric MCP Integration

**Feature**: 032-ipfabric-mcp-integration
**Date**: 2026-06-19
**Status**: Complete

## 1. IP Fabric MCP Environment Variables

The IP Fabric MCP Server requires authentication via API token. Based on the official documentation at https://docs.ipfabric.io/latest/IP_Fabric_Settings/integration/mcp/:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `IPFABRIC_HOST` | IP Fabric appliance URL (base URL without /mcp) | `https://ipfabric.example.com` |
| `IPFABRIC_API_TOKEN` | API token with appropriate RBAC permissions | `2fe04e6c7eb787f5547d72abbd7b4f09` |

### Derived Variables (for mcp-remote)

| Variable | Description | Value |
|----------|-------------|-------|
| `IPFABRIC_AUTH_HEADER` | Authorization header value | `Bearer ${IPFABRIC_API_TOKEN}` |
| `IPFABRIC_MCP_URL` | Full MCP endpoint URL | `${IPFABRIC_HOST}/mcp` |

### Token Generation

API tokens are generated in IP Fabric UI:
1. Navigate to **Settings** → **API Tokens**
2. Create a new token with appropriate permissions
3. Copy the token immediately (only shown once)

RBAC permissions on the token determine which data the MCP server can access.

## 2. MCP Tool Inventory

The IP Fabric MCP Server exposes the following tools:

### Network Health Assessment

| Tool | Description | Parameters |
|------|-------------|------------|
| `ipf_network_health_assess` | Comprehensive network health assessment | `snapshotId` (optional, defaults to `$last`) |

Returns: Snapshot freshness, intent verification results, inventory issues, routing stability, path check results.

### Path Lookup Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `ipf_pathlookup_unicast` | Trace unicast path between two IPs | `src`, `dst`, `snapshotId`, `groupBy`, `protocol`, `vrf` |
| `ipf_pathlookup_host-to-gateway` | Trace host to default gateway | `src`, `snapshotId`, `groupBy` |
| `ipf_pathlookup_multicast` | Trace multicast distribution path | `src`, `group`, `snapshotId`, `groupBy` |

**groupBy options**: `siteName`, `routingDomain`, `stpDomain`

### Path Diagram Tools (PNG)

| Tool | Description | Parameters |
|------|-------------|------------|
| `ipf_png_pathlookup_unicast` | Unicast path as PNG diagram | Same as `ipf_pathlookup_unicast` |
| `ipf_png_pathlookup_host-to-gateway` | Host-to-gateway path as PNG diagram | Same as `ipf_pathlookup_host-to-gateway` |
| `ipf_png_pathlookup_multicast` | Multicast path as PNG diagram | Same as `ipf_pathlookup_multicast` |

Returns: Base64-encoded PNG image data.

### API Discovery Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `ipf_api_endpoint_search` | Search for API endpoints by natural language | `query` |
| `ipf_api_endpoint_details` | Get endpoint details including parameters | `endpoint` |
| `api_invoke` | Execute arbitrary API call | `endpoint`, `method`, `params` |

## 3. mcp-remote Proxy Configuration

IP Fabric MCP is a remote HTTP server, requiring the `mcp-remote` proxy:

### NPX Invocation Pattern

```bash
npx -y mcp-remote https://<host>/mcp --header "Authorization:Bearer <token>"
```

### OpenClaw Configuration

```json
{
  "ipfabric-mcp": {
    "command": "npx",
    "args": [
      "-y",
      "mcp-remote",
      "${IPFABRIC_HOST}/mcp",
      "--header",
      "Authorization:${IPFABRIC_AUTH_HEADER}"
    ],
    "env": {
      "IPFABRIC_AUTH_HEADER": "Bearer ${IPFABRIC_API_TOKEN}"
    }
  }
}
```

### Key Differences from Check Point

| Aspect | Check Point | IP Fabric |
|--------|-------------|-----------|
| MCP Type | Local NPM packages | Remote HTTP server |
| Count | 15 MCP servers | 1 MCP server |
| Connection | Direct npx execution | mcp-remote proxy |
| Transport | stdio | HTTP/SSE |

## 4. Query Routing Patterns

Natural language queries map to IP Fabric tools:

### Health Assessment Patterns

| User Query Pattern | Tool | Notes |
|-------------------|------|-------|
| "check network health" | `ipf_network_health_assess` | Default snapshot |
| "show critical issues" | `ipf_network_health_assess` | Filter results |
| "what's the BGP status" | `ipf_network_health_assess` | Extract routing section |
| "are there routing problems" | `ipf_network_health_assess` | Filter to routing issues |
| "intent violations" | `ipf_network_health_assess` | Filter to intent results |

### Path Lookup Patterns

| User Query Pattern | Tool | Notes |
|-------------------|------|-------|
| "show path from X to Y" | `ipf_pathlookup_unicast` | Basic path trace |
| "trace route from X to Y" | `ipf_pathlookup_unicast` | Alias for path |
| "path from X to Y with diagram" | `ipf_png_pathlookup_unicast` | Include PNG |
| "show path to gateway" | `ipf_pathlookup_host-to-gateway` | Host-to-GW variant |
| "multicast path for group X" | `ipf_pathlookup_multicast` | Multicast variant |
| "path in VRF X" | Any pathlookup | Add vrf parameter |

### Inventory Patterns

| User Query Pattern | Tool | Notes |
|-------------------|------|-------|
| "show all Cisco devices" | `api_invoke` | Device inventory endpoint |
| "devices in site X" | `api_invoke` | Filtered inventory |
| "find devices with uptime < 1 day" | `api_invoke` | Uptime filter |

### API Discovery Patterns

| User Query Pattern | Tool | Notes |
|-------------------|------|-------|
| "find endpoints for X" | `ipf_api_endpoint_search` | Discovery |
| "how do I query X" | `ipf_api_endpoint_details` | After discovery |

## 5. Existing Install.sh Pattern

Review of `scripts/install.sh` shows the integration pattern:

### Current Structure

```bash
# Each integration follows this pattern:
echo "Enable [Integration] integration? [y/N]"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    # 1. Prompt for credentials
    # 2. Store in .env
    # 3. Clone/install MCP server (if local)
    # 4. Add to openclaw.json
fi
```

### IP Fabric Integration Point

Add after Check Point section:

```bash
# IP Fabric integration
echo -e "\n${YELLOW}Enable IP Fabric integration?${NC}"
echo "IP Fabric provides network assurance with topology, path analysis, and intent verification."
echo "Requires: IP Fabric appliance with MCP Server enabled, API token"
read -p "Enable IP Fabric? [y/N]: " ENABLE_IPFABRIC
if [[ "$ENABLE_IPFABRIC" =~ ^[Yy]$ ]]; then
    read -p "IP Fabric host URL (e.g., https://ipfabric.example.com): " IPFABRIC_HOST
    read -sp "IP Fabric API token: " IPFABRIC_API_TOKEN
    echo ""

    # Add to .env
    echo "IPFABRIC_HOST=$IPFABRIC_HOST" >> ~/.openclaw/.env
    echo "IPFABRIC_API_TOKEN=$IPFABRIC_API_TOKEN" >> ~/.openclaw/.env

    # Add MCP config (handled separately)
    echo "IP Fabric integration enabled!"
fi
```

## 6. PNG Diagram Handling

### Current NetClaw Capabilities

NetClaw already supports image attachments via messaging channels:
- **Discord**: File attachment support ✅
- **Slack**: File upload API ✅
- **Teams**: Adaptive card with image ✅
- **Webex**: File attachment support ✅

### Diagram Workflow

1. IP Fabric MCP returns base64-encoded PNG
2. Claude processes the image data
3. For messaging channels: attach as file
4. For CLI: save to workspace directory and provide path

### Workspace Storage

```text
~/.openclaw/workspace/diagrams/
├── ipfabric/
│   ├── path-2026-06-19-001.png
│   └── path-2026-06-19-002.png
```

## 7. Snapshot Handling

### Default Behavior

- `$last` refers to the most recent completed snapshot
- All queries default to `$last` when snapshotId not specified

### Snapshot Selection

Users can specify snapshots by:
- **UUID**: `snapshotId: "abc123-def456-..."`
- **Name**: The AI can list available snapshots and let user select

### Snapshot Listing

Use `api_invoke` to list snapshots:
```
GET /snapshots
```

Returns array of snapshots with:
- `id` (UUID)
- `name`
- `state` (running, completed, failed)
- `start`, `end` timestamps

## Research Findings Summary

1. **Single Remote MCP**: Unlike Check Point (15 local MCPs), IP Fabric is 1 remote MCP server
2. **mcp-remote Required**: Must use npx mcp-remote proxy for HTTP connection
3. **10 Core Tools**: Health, 3 path lookups, 3 PNG diagrams, 3 API tools
4. **Snapshot Defaults**: All queries default to `$last` snapshot
5. **PNG Support Ready**: NetClaw already handles image attachments
6. **Environment Variables**: Only 2 required (IPFABRIC_HOST, IPFABRIC_API_TOKEN)
