---
name: catc-inventory
description: "Catalyst Center device inventory and site management - list/filter devices by hostname, IP, platform, family, role, reachability; view site hierarchy; get interface details per device; device reachability monitoring; cross-reference with pyATS"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["CATC_MCP_SCRIPT", "MCP_CALL"] } } }
---

# Catalyst Center Device Inventory and Site Management

Comprehensive device inventory operations through Cisco Catalyst Center (formerly DNA Center). This skill covers device enumeration, filtering, site hierarchy management, interface inspection, reachability monitoring, and inventory reporting.

## Catalyst Center MCP Server

All Catalyst Center tool calls use this invocation pattern:

```
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 -u $CATC_MCP_SCRIPT
```

Variable shorthand used throughout this document:

```
CATC_CMD="CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 -u $CATC_MCP_SCRIPT"
```

## How to Call Tools

Use the `$MCP_CALL` protocol handler to invoke MCP tools:

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" TOOL_NAME 'ARGS_JSON'
```

## When to Use

- Asset inventory audits and device lifecycle management
- Verifying device reachability across the campus or data center
- Site hierarchy reviews before provisioning changes
- Pre-change baseline: confirm which devices are at a given site
- Interface-level capacity planning and port utilization analysis
- Cross-referencing Catalyst Center inventory with pyATS testbed data
- Compliance checks: platform IDs, software versions, device roles

## Available Inventory Tools

### 1. `fetch_devices` -- List and Filter Network Devices

Fetches devices from the `/dna/intent/api/v1/network-device` endpoint with extensive filtering. **NEVER call this tool without at least one filter parameter** -- unfiltered queries can return massive result sets and are blocked by design.

**Parameters (all optional, but at least one required):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `hostname` | `List[str]` | Filter by device hostname(s) |
| `managementIpAddress` | `List[str]` | Filter by management IP(s) |
| `serialNumber` | `List[str]` | Filter by serial number(s) |
| `platformId` | `List[str]` | Filter by platform ID (e.g., `C9300-48UXM`) |
| `family` | `List[str]` | Filter by device family (e.g., `Switches and Hubs`, `Routers`, `Wireless Controller`) |
| `type` | `List[str]` | Filter by device type (e.g., `Cisco Catalyst 9300 Switch`) |
| `role` | `List[str]` | Filter by role: `ACCESS`, `DISTRIBUTION`, `CORE`, `BORDER ROUTER`, `UNKNOWN` |
| `reachabilityStatus` | `List[str]` | Filter by: `Reachable`, `Unreachable` |
| `collectionStatus` | `List[str]` | Filter by: `Managed`, `Partial Collection Failure`, `Could Not Synchronize` |
| `softwareVersion` | `List[str]` | Filter by IOS/NX-OS version string |
| `softwareType` | `List[str]` | Filter by: `IOS-XE`, `NX-OS`, `IOS`, `AireOS` |
| `series` | `List[str]` | Filter by product series (e.g., `Cisco Catalyst 9300 Series Switches`) |
| `locationName` | `List[str]` | Filter by full site path (e.g., `Global/USA/Building1/Floor1`) |
| `associatedWlcIp` | `List[str]` | For APs: filter by WLC management IP |
| `macAddress` | `List[str]` | Filter by device MAC address(es) |
| `id` | `List[str]` | Filter by device UUID(s) |
| `roleSource` | `List[str]` | Filter by role source: `MANUAL`, `AUTO` |
| `offset` | `str` | Starting record for pagination (e.g., `"0"`) |
| `limit` | `str` | Maximum records to return (e.g., `"50"`) |
| `sortBy` | `str` | Attribute to sort by (e.g., `hostname`) |
| `sortOrder` | `str` | `asc` or `desc` |

**Response fields per device:** `id` (UUID), `hostname`, `managementIpAddress`, `macAddress`, `serialNumber`, `platformId`, `softwareVersion`, `softwareType`, `type`, `family`, `series`, `role`, `roleSource`, `reachabilityStatus`, `collectionStatus`, `errorCode`, `locationName`, `location`, `upTime`, `lastUpdated`, `lastUpdateTime`, `associatedWlcIp`, `apManagerInterfaceIp`, and more.

### 2. `fetch_sites` -- List All Sites

Fetches the complete site hierarchy from Catalyst Center. Takes no arguments.

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_sites '{}'
```

**Response fields per site:** `id`, `name`, `parentId`, `siteNameHierarchy` (full path like `Global/USA/NYC/Floor2`), `type` (area, building, floor), `address`, `latitude`, `longitude`.

### 3. `fetch_interfaces` -- Get Interfaces for a Device

Fetches all interfaces for a specific device by its UUID from the `/dna/intent/api/v1/interface/network-device/{device_id}` endpoint.

**Parameters:**
- `device_id` (string, **required**): The UUID of the device (obtained from `fetch_devices` response `id` field)

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"a1b2c3d4-e5f6-7890-abcd-ef1234567890"}'
```

**Response fields per interface:** `id`, `deviceId`, `portName`, `interfaceType`, `adminStatus`, `status` (operStatus), `speed`, `duplex`, `ipv4Address`, `ipv4Mask`, `macAddress`, `mediaType`, `mtu`, `vlanId`, `nativeVlanId`, `description`, `portMode`, `lastUpdated`, and more.

---

## Inventory Workflows

### Workflow 1: Find All Unreachable Devices

Identify devices that Catalyst Center cannot reach -- critical for outage detection.

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"reachabilityStatus":["Unreachable"]}'
```

**Analyze the results:**
- Record each unreachable device: hostname, management IP, platformId, locationName
- Check `lastUpdated` to determine when the device was last seen
- Check `collectionStatus` for additional context (`Could Not Synchronize` vs `Partial Collection Failure`)
- Group by `locationName` to determine if the outage is site-localized

**Escalation:** If multiple devices at the same site are unreachable, this likely indicates a site-wide outage (WAN link, upstream switch, power). Escalate to the site-wide outage triage workflow in the catc-troubleshoot skill.

### Workflow 2: List All Switches

Enumerate all switching devices managed by Catalyst Center.

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Switches and Hubs"]}'
```

**Refine by role:**

```bash
# Access layer switches only
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Switches and Hubs"],"role":["ACCESS"]}'

# Distribution layer switches
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Switches and Hubs"],"role":["DISTRIBUTION"]}'

# Core switches
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Switches and Hubs"],"role":["CORE"]}'
```

**Refine by platform:**

```bash
# All Catalyst 9300 series
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"series":["Cisco Catalyst 9300 Series Switches"]}'

# Specific platform ID
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"platformId":["C9300-48UXM"]}'
```

### Workflow 3: List All Routers

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Routers"]}'
```

### Workflow 4: List Wireless Controllers and Access Points

```bash
# Wireless LAN Controllers
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Wireless Controller"]}'

# Unified Access Points
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Unified AP"]}'

# APs associated with a specific WLC
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"associatedWlcIp":["10.1.100.10"]}'
```

### Workflow 5: Get Interfaces for a Specific Device

This is a two-step process: first find the device to obtain its UUID, then query interfaces.

**Step 1: Find the device**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"hostname":["CORE-SW-01"]}'
```

Extract the `id` field (UUID) from the response.

**Step 2: Fetch interfaces using the UUID**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"a1b2c3d4-e5f6-7890-abcd-ef1234567890"}'
```

**Analyze interface data:**
- Count interfaces by `adminStatus` (UP vs DOWN) and `status` (operationally UP vs DOWN)
- Identify interfaces with `adminStatus=UP` but `status=down` -- these are operationally failed interfaces
- Check `speed` and `duplex` for mismatches
- Identify trunk ports vs access ports via `portMode`
- Calculate port utilization: (used ports / total ports) * 100

### Workflow 6: Site-Based Device Grouping

Build a report of devices organized by site hierarchy.

**Step 1: Retrieve the site hierarchy**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_sites '{}'
```

**Step 2: For each site, retrieve devices at that location**

```bash
# Devices at a specific site
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"locationName":["Global/USA/NYC/Floor2"]}'
```

**Build the report:**

```
Site Inventory Report
=====================
Catalyst Center: $CCC_HOST
Timestamp: YYYY-MM-DD HH:MM UTC

Global/USA/NYC
  Global/USA/NYC/Floor1 (floor)
    +--------------+------------------+-----------+------------+--------+
    | Hostname     | Mgmt IP          | Platform  | SW Version | Status |
    +--------------+------------------+-----------+------------+--------+
    | ACC-SW-01    | 10.1.10.1        | C9300-48U | 17.09.04a  | Reach  |
    | ACC-SW-02    | 10.1.10.2        | C9300-48U | 17.09.04a  | Reach  |
    | AP-NYC-F1-01 | 10.1.10.100      | C9120AXI  | 17.09.04a  | Reach  |
    +--------------+------------------+-----------+------------+--------+

  Global/USA/NYC/Floor2 (floor)
    +--------------+------------------+-----------+------------+--------+
    | Hostname     | Mgmt IP          | Platform  | SW Version | Status |
    +--------------+------------------+-----------+------------+--------+
    | ACC-SW-03    | 10.1.20.1        | C9300-24P | 17.09.04a  | Reach  |
    | AP-NYC-F2-01 | 10.1.20.100      | C9130AXI  | 17.09.04a  | Unrch  |
    +--------------+------------------+-----------+------------+--------+

Total: 5 devices | 4 reachable | 1 unreachable
```

### Workflow 7: Software Version Audit

Identify devices running non-compliant or mixed firmware versions.

```bash
# Find all devices on a specific software version
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"softwareVersion":["17.09.04a"]}'

# Find devices running IOS-XE
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"softwareType":["IOS-XE"]}'
```

**Audit steps:**
1. Query each device family separately (switches, routers, WLCs, APs)
2. Group results by `softwareVersion`
3. Flag devices not on the approved golden image version
4. Report version distribution per platform:

```
Software Version Audit
======================
Platform: Cisco Catalyst 9300 Series Switches
  17.09.04a: 42 devices (APPROVED)
  17.06.05 : 3 devices  (NON-COMPLIANT -- schedule upgrade)
  17.03.04a: 1 device   (EOL VERSION -- immediate upgrade required)

Platform: Cisco Catalyst 9800 Wireless Controller
  17.09.04a: 2 devices (APPROVED)
```

### Workflow 8: Find a Device by Serial Number or IP

```bash
# By serial number
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"serialNumber":["FDO2325A0B1"]}'

# By management IP
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"managementIpAddress":["10.1.10.1"]}'

# By MAC address
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"macAddress":["00:1A:2B:3C:4D:5E"]}'
```

### Workflow 9: Collection Failure Investigation

Devices with collection failures may have partial data in Catalyst Center.

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"collectionStatus":["Partial Collection Failure"]}'
```

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"collectionStatus":["Could Not Synchronize"]}'
```

**Common causes:**
- SNMP community/credential mismatch
- NETCONF/RESTCONF not enabled on the device
- SSH connectivity issue (ACL blocking, timeout)
- Device CPU too high to respond to polling
- Device running an unsupported software version

---

## Cross-Reference: Catalyst Center + pyATS

When the pyATS testbed is available (`$PYATS_MCP_SCRIPT` and `$PYATS_TESTBED_PATH` are set), cross-reference Catalyst Center inventory with live device data for deeper validation.

### Verify Device Software Version

Compare what Catalyst Center reports vs what the device itself reports:

```bash
# Catalyst Center says the device runs 17.09.04a
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"hostname":["CORE-SW-01"]}'

# Verify directly from the device
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"CORE-SW-01","command":"show version"}'
```

**Flag any discrepancy** -- this indicates Catalyst Center inventory is stale and needs a resync.

### Verify Interface State

Compare Catalyst Center interface data vs live device state:

```bash
# Catalyst Center interface data (may be up to 25 minutes stale)
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"<UUID>"}'

# Live interface state from the device
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"CORE-SW-01","command":"show ip interface brief"}'
```

**Identify drift:** Interfaces that show UP in Catalyst Center but DOWN on the live device (or vice versa) indicate a polling lag or inventory desync.

---

## Inventory Report Format

Always produce a consolidated inventory summary when performing audit workflows:

```
Catalyst Center Inventory Report
=================================
Controller: $CCC_HOST
Timestamp: YYYY-MM-DD HH:MM UTC

Device Summary
--------------
Total Devices: 156
  Switches and Hubs: 92 (59%)
  Routers: 12 (8%)
  Wireless Controller: 4 (3%)
  Unified AP: 48 (31%)

Reachability
------------
  Reachable: 152 (97.4%)
  Unreachable: 4 (2.6%)
    - ACC-SW-15 (10.1.30.15) at Global/USA/NYC/Floor3 -- last seen 2h ago
    - AP-CHI-F2-03 (10.2.20.103) at Global/USA/CHI/Floor2 -- last seen 45m ago
    - AP-CHI-F2-04 (10.2.20.104) at Global/USA/CHI/Floor2 -- last seen 45m ago
    - RTR-WAN-02 (10.0.0.2) at Global/USA/NYC/MDF -- last seen 6h ago

Collection Status
-----------------
  Managed: 150
  Partial Collection Failure: 4
  Could Not Synchronize: 2

Role Distribution
-----------------
  ACCESS: 82 | DISTRIBUTION: 8 | CORE: 4 | BORDER ROUTER: 2 | UNKNOWN: 12

Site Summary
------------
Total Sites: 24 (8 areas, 10 buildings, 6 floors)
Sites with unreachable devices: 2 (Global/USA/NYC/Floor3, Global/USA/CHI/Floor2)

Software Version Compliance
----------------------------
  IOS-XE 17.09.04a: 140 devices (COMPLIANT)
  IOS-XE 17.06.05:  8 devices  (NON-COMPLIANT)
  AireOS 8.10.185:  4 devices  (COMPLIANT)
  NX-OS 10.3(2):    4 devices  (COMPLIANT)
```

---

## GAIT Audit Trail

After completing any inventory operation, record the session in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Catalyst Center inventory audit on $CCC_HOST: 156 devices total, 152 reachable (97.4%), 4 unreachable (ACC-SW-15, AP-CHI-F2-03, AP-CHI-F2-04, RTR-WAN-02). Collection failures: 6 devices. Software compliance: 96% on approved versions. 2 sites with unreachable devices flagged for investigation.","artifacts":[]}}'
```
