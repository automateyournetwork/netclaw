---
name: aruba-cx-system
description: "Discover Aruba CX switch system information, firmware versions, and VSF topology"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["ARUBA_CX_TARGETS"]
---

# Aruba CX System Discovery

Discover HPE Aruba CX switch system information, firmware versions, and VSF (Virtual Switching Framework) topology through natural language. View switch inventory, software versions, and cluster membership.

## When to Use

- Inventorying Aruba CX switches (hostname, model, serial number)
- Checking switch software versions and uptime
- Auditing firmware versions across the switching fabric
- Understanding VSF cluster topology and member roles
- Planning firmware upgrades (ISSU)
- Verifying VSF commander/standby/member assignments

## MCP Server

- **Server**: `aruba-cx-mcp` (community MCP from slientnight)
- **Command**: `python3 -u mcp-servers/aruba-cx-mcp/aruba_cx_mcp_server.py` (stdio transport)
- **Auth**: REST API via `ARUBA_CX_TARGETS` (JSON array) or `ARUBA_CX_CONFIG` (file path)
- **Timeout**: `ARUBA_CX_TIMEOUT` (default: 30 seconds)

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_system_info` | target | Get hostname, model, serial number, software version, uptime |
| `get_firmware_info` | target | Get primary/secondary firmware versions, boot image, ISSU capability |
| `get_vsf_topology` | target | Get VSF cluster members with roles, serial numbers, status |

## Workflow Examples

### System Information Discovery

```bash
# Get system info for a switch
"Show me the system information for core-sw-1"

# Check switch details
"What model is core-sw-1?"

# View software version
"What software version is running on core-sw-1?"

# Check uptime
"How long has core-sw-1 been running?"
```

### Firmware Audit

```bash
# Get firmware versions
"Show the firmware versions for core-sw-1"

# Check primary and secondary images
"What firmware images are on core-sw-1?"

# Verify ISSU capability
"Is core-sw-1 capable of ISSU upgrades?"

# Plan upgrades
"Which switches need firmware upgrades?"
```

### VSF Topology Discovery

```bash
# View VSF cluster
"Show the VSF topology for core-sw-1"

# Check cluster membership
"What switches are in the VSF cluster with core-sw-1?"

# Identify commander
"Which switch is the VSF commander?"

# View member roles
"Show me the VSF member roles and serial numbers"
```

## Integration with Other Skills

- **aruba-cx-interfaces**: After discovering systems, check interface status
- **aruba-cx-switching**: View VLANs configured on discovered switches
- **aruba-cx-config**: Review running configuration on discovered switches

## Response Examples

### System Info Response

```json
{
  "hostname": "core-sw-1",
  "model": "Aruba 6300M",
  "serial_number": "SG1234567890",
  "software_version": "10.13.1000",
  "uptime": 8640000,
  "boot_time": "2026-01-01T00:00:00Z"
}
```

### Firmware Info Response

```json
{
  "primary_version": "10.13.1000",
  "secondary_version": "10.12.0030",
  "boot_image": "primary",
  "issu_capable": true,
  "last_upgrade": "2026-03-01T00:00:00Z"
}
```

### VSF Topology Response

```json
{
  "enabled": true,
  "domain_id": 1,
  "members": [
    {
      "member_id": 1,
      "role": "commander",
      "serial_number": "SG1234567890",
      "model": "6300M",
      "status": "ready",
      "priority": 255
    },
    {
      "member_id": 2,
      "role": "standby",
      "serial_number": "SG0987654321",
      "model": "6300M",
      "status": "ready",
      "priority": 128
    }
  ]
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | Invalid credentials | Verify username/password in ARUBA_CX_TARGETS |
| CONN_TIMEOUT | Switch unreachable | Check network connectivity and ARUBA_CX_TIMEOUT |
| TARGET_NOT_FOUND | Unknown switch name | Verify target name matches ARUBA_CX_TARGETS configuration |
| VSF_NOT_CONFIGURED | VSF not enabled | Switch is standalone - VSF topology not applicable |
| API_VERSION_MISMATCH | Unsupported API version | Update api_version in target config (default: v10.13) |

## Notes

- Read-only operations - no ServiceNow CR gating required
- All operations logged to GAIT audit trail
- Switches must run AOS-CX 10.x or later with REST API enabled
- Default API version is v10.13 - adjust in target config if needed
- VSF topology returns "not configured" for standalone switches
