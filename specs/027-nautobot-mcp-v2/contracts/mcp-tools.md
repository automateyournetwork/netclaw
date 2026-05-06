# MCP Tool Contracts: Enhanced Nautobot MCP Server v2

**Feature**: 027-nautobot-mcp-v2
**Date**: 2026-04-09
**Transport**: stdio
**Nautobot Version**: 3.1.0 (graphene_django 3.2.3, no GraphQL mutations)

## Read Tools (7) — GraphQL API

### nautobot_get_devices

**Description**: Query devices from Nautobot source of truth. Returns device inventory with role, platform, location, status, primary IP, and serial number. Uses GraphQL for efficient nested queries.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | Filter by device name (exact match) |
| location | string | No | Filter by location name |
| role | string | No | Filter by device role name |
| platform | string | No | Filter by platform name |
| status | string | No | Filter by status name (e.g., "Active") |
| q | string | No | General search across device fields |
| limit | integer | No | Max results (default: 50, max: 200) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with device list including name, status, role, platform, location, primary_ip4, serial, and device_type.

**Example invocations**:
- All devices: `nautobot_get_devices()`
- By name: `nautobot_get_devices(name="HomeSwitch01")`
- By location: `nautobot_get_devices(location="House")`
- Search: `nautobot_get_devices(q="switch")`

---

### nautobot_get_interfaces

**Description**: Query interfaces from Nautobot with full detail including VLAN assignments, IP addresses, and cable peer. Uses GraphQL for efficient nested relationship queries.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| device | string | No | Filter by device name |
| name | string | No | Filter by interface name |
| type | string | No | Filter by interface type |
| enabled | boolean | No | Filter by enabled state |
| status | string | No | Filter by status name |
| has_ip_addresses | boolean | No | Filter to interfaces with/without IPs |
| limit | integer | No | Max results (default: 50, max: 500) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with interface list including name, type, enabled, status, description, mac_address, mtu, mode, untagged_vlan, tagged_vlans, ip_addresses, device name, and connected_endpoint.

**Example invocations**:
- All interfaces on a device: `nautobot_get_interfaces(device="HomeSwitch01")`
- Only interfaces with IPs: `nautobot_get_interfaces(device="HomeSwitch01", has_ip_addresses=true)`
- Disabled interfaces: `nautobot_get_interfaces(device="HomeSwitch01", enabled=false)`

---

### nautobot_get_vlans

**Description**: Query VLANs from Nautobot. Returns VLAN ID, name, status, locations, and group.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| vid | integer | No | Filter by VLAN ID |
| name | string | No | Filter by VLAN name |
| location | string | No | Filter by location name |
| vlan_group | string | No | Filter by VLAN group name |
| status | string | No | Filter by status name |
| limit | integer | No | Max results (default: 100, max: 500) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with VLAN list including vid, name, status, locations, vlan_group, tenant, and role.

**Example invocations**:
- All VLANs: `nautobot_get_vlans()`
- By VID: `nautobot_get_vlans(vid=100)`
- By location: `nautobot_get_vlans(location="House")`

---

### nautobot_get_prefixes

**Description**: Query IP prefixes from Nautobot IPAM. Returns prefix, status, locations, and role.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| prefix | string | No | Filter by prefix (e.g., "192.168.3.0/24") |
| status | string | No | Filter by status name |
| location | string | No | Filter by location name |
| tenant | string | No | Filter by tenant name |
| limit | integer | No | Max results (default: 50, max: 200) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with prefix list including prefix, status, locations, role, tenant, and description.

**Example invocations**:
- All prefixes: `nautobot_get_prefixes()`
- By prefix: `nautobot_get_prefixes(prefix="192.168.3.0/24")`

---

### nautobot_get_ip_addresses

**Description**: Query IP addresses from Nautobot IPAM. Returns address, status, assigned interface, and device.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| address | string | No | Filter by IP address (e.g., "192.168.3.2/24") |
| device | string | No | Filter by device name (via interface assignment) |
| interface | string | No | Filter by interface name |
| status | string | No | Filter by status name |
| q | string | No | General search |
| limit | integer | No | Max results (default: 50, max: 500) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with IP address list including address, status, dns_name, description, tenant, and parent interface/device.

**Example invocations**:
- All IPs: `nautobot_get_ip_addresses()`
- By device: `nautobot_get_ip_addresses(device="HomeSwitch01")`
- Search: `nautobot_get_ip_addresses(q="192.168.3")`

---

### nautobot_get_cables

**Description**: Query cables from Nautobot. Returns cable endpoints, type, status, and label. Resolves termination UUIDs to human-readable device + interface names.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| device | string | No | Filter cables connected to this device |
| status | string | No | Filter by status name |
| limit | integer | No | Max results (default: 50, max: 200) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with cable list including id, type, status, label, color, and resolved termination_a/termination_b (device name + interface name).

**Example invocations**:
- All cables: `nautobot_get_cables()`
- By device: `nautobot_get_cables(device="HomeSwitch01")`

---

### nautobot_graphql

**Description**: Execute an arbitrary GraphQL query against Nautobot. Use for advanced queries, plugin data (BGP models, golden config, firewall models), custom fields, or any data not covered by the structured tools. Read-only — Nautobot 3.1.0 has no GraphQL mutations.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | GraphQL query string |
| variables | string | No | JSON string of GraphQL variables |

**Returns**: Raw GraphQL response data as JSON.

**Example invocations**:
- Plugin query: `nautobot_graphql(query="{ bgp_routing_instances { device { name } router_id autonomous_system { asn } } }")`
- With variables: `nautobot_graphql(query="query($name: String) { devices(name: $name) { name serial } }", variables="{\"name\": \"HomeSwitch01\"}")`

---

## Write Tools (5) — REST API

> **ITSM Gating**: All write tools require ServiceNow CR approval when ITSM_ENABLED=true and ITSM_LAB_MODE is not true.

### nautobot_create_ip_address

**Description**: Create an IP address in Nautobot IPAM via REST API. Optionally assign to an interface. Resolves names to UUIDs automatically.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| address | string | Yes | IP address with prefix length (e.g., "10.0.1.50/24") |
| status | string | No | Status name (default: "Active") |
| device | string | No | Device name to assign IP to (requires interface) |
| interface | string | No | Interface name to assign IP to (requires device) |
| dns_name | string | No | DNS hostname |
| description | string | No | Description |
| tenant | string | No | Tenant name |
| namespace | string | No | IPAM namespace (default: "Global") |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with created IP address details including Nautobot ID.

---

### nautobot_create_vlan

**Description**: Create a VLAN in Nautobot via REST API. Resolves location and status names to UUIDs automatically.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| vid | integer | Yes | VLAN ID (1-4094) |
| name | string | Yes | VLAN name |
| status | string | No | Status name (default: "Active") |
| location | string | No | Location name to associate |
| vlan_group | string | No | VLAN group name |
| tenant | string | No | Tenant name |
| description | string | No | Description |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with created VLAN details including Nautobot ID.

---

### nautobot_create_prefix

**Description**: Create a prefix in Nautobot IPAM via REST API.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| prefix | string | Yes | Network prefix (e.g., "10.0.1.0/24") |
| status | string | No | Status name (default: "Active") |
| location | string | No | Location name |
| tenant | string | No | Tenant name |
| namespace | string | No | IPAM namespace (default: "Global") |
| description | string | No | Description |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with created prefix details including Nautobot ID.

---

### nautobot_update_object

**Description**: Update any Nautobot object (device, interface, IP, VLAN, prefix, cable) via REST API PATCH. Resolves the object by type + name/identifier, then applies partial updates.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| object_type | string | Yes | Object type: "device", "interface", "ip_address", "vlan", "prefix", "cable" |
| identifier | string | Yes | Object identifier — device name, interface "device:interface_name", IP address, VLAN "vid", prefix, or cable UUID |
| updates | string | Yes | JSON string of fields to update (e.g., '{"description": "new desc", "enabled": false}') |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with updated object showing old and new values for changed fields.

**Example invocations**:
- Update interface: `nautobot_update_object(object_type="interface", identifier="HomeSwitch01:GigabitEthernet1/0/4", updates='{"description": "Server port", "enabled": true}')`
- Update VLAN: `nautobot_update_object(object_type="vlan", identifier="100", updates='{"name": "server_net"}')`

---

### nautobot_reconcile

**Description**: Compare live device state against Nautobot source of truth and produce a structured diff report. Accepts live interface data (from pyATS) as JSON input, queries Nautobot internally for the SoT state, and returns categorized differences.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| device_name | string | Yes | Device name in Nautobot to reconcile against |
| live_interfaces | string | Yes | JSON string of live interface data from pyATS. Expected format: array of objects with keys: name, enabled, description, ip_addresses (array of strings), mtu, type |

**Returns**: JSON diff report with sections:
- `matches` — interfaces present in both with identical fields
- `mismatches` — interfaces present in both with field-level differences (showing nautobot vs live values)
- `device_only` — interfaces on live device but not in Nautobot
- `nautobot_only` — interfaces in Nautobot but not on live device
- `summary` — counts for each category

**Example invocation**:
```
nautobot_reconcile(
  device_name="HomeSwitch01",
  live_interfaces='[{"name": "GigabitEthernet1/0/1", "enabled": true, "description": "Server port", "ip_addresses": [], "mtu": 9198}]'
)
```

---

## Connection Test Tool (1)

### nautobot_test_connection

**Description**: Test connectivity to the Nautobot API. Verifies both GraphQL and REST endpoints are reachable and the token is valid.

**Parameters**: None.

**Returns**: JSON with connection status, Nautobot URL, API version, and GraphQL availability.

---

## Virtualization Tools (4) — GraphQL reads + REST writes

### nautobot_get_virtual_machines

**Description**: Query virtual machines from Nautobot. Returns name, cluster, role, status, primary IP, vCPUs, memory, disk, and interfaces.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | No | Filter by VM name |
| cluster | string | No | Filter by cluster name |
| role | string | No | Filter by role name |
| status | string | No | Filter by status name |
| limit | integer | No | Max results (default: 50) |
| offset | integer | No | Pagination offset (default: 0) |

**Returns**: JSON with VM list including name, status, role, cluster, vcpus, memory, disk, primary_ip4, and interfaces with IPs.

**Example invocations**:
- All VMs: `nautobot_get_virtual_machines()`
- By cluster: `nautobot_get_virtual_machines(cluster="Observability")`

---

### nautobot_create_virtual_machine

**Description**: Create a virtual machine in Nautobot. ITSM-gated.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | VM name (e.g., "otel-collector") |
| cluster | string | Yes | Cluster name the VM belongs to |
| role | string | No | Device role name (e.g., "Monitoring") |
| status | string | No | Status name (default: "Active") |
| vcpus | integer | No | Number of virtual CPUs |
| memory | integer | No | Memory in MB |
| disk | integer | No | Disk in GB |
| comments | string | No | Free-text description |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with created VM details including Nautobot ID.

---

### nautobot_create_vm_interface

**Description**: Create a network interface on a virtual machine. ITSM-gated.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| virtual_machine | string | Yes | VM name |
| name | string | Yes | Interface name (e.g., "eth0") |
| enabled | boolean | No | Whether the interface is enabled (default: true) |
| description | string | No | Interface description |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with created VM interface details.

---

### nautobot_assign_ip_to_vm

**Description**: Create an IP address and assign it to a VM interface. Optionally set as the VM's primary IPv4 address. ITSM-gated.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| virtual_machine | string | Yes | VM name |
| interface | string | Yes | VM interface name (e.g., "eth0") |
| address | string | Yes | IP address in CIDR notation (e.g., "192.168.220.200/24") |
| status | string | No | IP status (default: "Active") |
| namespace | string | No | IPAM namespace (default: "Global") |
| set_primary | boolean | No | Set as VM's primary IPv4 (default: true) |
| cr_number | string | Conditional | ServiceNow CR (required if ITSM_ENABLED) |

**Returns**: JSON with IP address, assignment confirmation, and primary status.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| NAUTOBOT_URL | Yes | Nautobot base URL (e.g., https://192.168.3.253) |
| NAUTOBOT_TOKEN | Yes | Nautobot API token with read+write permissions |
| NAUTOBOT_VERIFY_SSL | No | Verify SSL certificates (default: false for self-signed) |
| NAUTOBOT_TIMEOUT | No | Request timeout in seconds (default: 30) |
| ITSM_ENABLED | No | Enable ITSM gating for write operations (default: false) |
| ITSM_LAB_MODE | No | Bypass ITSM gating for lab use (default: true) |

## Error Responses

All tools return structured error messages for:
- **Connection failure**: "Nautobot API unreachable at {url}: {detail}"
- **Authentication failure**: "Nautobot authentication failed. Verify NAUTOBOT_TOKEN is correct."
- **GraphQL error**: "Nautobot GraphQL error: {errors}" (passes through GraphQL error messages)
- **REST write error**: "Nautobot REST API error ({status_code}): {detail}"
- **ITSM blocked**: "Write operation blocked: ITSM is enabled. Provide a cr_number parameter with a valid ServiceNow Change Request number."
- **Not found**: "No {object_type} found matching '{identifier}' in Nautobot." (not treated as error)
- **Timeout**: "Nautobot query timed out after {timeout}s. Try narrowing filters or increasing NAUTOBOT_TIMEOUT."
- **Permission denied**: "Nautobot token does not have write permission. Contact your Nautobot admin."
