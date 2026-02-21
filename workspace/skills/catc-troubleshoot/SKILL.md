---
name: catc-troubleshoot
description: "Catalyst Center troubleshooting workflows - device unreachable investigation, client connectivity issues, interface down analysis, site-wide outage triage, wireless roaming problems, integration with pyATS for CLI-level diagnostics"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["CATC_MCP_SCRIPT", "MCP_CALL"] } } }
---

# Catalyst Center Troubleshooting Workflows

Structured troubleshooting methodology using Cisco Catalyst Center (formerly DNA Center) as the primary diagnostic platform, with escalation to pyATS CLI-level tools when the controller APIs are insufficient. This skill provides decision trees, triage procedures, and escalation paths for the most common network issues surfaced through Catalyst Center.

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

- Help desk escalation: user reports "I can't connect"
- NOC alert: device unreachable in Catalyst Center
- Client connectivity complaints (wired or wireless)
- Site-wide outage affecting multiple users
- Wireless roaming issues or poor signal complaints
- Interface down investigations
- Post-change verification when something goes wrong
- Correlation between Catalyst Center data and live device state via pyATS

## Troubleshooting Principles

1. **Define the problem** -- What exactly is reported? Single user, multiple users, entire site? Wired or wireless? When did it start?
2. **Scope the impact** -- Use Catalyst Center client counts and device reachability to quantify: how many clients affected? How many devices unreachable?
3. **Gather data from the controller** -- Catalyst Center provides a controller-level view that covers hundreds of devices simultaneously. Start here.
4. **Correlate with live device state** -- When Catalyst Center data is stale or insufficient, escalate to pyATS for real-time CLI data.
5. **Isolate the fault domain** -- Is it the client, the access layer, the distribution/core, or a WAN/upstream issue?
6. **Resolve and verify** -- Fix the issue, confirm via both Catalyst Center and pyATS, document.

---

## Issue 1: Device Unreachable

**Trigger:** Catalyst Center shows one or more devices with `reachabilityStatus: Unreachable`.

### Decision Tree

```
Device Unreachable in Catalyst Center
|
+-- Step 1: Confirm the scope
|   How many devices are unreachable?
|   Are they at the same site?
|   |
|   +-- Single device unreachable
|   |   --> Go to "Single Device Investigation"
|   |
|   +-- Multiple devices at same site
|   |   --> Go to "Site-Wide Outage Triage" (Issue 4)
|   |
|   +-- Multiple devices across sites
|       --> Go to "Catalyst Center or Upstream Issue"
|
+-- Step 2: Single Device Investigation
|   |
|   +-- Check device details in CatC
|   +-- Check last update time
|   +-- Check collection status and error code
|   +-- Attempt pyATS connectivity test
|   |
|   +-- pyATS connects successfully?
|   |   |
|   |   +-- YES: CatC polling issue (SNMP/NETCONF credentials, ACL)
|   |   +-- NO: Device is truly unreachable
|   |       |
|   |       +-- Ping from adjacent device (pyATS)
|   |       +-- Check upstream interface state
|   |       +-- Check ARP/MAC table on upstream switch
|   |       +-- Physical layer: power, cable, SFP
```

### Step 1: Identify All Unreachable Devices

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"reachabilityStatus":["Unreachable"]}'
```

**Record for each device:** hostname, managementIpAddress, platformId, locationName, lastUpdated, collectionStatus, errorCode.

### Step 2: Check If It Is Site-Localized

```bash
# Get the site hierarchy to understand the topology
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_sites '{}'
```

Group unreachable devices by `locationName`. If multiple devices at the same site are unreachable, skip to Issue 4 (Site-Wide Outage).

### Step 3: Inspect the Specific Device

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"hostname":["UNREACHABLE-SW-01"]}'
```

**Analyze:**
- `lastUpdated` -- How long has it been unreachable? Minutes = recent event. Hours/days = chronic issue.
- `collectionStatus` -- `Could Not Synchronize` vs `Partial Collection Failure` vs `Managed`
- `errorCode` -- Specific error from Catalyst Center's collection engine

### Step 4: Check Interfaces on the Unreachable Device (If CatC Has Cached Data)

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"<UUID-from-step-3>"}'
```

**NOTE:** This returns the last-known interface state. If the device became unreachable recently, this data may still reflect the pre-failure state. Look for interfaces that were already showing errors before the device went dark.

### Step 5: Escalate to pyATS for Live Validation

When `$PYATS_MCP_SCRIPT` and `$PYATS_TESTBED_PATH` are available and the device is in the pyATS testbed:

```bash
# Attempt to connect and get basic state
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"UNREACHABLE-SW-01","command":"show ip interface brief"}'
```

**If pyATS connects but CatC cannot reach the device:**
- The device is alive but Catalyst Center's polling is blocked
- Check SNMP community strings, NETCONF/RESTCONF configuration
- Check if an ACL on the device is blocking the CatC management IP
- Verify the management VRF routing to the CatC appliance

**If pyATS also cannot connect:**
- The device is truly unreachable from the management network
- Ping from an adjacent device in pyATS:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"UPSTREAM-SW-01","command":"ping 10.1.10.1"}'
```

- Check the upstream switch's interface to the unreachable device:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"UPSTREAM-SW-01","command":"show interfaces GigabitEthernet1/0/1"}'
```

- Check ARP and MAC table on the upstream switch:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"UPSTREAM-SW-01","command":"show arp"}'
```

### Common Root Causes: Device Unreachable

| Root Cause | CatC Indicators | pyATS Indicators | Resolution |
|------------|-----------------|-------------------|------------|
| Device powered off | Unreachable, no updates | Connection refused | Check power, PDU, UPS |
| Management interface down | Unreachable | Cannot SSH | Verify mgmt interface config via console |
| SNMP credential mismatch | Partial Collection Failure | pyATS connects OK | Fix SNMP community on device or CatC |
| ACL blocking CatC | Unreachable from CatC | pyATS connects OK | Update ACL to permit CatC management IPs |
| Routing issue to mgmt subnet | Unreachable | Ping fails from adjacent device | Check routing table, management VRF |
| Upstream link failure | Multiple devices unreachable | Upstream interface down | Physical layer: cable, SFP, port |
| Device crash/reload | Recently unreachable | Boot messages in logs | Check `show logging`, `show version` uptime |

---

## Issue 2: Client Connectivity Problems

**Trigger:** User reports cannot connect to the network, slow connectivity, or intermittent drops.

### Decision Tree

```
Client Connectivity Issue
|
+-- Step 1: Identify the client
|   Do we have the MAC address, IP address, or username?
|   |
|   +-- MAC known --> get_client_details_by_mac
|   +-- IP known --> get_clients_list with ipv4_address filter, then get details by MAC
|   +-- Only username/location --> get_clients_list filtered by site
|
+-- Step 2: Is the client visible in CatC?
|   |
|   +-- YES: Client is associating/authenticating
|   |   |
|   |   +-- Check health score
|   |   +-- Wired or wireless?
|   |   |   |
|   |   |   +-- WIRED --> Check connected switch port, VLAN, duplex
|   |   |   +-- WIRELESS --> Check RSSI, SNR, band, AP, SSID
|   |   |
|   |   +-- Check IP assignment (DHCP working?)
|   |   +-- Check connected network device status
|   |
|   +-- NO: Client not visible
|       |
|       +-- Is the access switch/AP reachable?
|       +-- Is the client physically connected (cable/Wi-Fi enabled)?
|       +-- Is 802.1X/MAB failing? (check ISE if available)
|       +-- Is the SSID broadcasting?
```

### Step 1: Get Time Range

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 4 hours"}'
```

### Step 2: Look Up the Client

**By MAC address (preferred):**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_client_details_by_mac '{"client_mac_address":"AA:BB:CC:DD:EE:FF","start_time":1705312800000,"end_time":1705399200000,"view":["Wireless","WirelessHealth"]}'
```

**By IP address:**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"ipv4_address":["10.1.50.42"]}'
```

### Step 3: Analyze Client Data

**For wired clients, check:**
- `connectedNetworkDeviceName` -- Which switch is the client on?
- `connectedNetworkDeviceInterfaceName` -- Which port?
- `vlanId` -- Correct VLAN assignment?
- `ipv4Address` -- Valid IP? Or APIPA (169.254.x.x) indicating DHCP failure?
- `healthScore` -- Score 0-10. Below 7 = issue.

**For wireless clients, check:**
- `ssid` -- Connected to the correct SSID?
- `band` -- 2.4 GHz or 5 GHz?
- `rssi` -- Signal strength (see RSSI table below)
- `snr` -- Signal-to-noise ratio
- `dataRate` -- Current data rate in Mbps
- `connectedNetworkDeviceName` -- Which AP?
- `healthScore` -- Client health score

### Step 4: Check the Access Device

If the client's access switch or AP shows issues:

```bash
# Is the access device reachable?
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"hostname":["ACC-SW-01"]}'

# Get the switch's interfaces to check the client-facing port
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"<switch-UUID>"}'
```

### Step 5: Escalate to pyATS for Switch-Port Level Troubleshooting

When CatC data is insufficient (e.g., you need to check port security, 802.1X session state, or MAC address table):

```bash
# Check the specific switchport
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"ACC-SW-01","command":"show interfaces GigabitEthernet1/0/15"}'

# Check authentication sessions (802.1X/MAB)
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"ACC-SW-01","command":"show authentication sessions"}'

# Check MAC address table for the client
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"ACC-SW-01","command":"show mac address-table"}'

# Check DHCP snooping bindings
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"ACC-SW-01","command":"show ip dhcp snooping binding"}'

# Check port-security
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"ACC-SW-01","command":"show port-security"}'
```

### Common Root Causes: Client Connectivity

| Root Cause | CatC Indicators | pyATS/CLI Indicators | Resolution |
|------------|-----------------|----------------------|------------|
| DHCP exhaustion | Client has 169.254.x.x IP | `show ip dhcp pool` shows 0 free | Expand DHCP scope or reduce lease time |
| Port security violation | Client not visible | `err-disabled` state on port | Clear port-security, investigate |
| 802.1X failure | Client not visible | Authentication failed in ISE | Check credentials, certificate, RADIUS |
| Wrong VLAN | Client visible but no connectivity | Port in wrong VLAN | Correct VLAN assignment |
| Duplex mismatch | Poor health score (wired) | Half-duplex on one end | Set both ends to auto or match manually |
| Wireless: low RSSI | Low health score, low RSSI | N/A (wireless) | Move closer to AP, add AP coverage |
| Wireless: co-channel | Intermittent drops | N/A (wireless) | Adjust channel plan, reduce AP power |
| AP overloaded | Multiple clients with issues | N/A (wireless) | Load balance, add AP capacity |
| Upstream link failure | Multiple clients affected | Interface down on distribution | Physical layer or routing issue |

---

## Issue 3: Interface Down Analysis

**Trigger:** Catalyst Center shows interfaces in admin up / operationally down state, or CatC alerts on interface status changes.

### Step 1: Get All Interfaces on the Device

```bash
# Find the device first
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"hostname":["DIST-SW-01"]}'

# Fetch interfaces
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"<UUID>"}'
```

### Step 2: Identify Problem Interfaces

Filter the interface response for:
- `adminStatus: "UP"` AND `status: "down"` -- Operationally failed interfaces (admin enabled but link is down)
- High error counters in the interface data
- Interfaces with no description (potential unused/misconfigured ports)

### Step 3: Classify the Interface

| Interface Type | Impact | Urgency |
|---------------|--------|---------|
| Uplink to distribution/core | CRITICAL: Affects all downstream devices and clients | Immediate |
| Inter-switch link (trunk) | HIGH: May break VLAN spanning, STP reconvergence | Immediate |
| Access port (user-facing) | MEDIUM: Single user affected | Standard |
| Management interface | HIGH: Loses management access to the device | Urgent |
| Loopback | HIGH if used for routing (OSPF RID, BGP update-source) | Urgent |

### Step 4: Escalate to pyATS for Detailed Interface Diagnostics

```bash
# Detailed interface statistics
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-01","command":"show interfaces TenGigabitEthernet1/0/1"}'

# Check for recent log messages about the interface
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"DIST-SW-01"}'

# Check SFP/transceiver status
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-01","command":"show interfaces transceiver"}'

# Check EtherChannel status if applicable
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-01","command":"show etherchannel summary"}'

# Check spanning-tree for blocked ports
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-01","command":"show spanning-tree"}'
```

### Interface Down Root Causes

| Symptom | CatC Data | CLI Investigation | Likely Cause |
|---------|-----------|-------------------|-------------|
| admin UP, oper DOWN | Status mismatch in CatC | No link pulse on interface | Bad cable, SFP, remote end shut |
| CRC errors incrementing | Error counters in interface data | `show interfaces` CRC count | Faulty cable, bad SFP, duplex mismatch |
| Err-disabled | Port not visible or shows errors | `show interfaces status err-disabled` | Port-security, BPDU guard, storm-control |
| Flapping (up/down cycles) | Multiple status changes | `show logging` UPDOWN messages | Loose cable, auto-negotiation failure |
| STP blocked | Port up but no traffic | `show spanning-tree` BLK state | STP topology issue, loop detected |

---

## Issue 4: Site-Wide Outage Triage

**Trigger:** Multiple users at a single site report connectivity loss, or Catalyst Center shows multiple devices unreachable at the same location.

### Decision Tree

```
Site-Wide Outage
|
+-- Step 1: Quantify the impact
|   How many devices unreachable at this site?
|   How many clients affected?
|   |
|   +-- ALL devices unreachable at site
|   |   --> WAN link failure, upstream router, or site power outage
|   |
|   +-- SOME devices unreachable
|   |   --> Distribution layer or IDF/MDF issue
|   |
|   +-- Devices reachable but clients can't connect
|       --> DHCP, VLAN, wireless controller, or authentication issue
|
+-- Step 2: Identify the failure boundary
|   Which devices ARE still reachable?
|   What is the common upstream for the failed devices?
|
+-- Step 3: Investigate the upstream device
|   Check interfaces, routing, logs on the common upstream
|
+-- Step 4: Resolve and verify
    Fix the issue, confirm all devices come back, verify client counts recover
```

### Step 1: Assess Site Device Status

```bash
# Get all devices at the affected site
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"locationName":["Global/USA/NYC/Floor3"]}'
```

**Categorize the results:**
- Count reachable vs unreachable devices
- Identify device roles (ACCESS, DISTRIBUTION, CORE)
- If the distribution switch is unreachable, all downstream access switches will also be unreachable

### Step 2: Check Client Impact

```bash
# Get time range
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 1 hours"}'

# Count clients at the affected site NOW
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"site_hierarchy":["Global/USA/NYC/Floor3"]}'

# Compare with a baseline (e.g., same time window yesterday)
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"yesterday"}'
```

**Impact assessment:**
- Current client count vs expected baseline
- If client count dropped to 0 or near-0: complete site outage
- If client count dropped by 50%: partial outage (one IDF or floor affected)

### Step 3: Find the Failure Boundary

Check the upstream/distribution devices that serve the affected site:

```bash
# Check the distribution switch
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"hostname":["DIST-SW-NYC"]}'

# Check its interfaces
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_interfaces '{"device_id":"<DIST-UUID>"}'
```

### Step 4: Escalate to pyATS for the Reachable Upstream

If the distribution/core device is still reachable:

```bash
# Check all interfaces on the distribution switch
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-NYC","command":"show ip interface brief"}'

# Check routing table -- are routes to the affected site present?
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-NYC","command":"show ip route"}'

# Check OSPF/BGP adjacencies
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"DIST-SW-NYC","command":"show ip ospf neighbor"}'

# Check for recent events in the logs
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"DIST-SW-NYC"}'

# Ping the unreachable access switches from the distribution
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"DIST-SW-NYC","command":"ping 10.1.30.1"}'
```

### Site Outage Root Causes

| Scope | Likely Cause | Key Evidence | Resolution |
|-------|-------------|-------------|------------|
| All devices + all clients | Site power outage | All devices unreachable, no response to pings | Dispatch facilities team, check UPS/PDU |
| All devices + all clients | WAN link failure | Edge router reachable but uplink down | Check ISP, activate backup WAN if available |
| One floor/IDF | Distribution switch failure | Dist switch unreachable, access switches behind it down | Power cycle, console access, hardware swap |
| One floor/IDF | Trunk link failure | Access switches up but no VLAN connectivity | Check trunk port, SFP, cable between access and dist |
| Devices up but no clients | DHCP failure | Clients getting APIPA addresses | Check DHCP server, ip helper-address, DHCP relay |
| Devices up, wireless clients down | WLC issue | APs reachable but no SSID broadcast | Check WLC status, AP join status |
| Devices up, some clients down | VLAN issue | Specific VLAN clients affected | Check VLAN trunking, SVI status |

---

## Issue 5: Wireless Client Roaming Issues

**Trigger:** Wireless users report drops when moving between floors or areas, or CatC shows poor wireless health scores.

### Step 1: Get Client History

```bash
# Extended time range to capture roaming events
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 8 hours"}'

# Get detailed client info with wireless views
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_client_details_by_mac '{"client_mac_address":"AA:BB:CC:DD:EE:FF","start_time":1705312800000,"end_time":1705399200000,"view":["Wireless","WirelessHealth"]}'
```

### Step 2: Analyze Roaming Indicators

Look for:
- **AP changes** -- Frequent AP name changes indicate roaming events
- **RSSI drops** -- RSSI dipping below -70 dBm before roaming = sticky client (not roaming early enough)
- **Band changes** -- Client flipping between 2.4 GHz and 5 GHz during movement
- **SSID consistency** -- Client should stay on the same SSID during roaming

### Step 3: Check AP Coverage at the Problem Area

```bash
# List all APs at the affected site
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"family":["Unified AP"],"locationName":["Global/USA/NYC/Floor3"]}'

# Count wireless clients per AP to find overloaded APs
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","site_hierarchy":["Global/USA/NYC/Floor3"]}'
```

### Roaming Issue Root Causes

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Client holds onto far AP (sticky client) | 802.11k/v not enabled or client doesn't support it | Enable Optimized Roaming, BSS Transition Management |
| Client drops during roam | 802.11r (FT) not enabled, or PMK caching disabled | Enable Fast Transition (FT), enable CCKM/PMK caching |
| Client roams to 2.4 GHz | Band steering not aggressive enough | Increase band steering threshold, check client capability |
| Dead zone between APs | RF coverage gap | Add AP, increase power (carefully), adjust antenna |
| Client bounces between 2 APs | Equal signal from both APs | Reduce power on one AP, adjust cell boundaries |

---

## Issue 6: Catalyst Center Collection or API Issues

**Trigger:** CatC data seems stale, APIs return unexpected errors, or `collectionStatus` shows failures across many devices.

### Check Collection Failures

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"collectionStatus":["Partial Collection Failure"]}'

CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_devices '{"collectionStatus":["Could Not Synchronize"]}'
```

### API Time Range Errors

If client API calls return error 14013 (start time > 30 days ago):
- **Always use `get_api_compatible_time_range` first** to ensure the time range is valid
- The tool automatically clamps start times to the 30-day boundary

If client API calls return error 14006 (data not ready for endTime):
- The `get_clients_list`, `get_client_details_by_mac`, and `get_clients_count` tools automatically retry with the API-suggested adjusted endTime
- This is normal behavior when querying very recent data (within the last few minutes)

---

## Troubleshooting Report Format

Always produce a structured findings report after completing a troubleshooting session:

```
Troubleshooting Report
=======================
Catalyst Center: $CCC_HOST
Timestamp: YYYY-MM-DD HH:MM UTC
Ticket/Case: [reference number if applicable]

Problem Statement
-----------------
[What was reported, by whom, when it started]

Impact Assessment
-----------------
Devices affected: X unreachable out of Y total at site
Clients affected: ~Z clients (estimated from client count delta)
Sites affected: [list]
Severity: CRITICAL / HIGH / MEDIUM / LOW

Investigation Timeline
-----------------------
1. [HH:MM] Checked CatC device reachability -- found X devices unreachable
2. [HH:MM] Identified site-localized issue at Global/USA/NYC/Floor3
3. [HH:MM] Checked distribution switch DIST-SW-NYC -- reachable
4. [HH:MM] Found TenGig1/0/1 (uplink to Floor3 IDF) down/down
5. [HH:MM] pyATS logs show %LINK-3-UPDOWN at 14:23 UTC
6. [HH:MM] SFP transceiver showing rx power below threshold

Root Cause
----------
Failing SFP transceiver on DIST-SW-NYC TenGigabitEthernet1/0/1
(uplink to Floor3 access layer IDF)

Resolution
----------
[Steps taken to resolve, or escalation path if unresolved]

Verification
-----------
- All Floor3 access switches returned to Reachable in CatC
- Client count at Floor3 recovered to baseline (335 clients)
- No further interface flaps observed in 30-minute monitoring window

Preventive Measures
--------------------
- Schedule optical monitoring for all uplink SFPs
- Add redundant uplink to Floor3 IDF (single point of failure identified)
```

---

## GAIT Audit Trail

After completing any troubleshooting session, record the findings and resolution in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Troubleshooting: Site-wide outage at Global/USA/NYC/Floor3. Root cause: Failing SFP on DIST-SW-NYC Te1/0/1. Impact: 335 clients, 5 access switches unreachable for 47 minutes. Resolution: SFP replaced, services restored. Preventive: Redundant uplink recommended.","artifacts":[]}}'
```
