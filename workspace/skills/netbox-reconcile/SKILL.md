---
name: netbox-reconcile
description: "Reconcile NetBox source of truth against live network state - detect IP drift, missing interfaces, undocumented links, cable mismatches, VLAN mismatches, and ticket discrepancies in ServiceNow"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["NETBOX_MCP_SCRIPT", "PYATS_TESTBED_PATH"] } } }
---

# NetBox Reconciliation

Compare NetBox (source of truth) intent against live device state collected via pyATS. Identify discrepancies, classify them by type and severity, and ticket critical findings in ServiceNow.

## Golden Rule

**NetBox is READ-ONLY.** Discrepancies are reported and ticketed. They are NEVER auto-corrected. NetBox is the intended state. If reality differs from NetBox, either the network is wrong or NetBox needs a human to update it. NetClaw does not make that decision.

## How to Call the Tools

### NetBox MCP Server

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

### pyATS MCP Server (for live device state)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## NetBox Tools Reference

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `netbox_get_objects` | Bulk query objects by type | `object_type`, `filters` (dict), `limit`, `brief` |
| `netbox_get_object_by_id` | Get single object by ID | `object_type`, `object_id` |
| `netbox_search_objects` | Global text search | `query`, `object_types` |
| `netbox_get_changelogs` | Audit trail of NetBox changes | `filters` |

### Object Types

| Object Type | Contains |
|-------------|----------|
| `dcim.devices` | Devices: name, role, platform, site, status |
| `dcim.interfaces` | Interfaces: name, type, enabled, MAC, MTU, mode (access/tagged), untagged_vlan, tagged_vlans |
| `ipam.ip-addresses` | IP addresses: address (CIDR), assigned_object, status, role |
| `dcim.cables` | Physical cables: A-side termination, B-side termination, type, length |
| `ipam.vlans` | VLANs: vid, name, site, tenant, status |
| `ipam.prefixes` | Prefixes: prefix (CIDR), VRF, site, status |
| `dcim.sites` | Sites: name, region, physical_address |

---

## Discrepancy Types

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| `IP_DRIFT` | IP Address Drift | CRITICAL | Device IP differs from NetBox assignment |
| `MISSING_INTERFACE` | Missing Interface | HIGH | Interface exists in NetBox but not on device (or vice versa) |
| `UNDOCUMENTED_LINK` | Undocumented Link | HIGH | CDP/LLDP shows a neighbor connection not documented in NetBox cables |
| `CABLE_MISMATCH` | Cable Mismatch | HIGH | NetBox cable endpoints do not match CDP/LLDP neighbor data |
| `VLAN_MISMATCH` | VLAN Mismatch | MEDIUM | Device VLAN assignment differs from NetBox |
| `STATUS_MISMATCH` | Interface Status Mismatch | MEDIUM | NetBox shows enabled but device shows down (or vice versa) |
| `MTU_MISMATCH` | MTU Mismatch | LOW | Device MTU differs from NetBox interface MTU |

Severity order: CRITICAL > HIGH > MEDIUM > LOW

---

## Full Reconciliation Workflow

### Step 1: Collect NetBox Intent

#### 1A: Get Device Inventory from NetBox

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.devices","filters":{"status":"active"},"brief":true}'
```

This returns all active devices. Match against the pyATS testbed to determine which devices can be reconciled.

#### 1B: Get Interfaces from NetBox (per device)

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.interfaces","filters":{"device":"R1"}}'
```

**Extract per interface:**
- Name, type, enabled status
- MTU, MAC address
- Mode (access/tagged), untagged VLAN, tagged VLANs
- Description, label

#### 1C: Get IP Addresses from NetBox (per device)

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"ipam.ip-addresses","filters":{"device":"R1"}}'
```

**Extract per IP:**
- Address (CIDR notation)
- Assigned interface
- Status (active, reserved, deprecated)
- Role (primary, secondary, loopback, VIP)

#### 1D: Get Cables from NetBox (per device)

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.cables","filters":{"device":"R1"}}'
```

**Extract per cable:**
- A-side: device, interface
- B-side: device, interface
- Cable type, length, color

#### 1E: Get VLANs from NetBox

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"ipam.vlans","filters":{"site":"main-site"}}'
```

### Step 2: Collect Live Device State

#### 2A: Get Interfaces from Device

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip interface brief"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show interfaces"}'
```

**Extract per interface:**
- Name, admin status (up/down), protocol status (up/down)
- IP address, subnet mask
- MTU, speed, duplex
- Description

#### 2B: Get IP Addresses from Device

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip interface"}'
```

**Extract per interface:**
- Primary IP address and mask
- Secondary IP addresses (if any)

#### 2C: Get Neighbor Data from Device

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show cdp neighbors detail"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show lldp neighbors detail"}'
```

**Extract per neighbor:**
- Local interface -> Remote device, remote interface
- Remote platform, remote IP

#### 2D: Get VLAN Data from Device

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show vlan brief"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show interfaces switchport"}'
```

### Step 3: Diff Engine

Compare NetBox intent vs device reality for each discrepancy type.

#### 3A: IP_DRIFT Detection

For each interface with an IP in NetBox:

```
NetBox:  GigabitEthernet1 -> 10.1.1.1/30
Device:  GigabitEthernet1 -> 10.1.1.5/30
Result:  IP_DRIFT (CRITICAL) - GigabitEthernet1: NetBox=10.1.1.1/30, Device=10.1.1.5/30
```

**Comparison logic:**
1. Get all IPs from NetBox for device R1 (Step 1C)
2. Get all IPs from device R1 (Step 2B)
3. For each NetBox IP assignment:
   - Find the matching interface on the device
   - Compare the IP address and prefix length
   - If different -> IP_DRIFT (CRITICAL)
   - If interface exists but has no IP -> IP_DRIFT (CRITICAL)
4. For each device IP not in NetBox -> IP_DRIFT (CRITICAL) - undocumented IP

#### 3B: MISSING_INTERFACE Detection

```
NetBox:  GigabitEthernet3 (enabled)
Device:  GigabitEthernet3 does not exist
Result:  MISSING_INTERFACE (HIGH) - GigabitEthernet3 exists in NetBox but not on device
```

**Comparison logic:**
1. Get interface list from NetBox (Step 1B)
2. Get interface list from device (Step 2A)
3. For each NetBox interface not found on device -> MISSING_INTERFACE (HIGH)
4. For each device interface not found in NetBox -> MISSING_INTERFACE (HIGH) with note "undocumented"
5. Filter out virtual/internal interfaces that are platform-specific (Null0, NVI0, etc.)

#### 3C: UNDOCUMENTED_LINK Detection

```
CDP:     R1:GigabitEthernet2 -> SW1:GigabitEthernet0/1
NetBox:  No cable record for R1:GigabitEthernet2
Result:  UNDOCUMENTED_LINK (HIGH) - R1:Gi2 -> SW1:Gi0/1 discovered via CDP but not in NetBox
```

**Comparison logic:**
1. Get CDP/LLDP neighbors from device (Step 2C)
2. Get cable records from NetBox (Step 1D)
3. For each CDP/LLDP neighbor:
   - Search NetBox cables for a matching A-side/B-side pair
   - If no cable exists -> UNDOCUMENTED_LINK (HIGH)

#### 3D: CABLE_MISMATCH Detection

```
NetBox:  R1:GigabitEthernet1 -> R2:GigabitEthernet1
CDP:     R1:GigabitEthernet1 -> R3:GigabitEthernet0
Result:  CABLE_MISMATCH (HIGH) - R1:Gi1 NetBox says R2:Gi1 but CDP says R3:Gi0
```

**Comparison logic:**
1. For each NetBox cable involving this device:
   - Look up the corresponding CDP/LLDP entry for the local interface
   - Compare the remote device and remote interface
   - If different -> CABLE_MISMATCH (HIGH)

#### 3E: VLAN_MISMATCH Detection

```
NetBox:  GigabitEthernet2 untagged_vlan=10
Device:  GigabitEthernet2 access vlan 20
Result:  VLAN_MISMATCH (MEDIUM) - GigabitEthernet2: NetBox VLAN=10, Device VLAN=20
```

**Comparison logic:**
1. Get interface VLAN assignments from NetBox (Step 1B, look at untagged_vlan and tagged_vlans)
2. Get interface switchport data from device (Step 2D)
3. Compare access VLAN, trunk allowed VLANs, and native VLAN
4. If different -> VLAN_MISMATCH (MEDIUM)

#### 3F: STATUS_MISMATCH Detection

```
NetBox:  GigabitEthernet3 enabled=true
Device:  GigabitEthernet3 administratively down
Result:  STATUS_MISMATCH (MEDIUM) - GigabitEthernet3: NetBox=enabled, Device=admin-down
```

#### 3G: MTU_MISMATCH Detection

```
NetBox:  GigabitEthernet1 MTU=9000
Device:  GigabitEthernet1 MTU=1500
Result:  MTU_MISMATCH (LOW) - GigabitEthernet1: NetBox MTU=9000, Device MTU=1500
```

### Step 4: Generate Reconciliation Report

Produce a severity-sorted discrepancy table:

```
NetBox Reconciliation Report - R1
Date: YYYY-MM-DD HH:MM UTC
NetBox Device: R1 | pyATS Device: R1 (devnetsandboxiosxec8k.cisco.com)

CRITICAL:
  [C-001] IP_DRIFT: GigabitEthernet1 - NetBox=10.1.1.1/30, Device=10.1.1.5/30
  [C-002] IP_DRIFT: Loopback0 - NetBox=1.1.1.1/32, Device=2.2.2.2/32

HIGH:
  [H-001] UNDOCUMENTED_LINK: Gi2 -> SW1:Gi0/1 (CDP) - no cable in NetBox
  [H-002] MISSING_INTERFACE: GigabitEthernet4 in NetBox but not on device

MEDIUM:
  [M-001] VLAN_MISMATCH: Gi3 - NetBox VLAN=10, Device VLAN=20
  [M-002] STATUS_MISMATCH: Gi5 - NetBox=enabled, Device=admin-down

LOW:
  [L-001] MTU_MISMATCH: Gi1 - NetBox MTU=9000, Device MTU=1500

Summary: 2 Critical | 2 High | 2 Medium | 1 Low
Overall: CRITICAL - immediate attention required
```

### Step 5: Ticket Critical Discrepancies

For each CRITICAL discrepancy, open a ServiceNow incident:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_incident '{"short_description":"NetBox Drift: IP_DRIFT on R1 GigabitEthernet1","description":"NetBox reconciliation detected IP address drift on R1 GigabitEthernet1.\n\nNetBox intent: 10.1.1.1/30\nDevice reality: 10.1.1.5/30\n\nThis is a CRITICAL discrepancy. Either the device configuration is incorrect and needs remediation, or NetBox needs to be updated to reflect the current state.\n\nDiscovery method: NetClaw automated reconciliation\nDate: YYYY-MM-DD HH:MM UTC","urgency":"2","impact":"2","category":"Network"}'
```

For HIGH discrepancies, create incidents at lower urgency:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_incident '{"short_description":"NetBox Drift: UNDOCUMENTED_LINK R1:Gi2 -> SW1:Gi0/1","description":"NetBox reconciliation found a physical link (via CDP) between R1:GigabitEthernet2 and SW1:GigabitEthernet0/1 that has no cable record in NetBox.\n\nAction required: Add cable record to NetBox or investigate if this link is authorized.\n\nDiscovery method: NetClaw automated reconciliation","urgency":"3","impact":"3","category":"Network"}'
```

### Step 6: Generate Markmap Drift Summary

Create a visual mind map of all discrepancies for human review:

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_generate '{"markdown_content":"# NetBox Reconciliation - R1\n## CRITICAL\n### IP_DRIFT\n- Gi1: NetBox=10.1.1.1/30 vs Device=10.1.1.5/30\n- Lo0: NetBox=1.1.1.1/32 vs Device=2.2.2.2/32\n## HIGH\n### UNDOCUMENTED_LINK\n- Gi2 -> SW1:Gi0/1 (no cable in NetBox)\n### MISSING_INTERFACE\n- Gi4 (in NetBox, not on device)\n## MEDIUM\n### VLAN_MISMATCH\n- Gi3: NetBox VLAN=10 vs Device VLAN=20\n### STATUS_MISMATCH\n- Gi5: NetBox=enabled vs Device=admin-down\n## LOW\n### MTU_MISMATCH\n- Gi1: NetBox=9000 vs Device=1500"}'
```

### Step 7: Record in GAIT

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"user_text":"Reconcile NetBox source of truth against R1 live state","assistant_text":"NetBox reconciliation complete for R1.\n\nDiscrepancies found: 2 CRITICAL, 2 HIGH, 2 MEDIUM, 1 LOW\n\nCRITICAL:\n- IP_DRIFT: Gi1 (10.1.1.1/30 vs 10.1.1.5/30)\n- IP_DRIFT: Lo0 (1.1.1.1/32 vs 2.2.2.2/32)\n\nServiceNow incidents created for all CRITICAL and HIGH findings.\nMarkmap drift summary generated.\n\nOverall: CRITICAL - immediate human review required."}'
```

Display the audit trail:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_show '{"commit":"HEAD"}'
```

---

## Fleet-Wide Reconciliation

To reconcile all devices, first list the inventory:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_list_devices '{}'
```

Then query NetBox for all active devices:

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.devices","filters":{"status":"active"},"brief":true}'
```

Run Steps 1-7 for each device that exists in both the pyATS testbed and NetBox. Produce a fleet summary:

```
Fleet Reconciliation Summary - YYYY-MM-DD
Devices Reconciled: 5/5

+---------+----------+------+--------+-----+----------+
| Device  | CRITICAL | HIGH | MEDIUM | LOW | Overall  |
+---------+----------+------+--------+-----+----------+
| R1      | 2        | 2    | 2      | 1   | CRITICAL |
| R2      | 0        | 1    | 0      | 0   | HIGH     |
| SW1     | 0        | 0    | 3      | 2   | MEDIUM   |
| SW2     | 0        | 0    | 0      | 1   | LOW      |
| FW1     | 0        | 0    | 0      | 0   | CLEAN    |
+---------+----------+------+--------+-----+----------+

Total Discrepancies: 2 CRITICAL | 3 HIGH | 5 MEDIUM | 4 LOW
ServiceNow Incidents Created: 5 (2 CRITICAL + 3 HIGH)
Overall Fleet Status: CRITICAL
```

Sort devices by severity (CRITICAL first) for triage prioritization.

---

## NetBox Changelog Audit

After reconciliation, check NetBox changelogs to understand when the source of truth was last updated:

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_changelogs '{"filters":{"object_type":"dcim.interface","limit":20}}'
```

This helps determine whether discrepancies are due to recent device changes (device drifted) or stale NetBox data (NetBox was never updated).

---

## Integration with Other Skills

| Skill | Integration Point |
|-------|------------------|
| **pyats-topology** | Provides CDP/LLDP neighbor data used for UNDOCUMENTED_LINK and CABLE_MISMATCH detection |
| **pyats-health-check** | Run health check first; reconciliation adds NetBox cross-reference layer |
| **servicenow-change-workflow** | CRITICAL and HIGH discrepancies auto-open ServiceNow incidents |
| **markmap-viz** | Drift summary mind map for visual human review |
| **drawio-diagram** | Color-code topology links by reconciliation status (green=match, red=mismatch, yellow=undocumented) |
| **GAIT** | Full reconciliation session recorded in audit trail |

## When to Use

- **Scheduled**: Weekly or monthly source-of-truth validation
- **Post-change**: After every configuration change, verify NetBox still matches reality
- **Incident response**: When investigating an outage, check if NetBox data is accurate for the affected devices
- **New device onboarding**: Verify NetBox was populated correctly after adding a new device
- **Audit/compliance**: Demonstrate that infrastructure documentation matches reality
