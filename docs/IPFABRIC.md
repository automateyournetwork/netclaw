# IP Fabric MCP Integration Guide

> Production-grade integration of IP Fabric's network assurance platform into NetClaw via the official IP Fabric MCP Server.

**Developed in collaboration with Daren Fulwell (Field CTO, IP Fabric) and John Capobianco (Creator, NetClaw)** — representing nearly a decade of professional partnership.

---

## Overview

IP Fabric is a network assurance platform that automatically discovers, models, and analyzes network infrastructure. The IP Fabric MCP Server is built directly into IP Fabric appliances (v6.0+), exposing network data through standardized MCP tools for health assessment, path analysis, visual diagrams, and custom API queries.

### Key Capabilities

| Capability | Description | Tools |
|------------|-------------|-------|
| Network Health | Snapshot freshness, intent verification, routing stability | `ipf_network_health_assess` |
| Path Analysis | Trace connectivity between endpoints | `ipf_pathlookup_unicast`, `ipf_pathlookup_host-to-gateway`, `ipf_pathlookup_multicast` |
| Visual Diagrams | PNG path visualizations | `ipf_png_pathlookup_*` |
| API Discovery | Find and invoke arbitrary IP Fabric APIs | `ipf_api_endpoint_search`, `ipf_api_endpoint_details`, `api_invoke` |

---

## Prerequisites

1. **IP Fabric Appliance** (v6.0 or later) with MCP Server enabled
2. **API Token** with appropriate RBAC permissions
3. **Network Connectivity** from NetClaw host to IP Fabric over HTTPS (port 443)
4. **Node.js 18+** (for npx mcp-remote proxy)

---

## Installation

### New NetClaw Users

During the NetClaw installation process, you'll be prompted to enable IP Fabric:

```bash
./scripts/install.sh
# ...
Enable IP Fabric Integration? [y/N] y
Enter IP Fabric Host URL (e.g., https://ipfabric.example.com): https://your-ipfabric.com
Enter IP Fabric API Token: <your-token>
```

### Existing NetClaw Users

Run the dedicated enablement script:

```bash
./scripts/ipfabric-enable.sh
```

The script will:
1. Check prerequisites (Node.js, npx)
2. Prompt for IP Fabric credentials
3. Test connectivity to your IP Fabric appliance
4. Update your configuration automatically

---

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# IP Fabric Network Assurance Platform
IPFABRIC_HOST=https://ipfabric.example.com    # Appliance URL (no trailing slash)
IPFABRIC_API_TOKEN=your-api-token-here        # API token from Settings → API Tokens
```

### MCP Server Configuration

The IP Fabric MCP server is automatically configured in `~/.openclaw/openclaw.json`:

```json
{
  "mcp": {
    "servers": {
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
  }
}
```

### API Token Creation

1. Log into IP Fabric web UI
2. Navigate to **Settings → API Tokens**
3. Click **Create Token**
4. Set appropriate permissions (see RBAC section below)
5. Copy the token (it won't be shown again)

---

## Tool Reference

### Health Assessment

#### `ipf_network_health_assess`

Comprehensive network health overview including snapshot freshness, intent verification, device issues, and routing stability.

**Parameters:**
- `snapshotId` (optional): Snapshot ID or `$last` for most recent (default: `$last`)

**Returns:** Health status across multiple dimensions

**Example:**
```
Check network health
Show me critical issues only
What's the BGP status across my network?
```

### Path Lookups

#### `ipf_pathlookup_unicast`

Trace the forwarding path between two IP addresses.

**Parameters:**
- `src` (required): Source IP address
- `dst` (required): Destination IP address
- `snapshotId` (optional): Snapshot ID (default: `$last`)
- `vrf` (optional): VRF name for VRF-aware lookup
- `groupBy` (optional): Group by `siteName`, `routingDomain`, or `stpDomain`
- `protocol` (optional): Filter by `tcp`, `udp`, or `icmp`

**Example:**
```
Show me the path from 10.0.1.5 to 10.0.2.10
Trace route from 192.168.1.100 to 10.2.2.2 in VRF MGMT
```

#### `ipf_pathlookup_host-to-gateway`

Trace path from a host to its default gateway.

**Parameters:**
- `src` (required): Source IP address
- `snapshotId` (optional): Snapshot ID (default: `$last`)

**Example:**
```
Show path from 192.168.1.100 to its gateway
```

#### `ipf_pathlookup_multicast`

Trace multicast distribution path.

**Parameters:**
- `src` (required): Source IP address
- `group` (required): Multicast group address
- `snapshotId` (optional): Snapshot ID (default: `$last`)

**Example:**
```
Show multicast path for group 239.1.1.1 from source 10.0.1.5
```

### Path Diagrams (PNG)

#### `ipf_png_pathlookup_unicast`, `ipf_png_pathlookup_host-to-gateway`, `ipf_png_pathlookup_multicast`

Same parameters as corresponding path lookup tools, but return base64-encoded PNG diagrams.

**Example:**
```
Trace route from server A to server B with diagram
Show path from 10.1.1.1 to 10.2.2.2 and visualize it
```

### API Discovery

#### `ipf_api_endpoint_search`

Find API endpoints using natural language.

**Parameters:**
- `query` (required): Natural language search query

**Example:**
```
Find endpoints for device inventory
How do I query interface statistics?
```

#### `ipf_api_endpoint_details`

Get detailed information about a specific endpoint.

**Parameters:**
- `endpoint` (required): Endpoint path from search results

**Returns:** Parameters, request/response schema, examples

#### `api_invoke`

Execute arbitrary API calls.

**Parameters:**
- `endpoint` (required): API endpoint path
- `method` (optional): HTTP method (default: GET)
- `body` (optional): Request body for POST/PUT

**Example:**
```
Invoke /tables/inventory/devices with vendor filter Cisco
```

---

## Query Examples by Use Case

### Network Health Assessment

```
/ipfabric check network health
/ipfabric show me critical issues only
/ipfabric what's the BGP status across my network
/ipfabric are there any routing problems
/ipfabric show snapshot freshness
```

### Path Analysis with Diagrams

```
/ipfabric show me the path from 10.0.1.5 to 10.0.2.10
/ipfabric trace route from server A to server B with diagram
/ipfabric show path from 192.168.1.100 to its gateway
/ipfabric show path from 10.1.1.1 to 10.2.2.2 in VRF MGMT
/ipfabric show multicast path for group 239.1.1.1 from source 10.0.1.5 with diagram
```

### Device Inventory Queries

```
/ipfabric show all Cisco devices in site HQ
/ipfabric find devices with uptime less than 1 day
/ipfabric list devices with telnet enabled
/ipfabric show device counts by vendor
/ipfabric what devices are in site DATACENTER
```

### Routing Protocol Troubleshooting

```
/ipfabric show BGP neighbors that are not in Established state
/ipfabric list OSPF neighbors not in Full state
/ipfabric are there any routing adjacency issues
/ipfabric show routing neighbors for device CORE-RTR-01
```

### Intent Validation and Compliance

```
/ipfabric are there any intent violations
/ipfabric check compliance status
/ipfabric show failed intent rules
/ipfabric what intent checks are failing
```

### Advanced API Queries

```
/ipfabric find endpoints for device inventory
/ipfabric how do I query interface statistics
/ipfabric show me the API for routing tables
/ipfabric invoke /tables/inventory/devices with vendor filter Cisco
```

---

## Snapshot Management

IP Fabric queries execute against a specific snapshot (point-in-time network state).

### Default Behavior

All queries default to `$last` (most recent completed snapshot).

### Override Options

- **By name:** "using snapshot 'June Baseline'"
- **By UUID:** "snapshot abc123-def456"
- **List first:** "list available snapshots"

### Examples

```
/ipfabric check network health using snapshot from last week
/ipfabric show path from 10.0.1.5 to 10.0.2.10 in snapshot 'Pre-Change'
/ipfabric compare current health with snapshot 'Baseline'
```

---

## Diagram Handling

PNG diagrams are returned as base64-encoded images and handled differently based on the interface:

### CLI/Terminal

Diagrams are saved to workspace:
```
~/.openclaw/workspace/diagrams/ipfabric/
├── path-2026-06-19-001.png
└── path-2026-06-19-002.png
```

### Messaging Platforms

Diagrams are attached as files:
- **Slack**: Uploaded to thread
- **Microsoft Teams**: Attached to message
- **Cisco WebEx**: Attached as file
- **Discord**: Uploaded to channel

---

## RBAC Recommendations

The API token's RBAC permissions determine accessible data:

| Role | Recommended Permissions | Use Cases |
|------|------------------------|-----------|
| SOC Analyst | Read-only health, paths | Health monitoring, basic troubleshooting |
| Network Engineer | Full read, path analysis | Troubleshooting, capacity planning |
| Security/Compliance | Intent validation, compliance views | Audit, compliance reporting |
| Administrator | Full access | Intent rule configuration, all operations |

**Security Note:** API tokens are never exposed to the AI model. Only query results (network data) are processed.

---

## Cross-Platform Composition

IP Fabric data can be combined with other NetClaw skills:

### IP Fabric + SuzieQ

Compare live network state with historical SuzieQ data for drift detection:
```
/ipfabric compare network state with SuzieQ historical data
```

### IP Fabric + Batfish

Validate live paths against offline config analysis:
```
/ipfabric validate paths against Batfish config analysis
```

### IP Fabric + Check Point

Correlate network paths with security policies:
```
/ipfabric which Check Point firewall rules affect the path from 10.1.1.1 to 10.2.2.2
```

### IP Fabric + CML/GNS3

Compare production topology with lab environments:
```
/ipfabric compare topology with my CML lab
```

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| "Cannot connect" | Network issue or wrong URL | Verify `IPFABRIC_HOST` and connectivity |
| "Authentication failed" | Invalid or expired token | Regenerate token in IP Fabric UI |
| "Permission denied" | RBAC restrictions | Request appropriate token permissions |
| "Snapshot not found" | Invalid snapshot ID | Use `$last` or list available snapshots |
| "No path exists" | Disconnected endpoints | Check connectivity, verify IPs |

---

## Troubleshooting

### Verify Connectivity

```bash
# Test basic connectivity
curl -k -H "Authorization: Bearer $IPFABRIC_API_TOKEN" \
  "$IPFABRIC_HOST/api/v6.0/health"

# Should return: {"status":"healthy"}
```

### Verify MCP Registration

```bash
# List configured MCP servers
openclaw mcp list | grep ipfabric

# Should show: ipfabric-mcp
```

### Common Issues

1. **"mcp-remote not found"** — Install Node.js 18+ and ensure npx is in PATH
2. **"IPFABRIC_HOST not set"** — Check your `.env` file has the variable defined
3. **"SSL certificate error"** — IP Fabric appliance may use self-signed cert; verify with `curl -k`
4. **"Timeout"** — Large networks may need longer timeouts; check network latency

---

## Security Considerations

- **Token Security**: Store API tokens in `.env` file, never commit to git
- **Data Sensitivity**: Network topology data is sensitive; treat appropriately
- **RBAC**: Use minimum required permissions for each use case
- **Network Access**: Consider firewall rules for access to IP Fabric appliance
- **Audit Trail**: All queries are logged in GAIT session tracking

See [docs/SOUL-DEFENSE.md](SOUL-DEFENSE.md) for comprehensive security guidance.

---

## Related Documentation

- **Skill Reference**: [workspace/skills/ipfabric/SKILL.md](../workspace/skills/ipfabric/SKILL.md)
- **Quickstart**: [specs/032-ipfabric-mcp-integration/quickstart.md](../specs/032-ipfabric-mcp-integration/quickstart.md)
- **IP Fabric Docs**: https://docs.ipfabric.io/latest/IP_Fabric_Settings/integration/mcp/

---

## Partnership Attribution

This integration was developed in collaboration with:

- **Daren Fulwell** — Field CTO, IP Fabric
- **John Capobianco** — Creator, NetClaw

Their partnership, spanning nearly a decade, continues to bring innovative network automation capabilities to the community.
