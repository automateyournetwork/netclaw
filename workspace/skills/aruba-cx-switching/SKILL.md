---
name: aruba-cx-switching
description: "View and manage Aruba CX switch VLANs and MAC address tables for Layer 2 operations"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["ARUBA_CX_TARGETS"]
---

# Aruba CX Switching Operations

View VLANs, MAC address tables, and manage Layer 2 operations on HPE Aruba CX switches. Includes read-only operations for viewing network segmentation and write operations (ITSM-gated) for VLAN management.

## When to Use

- Viewing VLAN configurations and port assignments
- Tracking MAC addresses across the switching fabric
- Finding which port a specific endpoint is connected to
- Creating, modifying, or deleting VLANs (with ITSM approval)
- Auditing network segmentation
- Troubleshooting Layer 2 connectivity

## MCP Server

- **Server**: `aruba-cx-mcp` (community MCP from slientnight)
- **Command**: `python3 -u mcp-servers/aruba-cx-mcp/aruba_cx_mcp_server.py` (stdio transport)
- **Auth**: REST API via `ARUBA_CX_TARGETS` (JSON array) or `ARUBA_CX_CONFIG` (file path)
- **ITSM**: Write operations require CR when `ITSM_ENABLED=true`

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_vlans` | target, vlan_id? | Get VLAN configurations (ID, name, ports) |
| `get_mac_table` | target, vlan_id?, mac_address? | Get MAC address table entries |
| `create_vlan` | target, vlan_id, name?, cr_number? | Create a new VLAN (ITSM-gated) |
| `configure_vlan` | target, vlan_id, name?, tagged_ports?, untagged_ports?, cr_number? | Modify VLAN (ITSM-gated) |
| `delete_vlan` | target, vlan_id, cr_number? | Delete a VLAN (ITSM-gated) |

## Workflow Examples

### VLAN Discovery

```bash
# View all VLANs
"Show all VLANs on core-sw-1"

# Check specific VLAN
"What ports are in VLAN 100 on core-sw-1?"

# List VLAN names
"Show me the VLAN names configured on core-sw-1"

# Find untagged ports
"Which ports are untagged in VLAN 100?"
```

### MAC Address Tracking

```bash
# View full MAC table
"Show the MAC address table for core-sw-1"

# Filter by VLAN
"Show MAC addresses in VLAN 100 on core-sw-1"

# Find specific MAC
"Find MAC address aa:bb:cc:dd:ee:ff on core-sw-1"

# Locate endpoint
"Which port is MAC aa:bb:cc:dd:ee:ff learned on?"

# Count MACs per VLAN
"How many MAC addresses are in each VLAN on core-sw-1?"
```

### VLAN Management (ITSM-Gated)

```bash
# Create VLAN (requires CR when ITSM enabled)
"Create VLAN 200 named 'Guest_Network' on core-sw-1 with CR CHG0001234"

# Modify VLAN (requires CR when ITSM enabled)
"Add port 1/1/10 as untagged to VLAN 200 on core-sw-1 with CR CHG0001234"

# Rename VLAN
"Rename VLAN 200 to 'Visitor_Network' on core-sw-1 with CR CHG0001234"

# Delete VLAN (requires CR when ITSM enabled)
"Delete VLAN 200 on core-sw-1 with CR CHG0001234"
```

## ITSM Integration

Write operations (create_vlan, configure_vlan, delete_vlan) require change management approval:

| Environment Variable | Behavior |
|---------------------|----------|
| `ITSM_ENABLED=false` | Write operations proceed without CR validation |
| `ITSM_ENABLED=true` | Write operations require valid ServiceNow CR number |
| `ITSM_LAB_MODE=true` | CR format validated but not checked against ServiceNow |

**CR Format**: Must match ServiceNow pattern (e.g., CHG0001234)

## Integration with Other Skills

- **aruba-cx-system**: First discover switches, then view their VLANs
- **aruba-cx-interfaces**: Check which interfaces are in which VLANs
- **aruba-cx-config**: View full running configuration including VLANs

## Response Examples

### VLAN List Response

```json
[
  {
    "id": 1,
    "name": "default",
    "admin_state": "up",
    "tagged_ports": [],
    "untagged_ports": ["1/1/1", "1/1/2"],
    "voice": false
  },
  {
    "id": 100,
    "name": "Management",
    "admin_state": "up",
    "tagged_ports": ["1/1/49", "1/1/50"],
    "untagged_ports": ["1/1/3", "1/1/4"],
    "voice": false
  }
]
```

### MAC Table Response

```json
[
  {
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "vlan_id": 100,
    "port": "1/1/3",
    "type": "dynamic",
    "age": 300
  },
  {
    "mac_address": "11:22:33:44:55:66",
    "vlan_id": 100,
    "port": "1/1/4",
    "type": "dynamic",
    "age": 120
  }
]
```

### VLAN Create Response

```json
{
  "success": true,
  "message": "VLAN 200 created",
  "vlan": {
    "id": 200,
    "name": "Guest_Network"
  }
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | Invalid credentials | Verify username/password in ARUBA_CX_TARGETS |
| CONN_TIMEOUT | Switch unreachable | Check network connectivity |
| VLAN_NOT_FOUND | VLAN doesn't exist | Verify VLAN ID is configured |
| VLAN_EXISTS | VLAN already exists | Use configure_vlan to modify existing VLAN |
| MAC_NOT_FOUND | MAC not in table | MAC may have aged out or device disconnected |
| CR_REQUIRED | ITSM CR required | Provide cr_number parameter when ITSM_ENABLED |
| CR_INVALID | CR validation failed | Verify CR format (CHG0001234) and status |
| WRITE_FAILED | Configuration failed | Check switch connectivity and permissions |

## Notes

- Read operations (get_vlans, get_mac_table): No ITSM gating required
- Write operations: Require ServiceNow CR when ITSM_ENABLED=true
- Lab mode (ITSM_LAB_MODE=true): Validates CR format without ServiceNow call
- MAC addresses use format: aa:bb:cc:dd:ee:ff
- VLAN IDs: 1-4094 (1 is typically reserved for default)
- All operations logged to GAIT audit trail
