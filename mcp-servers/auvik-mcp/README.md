# Auvik API MCP Server (Feature 036)

Read-only FastMCP server that exposes 20 tools for querying the Auvik network
management platform. All tools are GET-only — no create, update, or delete
operations are available.

**Transport:** stdio (launch with `python auvik_mcp_server.py`; stdout is the
MCP JSON-RPC channel, all logging goes to stderr).

---

## Tools

### Inventory (9 tools)

| Tool | What it does |
|---|---|
| `auvik_list_devices` | List or inspect discovered devices at info / detail / extended level. Resolves device param from name, IP, or Auvik ID. `detail_level=extended` requires `device_type`. |
| `auvik_list_networks` | List or inspect networks (info or detail level). Resolves network param from name or Auvik ID. |
| `auvik_list_interfaces` | List network interfaces. `interface` param must be an Auvik numeric ID. `parent_device` resolves from name or IP. |
| `auvik_list_components` | List hardware components (CPU, memory, disk, fan, PSU, etc.). Optionally filter by device name / IP / ID. |
| `auvik_list_tenants` | List all tenants (clients) visible to the API key. Source of truth for `tenants` param used by other tools. `detail=True` requires `tenant_domain_prefix`. |
| `auvik_list_entity_notes` | List notes attached to entities (devices, networks, interfaces). Resolves entity param from device name or Auvik ID. |
| `auvik_list_entity_audits` | List audit log entries for managed entities. Filter by user, category, status, or date. |
| `auvik_get_usage` | Get billing/usage data for a date range. `scope=client` (default) or `scope=device`. Both require `from_date` and `thru_date`. |
| `auvik_verify_credentials` | Verify API credentials via GET /v1/authentication/verify. Use as a health-check. |

### Alerts (1 tool)

| Tool | What it does |
|---|---|
| `auvik_list_alerts` | List alert history. Filter by severity (unknown / emergency / critical / warning / info), status, dismissed, entity, or time window. `detected_time_after` / `detected_time_before` are ISO-8601 datetime strings. |

### Lifecycle (3 tools)

| Tool | What it does |
|---|---|
| `auvik_list_device_lifecycle` | List EoL / EoS lifecycle status for network devices. Filter by sales_availability, software_maintenance_status, security_software_maintenance_status, or last_support_status. |
| `auvik_list_device_warranty` | List warranty and service contract status. Filter by `covered_under_warranty` or `covered_under_service` (bool). |
| `auvik_list_configurations` | List device configuration backups. `config_id` returns the full backup body. Filter by device, backup time window, or `is_running`. |

### Performance (7 tools)

| Tool | What it does |
|---|---|
| `auvik_get_device_statistics` | Time-series device stats. `stat_id`, `from_time`, `interval` required. `availability=True` switches to deviceAvailability path (stat_id: uptime / outage). |
| `auvik_get_interface_statistics` | Time-series interface stats. `stat_id`, `from_time`, `interval` required. stat_id: bandwidth / utilization / packetLoss / packetDiscard / packetMulticast / packetUnicast / packetBroadcast. |
| `auvik_get_service_statistics` | Time-series service (ping) stats. `stat_id` (pingTime or pingPacket), `from_time`, `interval` required. |
| `auvik_get_component_statistics` | Time-series hardware component stats. `component_type`, `stat_id`, `from_time`, `interval` required. |
| `auvik_get_oid_statistics` | Point-in-time OID values from /v1/stat/oid/deviceMonitor. No time window required. |
| `auvik_list_snmp_poller_settings` | List SNMP poller configurations. `tenants` is REQUIRED. `poller_id` + `with_devices=True` returns assigned devices. |
| `auvik_get_snmp_poller_history` | Historical SNMP poller data. `tenants` and `from_time` required. `value_type=int` requires `interval`; `value_type=string` accepts `compact`. |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AUVIK_USERNAME` | Yes | — | Auvik user email address (Basic-auth username) |
| `AUVIK_API_KEY` | Yes | — | Auvik API key (Basic-auth password) |
| `AUVIK_BASE_URL` | No | `https://auvikapi.us1.my.auvik.com` | Regional cluster URL (swap `us1` for your region) |
| `AUVIK_VERIFY_SSL` | No | `true` | Set `false` to skip TLS verification (not recommended) |
| `AUVIK_TIMEOUT` | No | `30` | HTTP request timeout in seconds |
| `AUVIK_RATE_LIMIT` | No | `600` | Maximum API calls per 60-second window |
| `AUVIK_MAX_PAGES` | No | `50` | Pagination safety cap (stops auto-pagination after N pages) |

---

## Install

```bash
cd mcp-servers/auvik-mcp
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Configure

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# edit .env — set AUVIK_USERNAME and AUVIK_API_KEY
```

## Run (stdio)

```bash
python mcp-servers/auvik-mcp/auvik_mcp_server.py
```

The server speaks MCP JSON-RPC over stdio. Register it in `config/openclaw.json`
as `"auvik-mcp"` for OpenClaw integration.

---

## Read-only — no write tools

This server is intentionally read-only. `AuvikClient` exposes only `get` and
`get_all` methods. No `post`, `put`, `delete`, or `patch` methods exist. Every
registered tool name begins with `auvik_list_*`, `auvik_get_*`, or
`auvik_verify_*`. The test suite asserts these guarantees on every run.

---

## Identifier resolution

All `device`, `network`, `entity`, and `parent_device` parameters accept:

- **Auvik numeric ID** (6+ digits) — used directly, no lookup.
- **Device hostname / network name** — resolved via GET /v1/inventory/device/info
  with a name filter.
- **IP address** — resolved via the same endpoint with an IP filter.

Ambiguous matches (more than one result) return `ResolutionCandidate[]` so you
can narrow the query. No matches return a clear `NotFound` error.

---

## Troubleshooting

- **401 / 403** — check `AUVIK_USERNAME` and `AUVIK_API_KEY`; verify the API
  key's role has read access; check `AUVIK_BASE_URL` for the correct region.
- **Empty results for a known device** — the device may be under a different
  tenant; pass `tenants=<domain_prefix>` or call `auvik_list_tenants()` first.
- **ValidationError: device_type required** — `detail_level=extended` mandates
  `device_type` (Auvik API requirement).
- **Truncated list / `truncated: true`** — raise `AUVIK_MAX_PAGES` in `.env`,
  or narrow filters to reduce result size.
