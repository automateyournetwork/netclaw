---
name: claroty-asset-inventory
description: "Discover and classify OT / IoT / IoMT assets via Claroty xDome. List devices by site, Purdue level, and device purpose; assign Purdue layers and custom attributes; cross-reference with Nautobot / NetBox SoT to surface drift."
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["CLAROTY_API_URL", "CLAROTY_API_TOKEN"]
---

# Claroty Asset Inventory

OT / IoT / IoMT asset discovery, Purdue Model classification, and source-of-truth reconciliation, using the Claroty xDome MCP server.

## When to Use

- Building an OT asset inventory for a site, plant, or facility
- Filtering devices by Purdue level (0 — process; 1 — control; 2 — supervisory; 3 — operations; 3.5 — DMZ; 4/5 — enterprise)
- Identifying devices by purpose (PLC, HMI, RTU, engineering workstation, historian, IP camera, medical device)
- Assigning a Purdue layer to a newly discovered device (ITSM-gated write)
- Recording an out-of-band classification or compliance tag via custom attributes (ITSM-gated write)
- Cross-referencing xDome's discovered inventory against Nautobot or NetBox source-of-truth and surfacing drift

## MCP Server

- **Server**: `claroty-mcp` (in-repo, `mcp-servers/claroty-mcp/claroty_mcp_server.py`)
- **Command**: `python3 -u mcp-servers/claroty-mcp/claroty_mcp_server.py` (stdio transport)
- **Auth**: Bearer token via `CLAROTY_API_TOKEN`
- **ITSM**: Write operations require a ServiceNow CR (`CHG\d+`); bypassed in `NETCLAW_LAB_MODE=true`

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `list_devices` | `site_id?, purdue_level?, device_purpose?, name_contains?, limit?, offset?, max_items?` | List xDome-managed devices with rich filters |
| `get_device_details` | `device_id` | Full record for a single device including raw attributes |
| `set_device_purdue_level` | `device_id, purdue_level, cr_number` | **Write (ITSM-gated)** — assign Purdue layer |
| `set_device_custom_attribute` | `device_id, attribute_key, attribute_value, cr_number` | **Write (ITSM-gated)** — set a custom attribute |

For cross-referencing, also reach for:

- `nautobot_get_ip_address` / `nautobot_get_prefix` from the **nautobot-sot** skill
- `netbox-reconcile` from the NetBox skills

## Workflow Examples

### Inventory by site and Purdue layer

```
"List the first 50 devices at site warehouse-east at Purdue level 1, showing names, vendors, and risk scores"
```

Calls `list_devices(site_id="warehouse-east", purdue_level="Level 1", limit=50)`. Returns a GCF-encoded device table.

### Find every PLC in the fleet

```
"List all PLCs across all sites"
```

Calls `list_devices(device_purpose="PLC", max_items=500)`.

### Classify a newly discovered device

```
"Set device 7a2c... to Purdue level 2 under CHG0012345"
```

Calls `set_device_purdue_level(device_id="7a2c...", purdue_level="Level 2", cr_number="CHG0012345")`. The ITSM gate validates the CR before the POST.

### SoT drift check

```
"Compare xDome devices at site warehouse-east to Nautobot's inventory for that site and flag anything missing on either side"
```

1. `list_devices(site_id="warehouse-east")` → xDome set
2. `nautobot_get_ip_address(...)` filtered by site → SoT set
3. The agent diffs MAC / IP / name and reports IP_DRIFT, MISSING_FROM_SOT, and MISSING_FROM_XDOME entries.

### Tag for compliance audit

```
"Mark device 9f4d... with custom attribute compliance_scope=PCI under CHG0012999"
```

Calls `set_device_custom_attribute(device_id="9f4d...", attribute_key="compliance_scope", attribute_value="PCI", cr_number="CHG0012999")`.

## ITSM gating

All write tools call `validate_change_request(cr_number)` from `mcp-servers/claroty-mcp/utils/itsm_gate.py`. The CR must:

1. Match `CHG\d+`.
2. Be in "Implement" state in ServiceNow (skipped in `NETCLAW_LAB_MODE=true`).

A rejection returns `{"itsm_gate": {...}, "applied": false}` and the xDome call is NOT made.

## Token scope expectations

If `set_device_purdue_level` or `set_device_custom_attribute` returns `applied: false` and an `error` object with `status_code: 403`, the ITSM gate passed and the request body is correct — xDome rejected at RBAC. The token in `CLAROTY_API_TOKEN` lacks write scope on devices. Don't retry — escalate to whoever provisions xDome API tokens.

## GAIT audit

Every tool invocation is recorded in GAIT. The audit trail includes the tool name, parameters, CR number (for writes), and the xDome response status.
