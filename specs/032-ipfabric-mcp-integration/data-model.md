# Phase 1 Data Model: IP Fabric MCP Integration

**Feature**: 032-ipfabric-mcp-integration
**Date**: 2026-06-19
**Status**: Complete

## 1. MCP Server Configuration Schema

### OpenClaw Configuration Format

The IP Fabric MCP is registered in `~/.openclaw/openclaw.json` under `mcp.servers`:

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

### Schema Definition

```typescript
interface IPFabricMCPConfig {
  command: "npx";
  args: ["-y", "mcp-remote", string, "--header", string];
  env: {
    IPFABRIC_AUTH_HEADER: string;
  };
}
```

### Configuration Validation

| Field | Required | Validation |
|-------|----------|------------|
| `command` | Yes | Must be `"npx"` |
| `args[0]` | Yes | Must be `"-y"` |
| `args[1]` | Yes | Must be `"mcp-remote"` |
| `args[2]` | Yes | Must be valid URL ending in `/mcp` |
| `args[3]` | Yes | Must be `"--header"` |
| `args[4]` | Yes | Must start with `"Authorization:"` |
| `env.IPFABRIC_AUTH_HEADER` | Yes | Must start with `"Bearer "` |

## 2. Environment Variable Requirements

### Required Variables

```bash
# IP Fabric MCP Integration
# Documentation: docs/IPFABRIC.md

# IP Fabric appliance base URL (no trailing slash)
IPFABRIC_HOST=https://ipfabric.example.com

# API token with appropriate RBAC permissions
# Generate at: IP Fabric UI → Settings → API Tokens
IPFABRIC_API_TOKEN=your-api-token-here
```

### Variable Resolution Flow

```
User sets in .env:
  IPFABRIC_HOST=https://ipfabric.example.com
  IPFABRIC_API_TOKEN=abc123

OpenClaw resolves at runtime:
  args[2] = "${IPFABRIC_HOST}/mcp" → "https://ipfabric.example.com/mcp"
  env.IPFABRIC_AUTH_HEADER = "Bearer ${IPFABRIC_API_TOKEN}" → "Bearer abc123"
  args[4] = "Authorization:${IPFABRIC_AUTH_HEADER}" → "Authorization:Bearer abc123"
```

## 3. Query Router Mapping Table

The `/ipfabric` skill auto-routes natural language queries to appropriate tools:

### Primary Query Patterns

| Query Category | Pattern Keywords | Primary Tool | Fallback |
|----------------|------------------|--------------|----------|
| Health | health, status, issues, problems, violations | `ipf_network_health_assess` | - |
| Unicast Path | path, trace, route, from...to | `ipf_pathlookup_unicast` | - |
| Gateway Path | gateway, default gateway, host-to-gateway | `ipf_pathlookup_host-to-gateway` | - |
| Multicast Path | multicast, group, mcast | `ipf_pathlookup_multicast` | - |
| Diagram | diagram, png, image, visualize, picture | `ipf_png_*` variant | Add to path query |
| Inventory | devices, inventory, show all, list | `api_invoke` | `ipf_api_endpoint_search` |
| Routing | bgp, ospf, routing, neighbors, adjacency | `ipf_network_health_assess` | `api_invoke` |
| Intent | intent, compliance, verification | `ipf_network_health_assess` | - |
| API Discovery | find endpoint, api for, how to query | `ipf_api_endpoint_search` | - |

### Routing Decision Tree

```
User Query
    │
    ├─ Contains "health" OR "status" OR "issues"?
    │   └─ Yes → ipf_network_health_assess
    │
    ├─ Contains "path" OR "trace" OR "route"?
    │   ├─ Contains "multicast" OR "group"?
    │   │   └─ Yes → ipf_pathlookup_multicast (or png variant)
    │   ├─ Contains "gateway"?
    │   │   └─ Yes → ipf_pathlookup_host-to-gateway (or png variant)
    │   └─ Default → ipf_pathlookup_unicast (or png variant)
    │
    ├─ Contains "diagram" OR "png" OR "image"?
    │   └─ Yes → Use ipf_png_* variant of appropriate pathlookup
    │
    ├─ Contains "find endpoint" OR "api for"?
    │   └─ Yes → ipf_api_endpoint_search
    │
    └─ Default → ipf_network_health_assess
```

### Parameter Extraction

| User Input | Extracted Parameters |
|------------|---------------------|
| "from 10.0.1.5 to 10.0.2.10" | `src: "10.0.1.5"`, `dst: "10.0.2.10"` |
| "in VRF MGMT" | `vrf: "MGMT"` |
| "for group 239.1.1.1" | `group: "239.1.1.1"` |
| "snapshot abc123" | `snapshotId: "abc123"` |
| "in site HQ" | Filter by siteName in results |

## 4. Snapshot Handling

### Default Snapshot Behavior

```
snapshotId Resolution:
    │
    ├─ User specified snapshotId?
    │   └─ Yes → Use specified value
    │
    └─ No → Default to "$last"
```

### Snapshot Data Model

```typescript
interface Snapshot {
  id: string;           // UUID
  name: string;         // Human-readable name
  state: "running" | "completed" | "failed" | "loaded";
  start: string;        // ISO 8601 timestamp
  end?: string;         // ISO 8601 timestamp (null if running)
  version: string;      // IP Fabric version
}
```

### Snapshot Selection UX

1. **Implicit**: Query without snapshot → uses `$last`
2. **By Name**: "using snapshot 'June Baseline'" → lookup by name
3. **By UUID**: "snapshot abc123-def456" → direct use
4. **List First**: "list snapshots" → show available, then ask

## 5. Tool Response Models

### Health Assessment Response

```typescript
interface HealthAssessmentResponse {
  snapshotId: string;
  snapshotAge: string;              // "2 hours ago"
  summary: {
    status: "healthy" | "warning" | "critical";
    deviceCount: number;
    siteCount: number;
  };
  intentVerification: {
    passed: number;
    failed: number;
    rules: IntentRule[];
  };
  routingStability: {
    bgpNeighborsUp: number;
    bgpNeighborsDown: number;
    ospfNeighborsFull: number;
    ospfNeighborsPartial: number;
  };
  inventoryIssues: InventoryIssue[];
}
```

### Path Lookup Response

```typescript
interface PathLookupResponse {
  snapshotId: string;
  source: string;
  destination: string;
  pathExists: boolean;
  hops: PathHop[];
  decisions: ForwardingDecision[];
}

interface PathHop {
  order: number;
  hostname: string;
  inInterface: string;
  outInterface: string;
  forwardingType: "routing" | "switching" | "nat" | "firewall";
}
```

### PNG Diagram Response

```typescript
interface DiagramResponse {
  snapshotId: string;
  format: "png";
  encoding: "base64";
  data: string;         // Base64-encoded PNG
  width: number;
  height: number;
}
```

## 6. Error Handling Model

### Error Categories

| Category | HTTP Status | User Message |
|----------|-------------|--------------|
| Authentication | 401 | "IP Fabric API token is invalid or expired. Generate a new token in IP Fabric Settings → API Tokens." |
| Authorization | 403 | "API token lacks permission for this operation. Check RBAC settings in IP Fabric." |
| Not Found | 404 | "Resource not found. Verify the snapshot exists or check the IP/hostname." |
| Server Error | 500+ | "IP Fabric server error. Check appliance status at ${IPFABRIC_HOST}." |
| Connectivity | - | "Cannot reach IP Fabric at ${IPFABRIC_HOST}. Verify network connectivity and URL." |

### Error Response Format

```typescript
interface ErrorResponse {
  error: true;
  code: string;           // e.g., "AUTH_FAILED", "NOT_FOUND"
  message: string;        // User-friendly message
  details?: string;       // Technical details (for debugging)
  resolution: string;     // How to fix
}
```

## 7. Cross-Platform Composition Model

### Composition Patterns

| Integration | IP Fabric Provides | Partner Provides | Correlation Key |
|-------------|-------------------|------------------|-----------------|
| SuzieQ | Live network state | Historical state analysis | Device hostname, interface |
| Batfish | Live paths, topology | Config analysis, validation | Device name, interface |
| Check Point | Path endpoints | Security policy, rules | Source/dest IP |
| CML/GNS3 | Production topology | Lab topology | Hostname, IP addressing |

### Composition Example: IP Fabric + Batfish

```
User: "Compare IP Fabric path to Batfish analysis"

1. ipf_pathlookup_unicast(src, dst) → Live path
2. batfish.traceroute(src, dst) → Config-predicted path
3. Compare hop-by-hop:
   - Match: ✅ Config matches operational state
   - Mismatch: ⚠️ Operational state differs from intent
```
