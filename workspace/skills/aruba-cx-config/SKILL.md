---
name: aruba-cx-config
description: "View and manage Aruba CX switch configurations, perform ISSU upgrades, and firmware operations"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["ARUBA_CX_TARGETS"]
---

# Aruba CX Configuration Management

View running and startup configurations, save configuration changes, and perform In-Service Software Upgrades (ISSU) on HPE Aruba CX switches. Write operations require ITSM approval for production environments.

## When to Use

- Viewing running or startup configurations
- Comparing running vs startup config (unsaved changes)
- Saving running configuration to startup
- Checking routing table entries
- Viewing ISSU upgrade status
- Performing software upgrades with minimal disruption
- Managing firmware images

## MCP Server

- **Server**: `aruba-cx-mcp` (community MCP from slientnight)
- **Command**: `python3 -u mcp-servers/aruba-cx-mcp/aruba_cx_mcp_server.py` (stdio transport)
- **Auth**: REST API via `ARUBA_CX_TARGETS` (JSON array) or `ARUBA_CX_CONFIG` (file path)
- **ITSM**: Write operations require CR when `ITSM_ENABLED=true`

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_running_config` | target, section? | Get current active configuration |
| `get_startup_config` | target | Get saved startup configuration |
| `get_routing_table` | target, vrf? | Get IP routing table entries |
| `get_issu_status` | target | Get ISSU upgrade status |
| `save_config` | target, cr_number? | Save running config to startup (ITSM-gated) |
| `issu_upgrade` | target, image, cr_number? | Initiate ISSU upgrade (ITSM-gated) |
| `upload_firmware` | target, source, destination, cr_number? | Upload firmware image (ITSM-gated) |
| `download_firmware` | target, source, destination, cr_number? | Download firmware from switch (ITSM-gated) |

## Workflow Examples

### Configuration Viewing

```bash
# View running config
"Show the running configuration for core-sw-1"

# View specific section
"Show the interface configuration for core-sw-1"

# View startup config
"Show the startup configuration for core-sw-1"

# Compare configs
"Are there unsaved changes on core-sw-1?"
```

### Routing Table

```bash
# View routing table
"Show the routing table for core-sw-1"

# Check specific VRF
"Show routes in VRF management on core-sw-1"

# Find default route
"What's the default gateway on core-sw-1?"
```

### Configuration Save (ITSM-Gated)

```bash
# Save configuration (requires CR when ITSM enabled)
"Save the running configuration on core-sw-1 with CR CHG0001234"

# Verify save
"Is the configuration saved on core-sw-1?"
```

### ISSU Operations (ITSM-Gated)

```bash
# Check ISSU status
"What's the ISSU status on core-sw-1?"

# Check if upgrade in progress
"Is there an upgrade running on core-sw-1?"

# Initiate ISSU upgrade (requires CR)
"Upgrade core-sw-1 to firmware 10.14.1000 with CR CHG0001234"

# Monitor upgrade progress
"What's the ISSU progress on core-sw-1?"
```

### Firmware Management (ITSM-Gated)

```bash
# Upload firmware image
"Upload firmware from tftp://10.1.1.100/AOS-CX_10.14.1000.swi to core-sw-1 with CR CHG0001234"

# Download firmware backup
"Download the current firmware from core-sw-1 to backup location with CR CHG0001234"

# Check firmware images
"What firmware images are on core-sw-1?"
```

## ITSM Integration

Write operations require change management approval:

| Environment Variable | Behavior |
|---------------------|----------|
| `ITSM_ENABLED=false` | Write operations proceed without CR validation |
| `ITSM_ENABLED=true` | Write operations require valid ServiceNow CR number |
| `ITSM_LAB_MODE=true` | CR format validated but not checked against ServiceNow |

**CR Format**: Must match ServiceNow pattern (e.g., CHG0001234)

**ITSM-Gated Operations**:
- `save_config` - Saving running config to startup
- `issu_upgrade` - Initiating software upgrade
- `upload_firmware` - Uploading firmware images
- `download_firmware` - Downloading firmware images

## Integration with Other Skills

- **aruba-cx-system**: Check firmware versions before upgrade
- **aruba-cx-interfaces**: Verify interface config in running config
- **aruba-cx-switching**: Review VLAN configuration in running config

## Response Examples

### Running Config Response

```json
{
  "type": "running",
  "content": "hostname core-sw-1\n!\nvlan 1\nvlan 100\n  name Management\n...",
  "checksum": "abc123",
  "last_modified": "2026-04-08T10:00:00Z"
}
```

### Routing Table Response

```json
[
  {
    "destination": "0.0.0.0/0",
    "next_hop": "10.1.1.1",
    "interface": "vlan100",
    "protocol": "static",
    "metric": 1,
    "admin_distance": 1
  },
  {
    "destination": "10.0.0.0/8",
    "next_hop": "10.1.1.2",
    "interface": "vlan200",
    "protocol": "ospf",
    "metric": 100,
    "admin_distance": 110
  }
]
```

### ISSU Status Response

```json
{
  "state": "idle",
  "progress": 0,
  "target_version": null,
  "start_time": null,
  "error_message": null
}
```

### ISSU In-Progress Response

```json
{
  "state": "upgrading",
  "progress": 65,
  "target_version": "10.14.1000",
  "start_time": "2026-04-08T14:00:00Z",
  "error_message": null
}
```

### Save Config Response

```json
{
  "success": true,
  "message": "Configuration saved",
  "checksum": "def456"
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | Invalid credentials | Verify username/password in ARUBA_CX_TARGETS |
| CONN_TIMEOUT | Switch unreachable | Check network connectivity |
| CR_REQUIRED | ITSM CR required | Provide cr_number parameter when ITSM_ENABLED |
| CR_INVALID | CR validation failed | Verify CR format (CHG0001234) and status |
| SAVE_FAILED | Config save failed | Check switch storage and permissions |
| ISSU_NOT_SUPPORTED | Switch not ISSU capable | Use traditional upgrade method |
| ISSU_IN_PROGRESS | Upgrade already running | Wait for current upgrade to complete |
| ISSU_FAILED | Upgrade failed | Check error_message in ISSU status |
| FIRMWARE_NOT_FOUND | Firmware image not found | Verify source path/URL |
| TRANSFER_FAILED | Firmware transfer failed | Check network connectivity and storage |

## ISSU State Machine

```
idle → downloading (firmware download started)
downloading → staging (image validated)
staging → upgrading (ISSU in progress)
upgrading → complete (success)
upgrading → failed (error occurred)
failed → idle (error cleared)
complete → idle (upgrade finished)
```

## Notes

- Read operations (get_running_config, get_startup_config, get_routing_table, get_issu_status): No ITSM gating
- Write operations: Require ServiceNow CR when ITSM_ENABLED=true
- Lab mode (ITSM_LAB_MODE=true): Validates CR format without ServiceNow call
- ISSU upgrades minimize traffic disruption but may take 15-30 minutes
- Always verify firmware compatibility before ISSU
- Configuration changes should be saved after successful verification
- All operations logged to GAIT audit trail
