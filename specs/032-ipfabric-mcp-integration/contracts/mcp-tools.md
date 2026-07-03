# MCP Tool Contracts: IP Fabric MCP Server

**Feature**: 032-ipfabric-mcp-integration
**Date**: 2026-06-19
**MCP Server**: IP Fabric MCP (built into IP Fabric appliances)
**Transport**: Remote HTTP via mcp-remote proxy

## Tool Inventory Summary

| Tool | Category | Returns Data | Returns PNG |
|------|----------|--------------|-------------|
| `ipf_network_health_assess` | Health | ✅ | ❌ |
| `ipf_pathlookup_unicast` | Path | ✅ | ❌ |
| `ipf_pathlookup_host-to-gateway` | Path | ✅ | ❌ |
| `ipf_pathlookup_multicast` | Path | ✅ | ❌ |
| `ipf_png_pathlookup_unicast` | Diagram | ❌ | ✅ |
| `ipf_png_pathlookup_host-to-gateway` | Diagram | ❌ | ✅ |
| `ipf_png_pathlookup_multicast` | Diagram | ❌ | ✅ |
| `ipf_api_endpoint_search` | Discovery | ✅ | ❌ |
| `ipf_api_endpoint_details` | Discovery | ✅ | ❌ |
| `api_invoke` | Generic | ✅ | ❌ |

**Total Tools**: 10

---

## Tool Contracts

### 1. ipf_network_health_assess

**Purpose**: Comprehensive network health assessment including snapshot freshness, intent verification, inventory issues, and routing stability.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `snapshotId` | string | No | `$last` | Snapshot ID or `$last` for most recent |

**Response Schema**:

```json
{
  "snapshot": {
    "id": "string",
    "name": "string",
    "age": "string"
  },
  "summary": {
    "status": "healthy|warning|critical",
    "deviceCount": "number",
    "siteCount": "number"
  },
  "intentVerification": {
    "passed": "number",
    "failed": "number",
    "rules": [
      {
        "name": "string",
        "status": "pass|fail",
        "severity": "low|medium|high|critical"
      }
    ]
  },
  "routing": {
    "bgp": {
      "established": "number",
      "notEstablished": "number"
    },
    "ospf": {
      "full": "number",
      "notFull": "number"
    }
  },
  "inventory": {
    "issues": [
      {
        "device": "string",
        "issue": "string",
        "severity": "string"
      }
    ]
  }
}
```

**Example Usage**:

```
User: "Check network health"
Tool: ipf_network_health_assess()

User: "Show me critical issues only"
Tool: ipf_network_health_assess()
Post-process: Filter for critical severity
```

---

### 2. ipf_pathlookup_unicast

**Purpose**: Trace the network path between two IP addresses.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `src` | string | Yes | - | Source IP address |
| `dst` | string | Yes | - | Destination IP address |
| `snapshotId` | string | No | `$last` | Snapshot ID |
| `groupBy` | string | No | - | Group results by: `siteName`, `routingDomain`, `stpDomain` |
| `protocol` | string | No | - | Filter by protocol (tcp, udp, icmp) |
| `srcPort` | number | No | - | Source port (for tcp/udp) |
| `dstPort` | number | No | - | Destination port (for tcp/udp) |
| `vrf` | string | No | - | VRF name for VRF-aware lookup |

**Response Schema**:

```json
{
  "snapshotId": "string",
  "source": "string",
  "destination": "string",
  "pathExists": "boolean",
  "pathCount": "number",
  "paths": [
    {
      "hops": [
        {
          "order": "number",
          "hostname": "string",
          "site": "string",
          "inInterface": "string",
          "outInterface": "string",
          "forwardingType": "routing|switching|nat|firewall|load-balancer",
          "nextHop": "string"
        }
      ]
    }
  ],
  "decisions": [
    {
      "device": "string",
      "decision": "string",
      "details": "string"
    }
  ]
}
```

**Example Usage**:

```
User: "Show me the path from 10.0.1.5 to 10.0.2.10"
Tool: ipf_pathlookup_unicast(src="10.0.1.5", dst="10.0.2.10")

User: "Trace path from 10.1.1.1 to 10.2.2.2 in VRF MGMT"
Tool: ipf_pathlookup_unicast(src="10.1.1.1", dst="10.2.2.2", vrf="MGMT")
```

---

### 3. ipf_pathlookup_host-to-gateway

**Purpose**: Trace path from a host to its default gateway.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `src` | string | Yes | - | Host IP address |
| `snapshotId` | string | No | `$last` | Snapshot ID |
| `groupBy` | string | No | - | Group results by field |

**Response Schema**:

```json
{
  "snapshotId": "string",
  "host": "string",
  "gateway": "string",
  "pathExists": "boolean",
  "hops": [
    {
      "order": "number",
      "hostname": "string",
      "interface": "string",
      "type": "string"
    }
  ]
}
```

**Example Usage**:

```
User: "Show path from 192.168.1.100 to its gateway"
Tool: ipf_pathlookup_host-to-gateway(src="192.168.1.100")
```

---

### 4. ipf_pathlookup_multicast

**Purpose**: Trace multicast distribution path from source to group.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `src` | string | Yes | - | Multicast source IP |
| `group` | string | Yes | - | Multicast group address (e.g., 239.1.1.1) |
| `snapshotId` | string | No | `$last` | Snapshot ID |
| `groupBy` | string | No | - | Group results by field |

**Response Schema**:

```json
{
  "snapshotId": "string",
  "source": "string",
  "group": "string",
  "pathExists": "boolean",
  "rpAddress": "string",
  "distributionTree": [
    {
      "device": "string",
      "role": "source|rp|receiver|transit",
      "upstreamInterface": "string",
      "downstreamInterfaces": ["string"]
    }
  ]
}
```

**Example Usage**:

```
User: "Show multicast path for group 239.1.1.1 from source 10.0.1.5"
Tool: ipf_pathlookup_multicast(src="10.0.1.5", group="239.1.1.1")
```

---

### 5. ipf_png_pathlookup_unicast

**Purpose**: Generate PNG diagram of unicast path.

**Parameters**: Same as `ipf_pathlookup_unicast`

**Response Schema**:

```json
{
  "format": "png",
  "encoding": "base64",
  "data": "iVBORw0KGgoAAAANSUhEUgAA...",
  "width": "number",
  "height": "number"
}
```

**Example Usage**:

```
User: "Trace route from server A to server B with diagram"
Tool: ipf_png_pathlookup_unicast(src="10.0.1.5", dst="10.0.2.10")
```

---

### 6. ipf_png_pathlookup_host-to-gateway

**Purpose**: Generate PNG diagram of host-to-gateway path.

**Parameters**: Same as `ipf_pathlookup_host-to-gateway`

**Response Schema**: Same as `ipf_png_pathlookup_unicast`

---

### 7. ipf_png_pathlookup_multicast

**Purpose**: Generate PNG diagram of multicast distribution.

**Parameters**: Same as `ipf_pathlookup_multicast`

**Response Schema**: Same as `ipf_png_pathlookup_unicast`

---

### 8. ipf_api_endpoint_search

**Purpose**: Search for IP Fabric API endpoints using natural language.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language search query |

**Response Schema**:

```json
{
  "endpoints": [
    {
      "path": "string",
      "method": "GET|POST",
      "description": "string",
      "category": "string"
    }
  ]
}
```

**Example Usage**:

```
User: "Find endpoints for device inventory"
Tool: ipf_api_endpoint_search(query="device inventory")
```

---

### 9. ipf_api_endpoint_details

**Purpose**: Get detailed information about a specific API endpoint.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `endpoint` | string | Yes | - | API endpoint path |

**Response Schema**:

```json
{
  "path": "string",
  "method": "GET|POST",
  "description": "string",
  "parameters": [
    {
      "name": "string",
      "type": "string",
      "required": "boolean",
      "description": "string"
    }
  ],
  "responseSchema": {},
  "example": {
    "request": {},
    "response": {}
  }
}
```

**Example Usage**:

```
User: "How do I use the device inventory endpoint?"
Tool: ipf_api_endpoint_details(endpoint="/tables/inventory/devices")
```

---

### 10. api_invoke

**Purpose**: Execute arbitrary API calls against IP Fabric.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `endpoint` | string | Yes | - | API endpoint path |
| `method` | string | No | `GET` | HTTP method |
| `params` | object | No | `{}` | Request parameters |
| `body` | object | No | - | Request body (for POST) |

**Response Schema**: Varies by endpoint

**Example Usage**:

```
User: "Show all Cisco devices in site HQ"
Tool: api_invoke(
  endpoint="/tables/inventory/devices",
  method="POST",
  body={
    "filters": {
      "vendor": ["eq", "Cisco"],
      "siteName": ["eq", "HQ"]
    }
  }
)
```

---

## Environment Variable Requirements

| Variable | Required | Description |
|----------|----------|-------------|
| `IPFABRIC_HOST` | Yes | IP Fabric appliance URL (e.g., `https://ipfabric.example.com`) |
| `IPFABRIC_API_TOKEN` | Yes | API token with RBAC permissions |

## NPX Invocation Pattern

```bash
# Direct invocation (for testing)
npx -y mcp-remote https://ipfabric.example.com/mcp \
  --header "Authorization:Bearer ${IPFABRIC_API_TOKEN}"

# OpenClaw configuration
{
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
```

## Tool Availability by License

All tools are available with standard IP Fabric licensing. Some advanced features may require additional licensing:

| Tool | Standard | Advanced |
|------|----------|----------|
| Health Assessment | ✅ | ✅ |
| Path Lookups | ✅ | ✅ |
| Path Diagrams | ✅ | ✅ |
| API Discovery | ✅ | ✅ |
| Multicast Analysis | ⚠️ | ✅ |

⚠️ = Available but may require network discovery of multicast infrastructure
