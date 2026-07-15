---
name: aruba-cx-interfaces
description: "Monitor Aruba CX switch interface status, LLDP neighbors, and optical transceiver health"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["ARUBA_CX_TARGETS"]
---

# Aruba CX Interface Monitoring

Monitor HPE Aruba CX switch interface status, LLDP neighbor relationships, and optical transceiver health (DOM diagnostics). Essential for troubleshooting connectivity issues and monitoring link quality.

## When to Use

- Checking interface admin/operational status
- Troubleshooting port connectivity issues
- Discovering LLDP neighbors for topology mapping
- Monitoring optical transceiver health (TX/RX power, temperature)
- Identifying threshold violations on optics
- Verifying interface descriptions and speeds

## MCP Server

- **Server**: `aruba-cx-mcp` (community MCP from slientnight)
- **Command**: `python3 -u mcp-servers/aruba-cx-mcp/aruba_cx_mcp_server.py` (stdio transport)
- **Auth**: REST API via `ARUBA_CX_TARGETS` (JSON array) or `ARUBA_CX_CONFIG` (file path)
- **Timeout**: `ARUBA_CX_TIMEOUT` (default: 30 seconds)

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_interfaces` | target, interface? | Get interface status (admin, oper, speed, description) |
| `get_lldp_neighbors` | target, interface? | Get LLDP neighbor information (device, port, capabilities) |
| `get_dom_diagnostics` | target, interface? | Get optical transceiver health with threshold alerts |

## Workflow Examples

### Interface Status Monitoring

```bash
# View all interfaces
"Show all interfaces on core-sw-1"

# Check specific interface
"What's the status of interface 1/1/1 on core-sw-1?"

# Find down interfaces
"Which interfaces are down on core-sw-1?"

# Check interface speeds
"Show me the interface speeds on core-sw-1"

# View interface descriptions
"What are the interface descriptions on core-sw-1?"
```

### LLDP Neighbor Discovery

```bash
# View all LLDP neighbors
"Show LLDP neighbors on core-sw-1"

# Check specific port neighbors
"What device is connected to port 1/1/49 on core-sw-1?"

# Discover upstream devices
"What are the LLDP neighbors for the uplink ports?"

# Map topology
"Show me all connected devices on core-sw-1"
```

### Optical Transceiver Health

```bash
# View all optics health
"Show optical transceiver health for core-sw-1"

# Check specific port DOM
"What are the DOM readings for port 1/1/49?"

# Find threshold violations
"Are there any optical threshold warnings on core-sw-1?"

# Monitor TX/RX power
"Show the TX and RX power levels for all optics on core-sw-1"

# Check transceiver temperature
"What's the temperature of the transceivers on core-sw-1?"
```

## Integration with Other Skills

- **aruba-cx-system**: First discover switches, then check their interfaces
- **aruba-cx-switching**: View VLANs assigned to interfaces
- **aruba-cx-config**: Review interface configuration details

## Response Examples

### Interface List Response

```json
[
  {
    "name": "1/1/1",
    "admin_state": "up",
    "oper_state": "up",
    "speed": "10G",
    "description": "Uplink to spine-1",
    "mtu": 9198,
    "type": "ethernet"
  },
  {
    "name": "1/1/2",
    "admin_state": "up",
    "oper_state": "down",
    "speed": "10G",
    "description": "Server port",
    "mtu": 9198,
    "type": "ethernet"
  }
]
```

### LLDP Neighbors Response

```json
[
  {
    "local_port": "1/1/49",
    "remote_chassis_id": "aa:bb:cc:dd:ee:ff",
    "remote_port_id": "Ethernet1",
    "remote_system_name": "spine-1",
    "remote_system_description": "Aruba 8325",
    "remote_capabilities": ["bridge", "router"]
  }
]
```

### DOM Diagnostics Response

```json
[
  {
    "interface": "1/1/49",
    "temperature": 35.5,
    "temperature_status": "normal",
    "tx_power": -2.5,
    "tx_power_status": "normal",
    "rx_power": -3.1,
    "rx_power_status": "normal",
    "voltage": 3.3,
    "vendor": "Aruba",
    "part_number": "JL484A"
  },
  {
    "interface": "1/1/50",
    "temperature": 42.1,
    "temperature_status": "warning",
    "tx_power": -2.8,
    "tx_power_status": "normal",
    "rx_power": -15.2,
    "rx_power_status": "alarm",
    "voltage": 3.3,
    "vendor": "Aruba",
    "part_number": "JL484A"
  }
]
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | Invalid credentials | Verify username/password in ARUBA_CX_TARGETS |
| CONN_TIMEOUT | Switch unreachable | Check network connectivity and ARUBA_CX_TIMEOUT |
| INTERFACE_NOT_FOUND | Unknown interface | Verify interface name format (e.g., 1/1/1) |
| NO_DOM_SUPPORT | Port not optical | DOM diagnostics only available on optical transceiver ports |
| NO_LLDP_NEIGHBORS | No LLDP data | Verify LLDP is enabled and neighbors support LLDP |

## Notes

- Read-only operations - no ServiceNow CR gating required
- All operations logged to GAIT audit trail
- DOM diagnostics only available on optical transceiver ports
- Threshold status values: normal, warning, alarm
- LLDP must be enabled on both local and remote devices
- Interface names follow format: member/module/port (e.g., 1/1/1)
