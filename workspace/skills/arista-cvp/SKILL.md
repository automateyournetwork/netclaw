---
name: arista-cvp
description: "Arista CloudVision Portal (CVP) automation via REST API — device inventory, events, connectivity monitoring, tag management (4 tools)"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["uv"], "env": ["CVP", "CVPTOKEN"] } } }
---

# Arista CloudVision Portal (CVP) Automation

Manage Arista network infrastructure through the CloudVision Portal MCP server. Query device inventory, monitor events and alerts, analyze connectivity probe data (jitter, latency, packet loss), and create device tags through CloudVision's workspace workflow.

## MCP Server

| Field | Value |
|-------|-------|
| **Repository** | [noredistribution/mcp-cvp-fun](https://github.com/noredistribution/mcp-cvp-fun) |
| **Transport** | stdio (FastMCP) |
| **Python** | 3.12+ |
| **Protocol** | HTTPS REST → CloudVision Resource API |
| **Dependencies** | `fastmcp`, `httpx`, `python-dotenv` |
| **Install** | `git clone` + `uv run` (dependencies resolved at runtime) |
| **Entry Point** | `uv run --with fastmcp fastmcp run /path/to/mcp_server_rest.py` |
| **Status** | Community demo — not officially supported by Arista |

## Authentication

CloudVision uses service account tokens passed as HTTP cookies:

1. Log in to CloudVision Portal
2. Navigate to **Settings → Service Accounts**
3. Create a service account and generate a token
4. Store the token in the `.env` file as `CVPTOKEN`

The token is sent as an `access_token` cookie with every API request (not a Bearer header).

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `CVP` | Yes | CloudVision instance hostname (e.g., `www.arista.io` or `cvp.example.com`) |
| `CVPTOKEN` | Yes | Service account token for API authentication |

---

## Tools (4)

### Device Inventory (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_inventory` | — | Get inventory of all devices from CloudVision (hostname, model, serial, version, MAC, IP, streaming status) |

### Event Monitoring (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_events` | — | Get all events from CloudVision (alerts, warnings, informational events with severity, timestamps, device associations) |

### Connectivity Monitoring (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_connectivity_monitor` | — | Get Connectivity Monitor probe statistics (jitter, latency, packet loss, HTTP response time across all probes) |

### Tag Management (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_tag` | `tag_name`, `tag_value` | Create a device-level tag in CloudVision via workspace workflow (create workspace → create tag → build → submit) |

### `create_tag` Workflow Detail

The `create_tag` tool follows CloudVision's workspace model — a 5-step process:

1. **Create Workspace** — POST to `/api/resources/workspace/v1/WorkspaceConfig` with a UUID-based workspace
2. **Create Tag** — POST to `/api/resources/tag/v2/TagConfig` with `ELEMENT_TYPE_DEVICE`, workspace ID, tag name/value
3. **Build Workspace** — POST with `REQUEST_START_BUILD` to validate changes
4. **Wait for Build** — 10-second wait for build completion
5. **Submit Workspace** — POST with `REQUEST_SUBMIT` to apply the tag

---

## CloudVision Resource API Endpoints

| Method | Endpoint | Tool |
|--------|----------|------|
| GET | `/api/resources/inventory/v1/Device/all` | `get_inventory` |
| GET | `/api/resources/event/v1/Event/all` | `get_events` |
| GET | `/api/resources/connectivitymonitor/v1/ProbeStats/all` | `get_connectivity_monitor` |
| POST | `/api/resources/workspace/v1/WorkspaceConfig` | `create_tag` (workspace create/build/submit) |
| POST | `/api/resources/tag/v2/TagConfig` | `create_tag` (tag creation) |

Responses use newline-delimited JSON (NDJSON) format, consistent with CloudVision's streaming resource API.

---

## Workflows

### 1. Arista Device Discovery
```
get_inventory → list all Arista devices (hostname, model, serial, version, MAC, IP)
→ Cross-reference with NetBox/Nautobot → flag discrepancies
→ GAIT
```

### 2. Arista Event Monitoring
```
get_events → retrieve all CloudVision events
→ Filter by severity (critical, warning, info)
→ Correlate events with device inventory
→ Severity-sort findings → GAIT
```

### 3. Arista Network Health Check
```
get_inventory → identify all managed devices
→ get_events → check for active alarms and warnings
→ get_connectivity_monitor → analyze jitter, latency, packet loss
→ Correlate connectivity issues with events → severity-sort → GAIT
```

### 4. Arista Device Tagging
```
ServiceNow CR must be in Implement state
→ get_inventory → verify target devices exist
→ create_tag(tag_name, tag_value) → apply device-level tag via workspace workflow
→ get_inventory → verify tag applied
→ GAIT
```

### 5. Arista Connectivity Baseline
```
get_connectivity_monitor → capture current probe statistics
→ Record jitter, latency, packet loss baselines per probe
→ Compare against thresholds → flag degradation
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | CVP MCP for Arista fleet visibility, pyATS MCP for Cisco devices — unified multi-vendor monitoring |
| **junos-network** | CVP MCP for Arista, JunOS MCP for Juniper — multi-vendor device inventory and health |
| **netbox-reconcile** | Cross-reference CVP device inventory (model, serial, version) against NetBox source of truth |
| **nautobot-sot** | Same as NetBox — validate Arista device IPAM data in Nautobot |
| **infrahub-sot** | Cross-reference Infrahub node data with Arista device inventory from CVP |
| **servicenow-change-workflow** | Gate all `create_tag` operations behind ServiceNow Change Requests |
| **gait-session-tracking** | Every CVP inventory query, event pull, and tag creation logged in GAIT |
| **te-network-monitoring** | Correlate ThousandEyes path data with CVP connectivity monitor probes |
| **nvd-cve** | Scan EOS versions from `get_inventory` against NVD vulnerability database |
| **markmap-viz** | Generate topology mind maps from CVP device inventory data |

---

## CVP MCP vs pyATS MCP vs JunOS MCP

| Capability | CVP MCP | pyATS MCP | JunOS MCP |
|-----------|---------|-----------|-----------|
| **Vendor** | Arista (via CVP) | Cisco (IOS-XE, NX-OS, IOS-XR) | Juniper |
| **Protocol** | HTTPS REST → CVP Resource API | SSH + Genie parsers | NETCONF → PyEZ |
| **Device Inventory** | `get_inventory` (fleet-wide) | `pyats_learn("platform")` per device | `gather_device_facts` per device |
| **Event Monitoring** | `get_events` (fleet-wide) | Per-device show commands | Per-device show commands |
| **Connectivity Metrics** | `get_connectivity_monitor` (probes) | Per-device show commands | Per-device show commands |
| **Config Push** | Via CVP Change Control (not in MCP) | `pyats_configure_device` | `load_and_commit_config` |
| **Tag/Label Mgmt** | `create_tag` (workspace workflow) | N/A | N/A |
| **Batch Operations** | All tools are fleet-wide by default | `pyats_pcall` (parallel pCall) | `execute_junos_command_batch` |
| **MCP Tools** | 4 | 8 | 10 |

---

## Guardrails

- **Always call `get_inventory` first** — verify CloudVision is reachable and devices are streaming before deeper queries
- **Check events before changes** — call `get_events` to identify active issues before any tag operations
- **Gate tag creation** — all `create_tag` calls must have a ServiceNow CR in `Implement` state
- **Validate tag names** — ensure tag names follow organizational naming conventions before creation
- **Monitor connectivity baselines** — use `get_connectivity_monitor` to establish baselines before and after network changes
- **Cross-reference inventory** — compare CVP device data with NetBox/Nautobot to detect SoT drift
- **Record in GAIT** — every inventory query, event pull, connectivity check, and tag creation must be logged
- **Community project** — this is an unofficial demo; evaluate security implications (TLS verification disabled in source) before production use
