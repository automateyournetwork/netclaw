# Claroty xDome MCP Server

MCP server for the [Claroty xDome](https://claroty.com/industrial-cybersecurity/xdome) OT / IoT / IoMT visibility and threat-detection platform. Wraps the xDome REST API and exposes 21 tools (15 read-only + 6 ITSM-gated writes) via stdio transport.

## Tools (21)

### Read-only (15)

| Tool | xDome endpoint | Purpose |
|------|----------------|---------|
| `list_devices` | `POST /api/v1/devices/` | Inventory all OT/IoT/IoMT devices (filter by site, Purdue level, purpose, name) |
| `get_device_details` | `POST /api/v1/devices/{id}/` | Full record for a single device |
| `get_device_communication_map` | `POST /api/v1/device_communication_map/` | Device-to-device edges for topology rendering |
| `list_alerts` | `POST /api/v1/alerts/` | Security alerts (filter by severity, status, site, assignee) |
| `get_alert_with_devices` | `POST /api/v1/alerts/{id}/devices` (composite) | Alert plus blast-radius devices |
| `list_vulnerabilities` | `POST /api/v1/vulnerabilities/` | CVE-aligned findings (filter by severity, CVSS, CVE substring) |
| `get_vulnerable_devices` | `POST /api/v1/vulnerabilities/{id}/devices` | Devices affected by one vulnerability |
| `list_sites` | `POST /api/v1/sites/get` | Site inventory |
| `get_site` | `POST /api/v1/sites/get` (filtered) | Single site by ID |
| `list_edge_locations` | `POST /api/v1/edge_management/locations/get` | Edge sensor fleet visibility |
| `list_servers` | `POST /api/v1/servers/` | Physical / virtual server nodes |
| `get_server_interfaces` | `POST /api/v1/server_interfaces/` | NIC inventory and traffic stats |
| `list_ot_activity_events` | `POST /api/v1/ot_activity_events/` | OT activity / protocol observations |
| `get_audit_log` | `POST /api/v1/audit_log/get` | User actions, config changes, policy updates |
| `list_organization_zones` | `POST /api/v1/organization/zones/` | Network segmentation zones |

### ITSM-gated writes (6)

Every write tool requires a `cr_number` in `CHG\d+` format. The CR is validated against ServiceNow ("Implement" state) unless `NETCLAW_LAB_MODE=true`, in which case the format check is the only gate. See `utils/itsm_gate.py`.

| Tool | xDome endpoint | Purpose |
|------|----------------|---------|
| `acknowledge_alert` | `POST /api/v1/device_alert_status_set` | Set alert resolution state |
| `set_vulnerability_relevance` | `POST /api/v1/device_vulnerability_relations/relevance_set` | Triage: mark CVE relevant/not for a device |
| `set_device_purdue_level` | `POST /api/v1/devices/purdue_level_set` | Assign Purdue Model layer |
| `set_device_custom_attribute` | `POST /api/v1/devices/custom_attribute_set` | Set a custom asset attribute |
| `label_alerts` | `POST /api/v1/user_actions/labels/set` (or `/replace`) | Apply / replace labels on alerts (batch) |
| `assign_alerts` | `POST /api/v1/user_actions/assignees/set` | Assign alerts to a user / queue (batch) |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAROTY_API_URL` | No | `https://api.medigate.io` | xDome base URL |
| `CLAROTY_API_TOKEN` | **Yes** | – | Bearer token (Admin Settings > User Management) |
| `CLAROTY_VERIFY_SSL` | No | `true` | Verify TLS certificates |
| `CLAROTY_TIMEOUT` | No | `30` | Per-request timeout (seconds) |
| `CLAROTY_RATE_LIMIT_PER_MIN` | No | `2000` | Sliding-window request budget |
| `NETCLAW_LAB_MODE` | No | `false` | Shared lab-mode flag — bypasses ServiceNow CR state check |

### Token scopes

xDome tokens carry per-resource scopes. The wrapper does not enforce these locally — it surfaces xDome's 403 with the body intact. If you see:

```
"error": {"status_code": 403, "message": "...lacks the scope needed...", "body": {"detail": "Token lacks write:alerts scope"}}
```

…the request reached xDome and was rejected at RBAC. The ITSM gate and the request shape are fine — fix the token, not the code. Each write tool needs write scope on the matching resource:

| Tool | Required scope (typical) |
|------|--------------------------|
| `acknowledge_alert` | write on alerts |
| `label_alerts` / `assign_alerts` | write on alerts (user actions) |
| `set_device_purdue_level` / `set_device_custom_attribute` | write on devices |
| `set_vulnerability_relevance` | write on vulnerabilities |

Read-only tokens 403 on every write — that's expected. For dry-run validation of write paths, use `NETCLAW_LAB_MODE=true` with a read-only token: the ITSM gate passes, the body is built and validated, and you see the structured 403 with no real change to xDome state.

## Transport

**stdio** (JSON-RPC 2.0) via FastMCP. Registered in `config/openclaw.json` under `mcpServers.claroty-mcp`.

## Installation

```bash
cd mcp-servers/claroty-mcp/
pip install -r requirements.txt
```

`scripts/install.sh` does this for you when you re-run the installer.

## Usage

### Standalone test

```bash
export CLAROTY_API_URL="https://api.medigate.io"
export CLAROTY_API_TOKEN="<your-token>"
export NETCLAW_LAB_MODE="true"
python3 -u mcp-servers/claroty-mcp/claroty_mcp_server.py
```

### Via the agent

- "List the first 50 OT devices at site warehouse-east and show their Purdue levels" → `list_devices(site_id=...)`
- "Show me the communication map for device <id>" → `get_device_communication_map(device_id=...)`
- "What devices are exposed to CVE-2024-12345?" → `list_vulnerabilities(cve_contains="2024-12345")` → `get_vulnerable_devices(vulnerability_id=...)`
- "Acknowledge alert <id> under CHG0012345 with a note" → `acknowledge_alert(alert_id, resolution="acknowledged", cr_number="CHG0012345", note="...")`

## Architecture notes

- **Client abstraction** — `clients/claroty_client.py` exposes `post(endpoint, body)`, `paginate(...)`, and `collect(...)`. Tool authors never write a pagination loop or think about the all-POST quirk.
- **Rate gating** — `utils/rate_limiter.py` is a `SlidingWindowRateLimiter` (asyncio-safe, monotonic clock) that lives inside `client.post()`. Default 2000 calls/min matches the xDome upstream cap.
- **429 backoff** — `client.post()` honors the `Retry-After` header up to 5 attempts.
- **GCF serialization** — `utils/gcf_helper.py` is the shim that imports `netclaw_tokens.gcf_serializer.serialize_response()` with a JSON fallback (per project convention).
- **ITSM gate** — `utils/itsm_gate.py` is the same `CHG\d+` + `NETCLAW_LAB_MODE` gate used by `gnmi-mcp/itsm_gate.py`. Every write tool calls `validate_change_request(cr_number)` first.

## Deferred to a future spec

The following xDome capabilities are intentionally not in v1 — see `specs/035-claroty-mcp/research.md` for the rationale:

- Edge sensor lifecycle (add/update/delete locations, generate/rotate API keys)
- Site CRUD (the current `list_sites` / `get_site` are read-only)
- Organization policy CRUD (zones, firewall groups, ACL policies, attribution rules)
- CMMS asset upsert and match jobs
