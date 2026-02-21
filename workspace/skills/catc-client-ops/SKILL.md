---
name: catc-client-ops
description: "Catalyst Center client operations and monitoring - list/filter wired and wireless clients, detailed client lookup by MAC, client count analytics, time-based analysis, SSID and band filtering, wireless troubleshooting"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["CATC_MCP_SCRIPT", "MCP_CALL"] } } }
---

# Catalyst Center Client Operations and Monitoring

Comprehensive client visibility through Cisco Catalyst Center (formerly DNA Center). This skill covers client enumeration, filtering, detailed client inspection by MAC address, client count analytics, time-based trend analysis, and wireless client troubleshooting.

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

- Monitoring wired and wireless client populations
- Investigating specific client connectivity issues by MAC address
- Capacity planning: how many clients per site, SSID, or band
- Wireless troubleshooting: signal quality, RSSI, band steering analysis
- Time-based analysis: client count trends over hours/days
- Security investigations: locate a client by IP or MAC across the network
- Help desk escalations: look up a user's device and connection details
- SSID utilization and OS distribution analytics

## Critical: Time Range Handling

The Catalyst Center client APIs require `startTime` and `endTime` in **epoch milliseconds**. The API enforces a **30-day maximum lookback** for `startTime`.

**ALWAYS call `get_api_compatible_time_range` FIRST** to convert human-readable time ranges into valid epoch millisecond pairs before calling any client tool.

### `get_api_compatible_time_range` -- Convert Time Ranges

**Parameters:**
- `time_window` (string, optional): Human-readable relative time. Examples: `"last 2 hours"`, `"last 7 days"`, `"today"`, `"yesterday"`, `"last 30 days"`. Takes precedence over ISO params if provided.
- `start_datetime_iso` (string, optional): Specific start in ISO 8601 format (e.g., `"2025-01-15T10:00:00Z"`)
- `end_datetime_iso` (string, optional): Specific end in ISO 8601 format. Defaults to now if omitted.

**Returns:** JSON with `startTime` and `endTime` (epoch ms), `adjusted_for_30_day_limit` flag, and ISO timestamps for verification.

```bash
# Relative time window
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 2 hours"}'

# Specific date range
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"start_datetime_iso":"2025-01-15T08:00:00Z","end_datetime_iso":"2025-01-15T17:00:00Z"}'

# Today only
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"today"}'
```

**IMPORTANT:** If the response shows `adjusted_for_30_day_limit: true`, the requested start time exceeded the API's 30-day limit and was automatically clamped. Inform the user that the effective time range is shorter than requested.

---

## Available Client Tools

### 1. `get_clients_list` -- List Connected Clients

Retrieves a list of clients from the `/dna/data/api/v1/clients` endpoint. **Hard limit of 100 clients per call.** If more than 100 clients match the filters, the tool returns the total count and a message requesting more specific filters instead of partial data.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_time` | `int` | Epoch ms start time (use `get_api_compatible_time_range`) |
| `end_time` | `int` | Epoch ms end time |
| `limit` | `int` | Max clients to return (default 100, capped at 100) |
| `offset` | `int` | Starting record for pagination (default 1) |
| `sort_by` | `str` | Attribute to sort by (e.g., `clientConnectionTime`) |
| `order` | `str` | `asc` or `desc` (default `asc`) |
| `client_type` | `str` | `"wired"` or `"wireless"` |
| `os_type` | `List[str]` | OS filter: `["Windows"]`, `["macOS"]`, `["Android"]`, etc. |
| `os_version` | `List[str]` | OS version filter |
| `site_hierarchy` | `List[str]` | Full site path: `["Global/USA/NYC/Floor2"]` |
| `site_hierarchy_id` | `List[str]` | Site hierarchy UUID(s) |
| `site_id` | `List[str]` | Site UUID(s) |
| `ipv4_address` | `List[str]` | Client IPv4 address(es) |
| `ipv6_address` | `List[str]` | Client IPv6 address(es) |
| `mac_address` | `List[str]` | Client MAC address(es) |
| `wlc_name` | `List[str]` | WLC name(s) |
| `connected_network_device_name` | `List[str]` | Network device name(s) clients are connected to |
| `ssid` | `List[str]` | SSID name(s) |
| `band` | `List[str]` | Wireless band(s): `["2.4GHz"]`, `["5GHz"]`, `["6GHz"]` |
| `view` | `List[str]` | Additional data views: `["Wireless"]`, `["WirelessHealth"]` |
| `attribute` | `List[str]` | Specific attributes to include |

**List type parameters** (os_type, site_hierarchy, ssid, band, etc.) must be passed as JSON arrays of strings: `["value1","value2"]`.

### 2. `get_client_details_by_mac` -- Detailed Client Info by MAC

Fetches comprehensive details for a single client identified by MAC address from the `/dna/data/api/v1/clients/{mac}` endpoint.

**Parameters:**
- `client_mac_address` (string, **required**): The MAC address of the client
- `start_time` (int, optional): Epoch ms start time
- `end_time` (int, optional): Epoch ms end time
- `view` (List[str], optional): Additional data views
- `attribute` (List[str], optional): Specific attributes

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_client_details_by_mac '{"client_mac_address":"AA:BB:CC:DD:EE:FF"}'
```

**Response includes:** Client MAC, IP address, hostname, OS type/version, connected device name, connected interface, VLAN, SSID (if wireless), band, channel, RSSI, SNR, data rate, connection time, health score, and more.

**Automatic retries:** If the API returns error code 14006 (data not ready for the requested endTime), the tool automatically retries with the API-suggested adjusted endTime.

### 3. `get_clients_count` -- Count Clients Matching Filters

Returns the total count of clients matching the specified filters from the `/dna/data/api/v1/clients/count` endpoint. Use this for analytics and capacity planning without retrieving full client records.

**Parameters:** Same filter parameters as `get_clients_list` (except `limit`, `offset`, `sort_by`, `order`, `view`, `attribute`).

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless"}'
```

---

## Client Operations Workflows

### Workflow 1: Find All Wireless Clients on a Specific SSID

**Step 1: Get the time range**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 2 hours"}'
```

Extract `startTime` and `endTime` from the response.

**Step 2: Count clients on the SSID first**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","ssid":["Corporate-WiFi"]}'
```

If count > 100, narrow with additional filters (site, band, OS) before listing.

**Step 3: List the clients**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","ssid":["Corporate-WiFi"]}'
```

**If count exceeded 100, narrow by site:**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","ssid":["Corporate-WiFi"],"site_hierarchy":["Global/USA/NYC/Floor2"]}'
```

### Workflow 2: Investigate a Client by MAC Address

Full client investigation for help desk escalation or security incident.

**Step 1: Get the time range**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 24 hours"}'
```

**Step 2: Fetch detailed client info**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_client_details_by_mac '{"client_mac_address":"AA:BB:CC:DD:EE:FF","start_time":1705312800000,"end_time":1705399200000}'
```

**Step 3: With additional wireless views**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_client_details_by_mac '{"client_mac_address":"AA:BB:CC:DD:EE:FF","start_time":1705312800000,"end_time":1705399200000,"view":["Wireless","WirelessHealth"]}'
```

**Analyze the results:**
- **Connection state:** Is the client currently connected? What is the connection time?
- **Network attachment:** Which switch/AP is it connected to? Which interface/SSID?
- **IP assignment:** Does it have a valid IP? DHCP or static?
- **Health score:** Client health score (0-10). Below 7 indicates issues.
- **For wireless clients:** RSSI, SNR, channel, band, data rate, AP name
- **OS information:** OS type and version for security posture assessment

### Workflow 3: Count Clients Per Site

Build a site-by-site client distribution report.

**Step 1: Get the time range**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 1 hours"}'
```

**Step 2: Get the site hierarchy**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" fetch_sites '{}'
```

**Step 3: Count clients at each site**

```bash
# Site 1
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"site_hierarchy":["Global/USA/NYC"]}'

# Site 2
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"site_hierarchy":["Global/USA/CHI"]}'
```

**Step 4: Break down by wired vs wireless per site**

```bash
# Wired clients at NYC
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"site_hierarchy":["Global/USA/NYC"],"client_type":"wired"}'

# Wireless clients at NYC
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"site_hierarchy":["Global/USA/NYC"],"client_type":"wireless"}'
```

**Build the report:**

```
Client Distribution Report
===========================
Catalyst Center: $CCC_HOST
Time Window: Last 1 hour (2025-01-15 14:00 - 15:00 UTC)

+----------------------------+-------+--------+----------+-------+
| Site                       | Total | Wired  | Wireless | %WiFi |
+----------------------------+-------+--------+----------+-------+
| Global/USA/NYC             | 1,245 |    320 |      925 | 74.3% |
|   NYC/Floor1               |   412 |    110 |      302 | 73.3% |
|   NYC/Floor2               |   498 |    130 |      368 | 73.9% |
|   NYC/Floor3               |   335 |     80 |      255 | 76.1% |
| Global/USA/CHI             |   876 |    250 |      626 | 71.5% |
| Global/USA/LAX             |   534 |    180 |      354 | 66.3% |
+----------------------------+-------+--------+----------+-------+
| TOTAL                      | 2,655 |    750 |    1,905 | 71.8% |
+----------------------------+-------+--------+----------+-------+
```

### Workflow 4: Time-Based Client Trend Analysis

Analyze how client counts change over time for capacity planning or anomaly detection.

**Step 1: Define time windows** (e.g., hourly snapshots over the last 8 hours)

```bash
# 8 hours ago to 7 hours ago
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 8 hours"}'

# Or use specific ISO ranges for precise hourly windows
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"start_datetime_iso":"2025-01-15T06:00:00Z","end_datetime_iso":"2025-01-15T07:00:00Z"}'
```

**Step 2: Count clients for each time window**

Run `get_clients_count` for each hourly window with the appropriate `start_time` and `end_time` values.

**Build the trend report:**

```
Client Count Trend (Wireless)
==============================
Site: Global/USA/NYC
Date: 2025-01-15

Hour (UTC)    | Count  | Delta  | Bar
--------------+--------+--------+---------------------------
06:00 - 07:00 |    245 |    --  | ============
07:00 - 08:00 |    512 |  +267  | =========================
08:00 - 09:00 |    891 |  +379  | ============================================
09:00 - 10:00 |  1,102 |  +211  | ======================================================
10:00 - 11:00 |  1,189 |   +87  | ===========================================================
11:00 - 12:00 |  1,156 |   -33  | =========================================================
12:00 - 13:00 |    987 |  -169  | =================================================
13:00 - 14:00 |  1,134 |  +147  | ========================================================

Peak: 1,189 clients at 10:00-11:00 UTC
Trough: 245 clients at 06:00-07:00 UTC
```

### Workflow 5: OS Distribution Analysis

Understand the client OS mix for security posture and compatibility planning.

**Step 1: Get time range**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 1 hours"}'
```

**Step 2: Count clients per OS type**

```bash
# Windows clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"os_type":["Windows"]}'

# macOS clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"os_type":["macOS"]}'

# iOS clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"os_type":["iOS"]}'

# Android clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"os_type":["Android"]}'

# Linux clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"os_type":["Linux"]}'
```

### Workflow 6: Wireless Band Distribution

Analyze the 2.4 GHz vs 5 GHz vs 6 GHz client distribution for RF planning.

```bash
# 2.4 GHz clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","band":["2.4GHz"]}'

# 5 GHz clients
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","band":["5GHz"]}'

# 6 GHz clients (Wi-Fi 6E)
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_count '{"start_time":1705312800000,"end_time":1705399200000,"client_type":"wireless","band":["6GHz"]}'
```

**RF planning flags:**
- More than 40% of clients on 2.4 GHz -> WARNING: Poor band steering, co-channel interference risk
- 5 GHz utilization > 80% of wireless clients -> HEALTHY: Good band steering configuration
- 6 GHz adoption < 5% when Wi-Fi 6E APs are deployed -> INFO: Check client capability and SSID configuration

### Workflow 7: Find a Client by IP Address

Locate a client on the network when you only know the IP (common for security investigations).

**Step 1: Get the time range**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_api_compatible_time_range '{"time_window":"last 4 hours"}'
```

**Step 2: Search by IP**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"ipv4_address":["10.1.50.42"]}'
```

**Step 3: Get full details using the MAC from the response**

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_client_details_by_mac '{"client_mac_address":"AA:BB:CC:DD:EE:FF","start_time":1705312800000,"end_time":1705399200000}'
```

### Workflow 8: Clients Connected to a Specific Network Device

Identify all clients connected through a particular switch or AP.

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"connected_network_device_name":["ACC-SW-01"]}'
```

### Workflow 9: Clients on a Specific WLC

```bash
CCC_HOST=$CCC_HOST CCC_USER=$CCC_USER CCC_PWD=$CCC_PWD python3 $MCP_CALL "python3 -u $CATC_MCP_SCRIPT" get_clients_list '{"start_time":1705312800000,"end_time":1705399200000,"wlc_name":["WLC-NYC-01"]}'
```

---

## Wireless Client Troubleshooting Reference

When investigating wireless client issues, use `get_client_details_by_mac` with the `Wireless` and `WirelessHealth` views and examine these key metrics:

### RSSI (Received Signal Strength Indicator)

| RSSI (dBm) | Quality | Action |
|-------------|---------|--------|
| -30 to -50  | Excellent | No action needed |
| -50 to -60  | Good | Acceptable for all applications |
| -60 to -67  | Fair | VoIP may experience quality issues |
| -67 to -70  | Weak | Consider AP placement or power adjustment |
| -70 to -80  | Very Weak | Roaming and throughput issues likely |
| Below -80   | Unusable | Client will disconnect or fail to associate |

### SNR (Signal-to-Noise Ratio)

| SNR (dB) | Quality | Action |
|----------|---------|--------|
| > 40     | Excellent | No action needed |
| 25-40    | Good | Acceptable |
| 15-25    | Fair | May impact higher data rates |
| 10-15    | Poor | Significant throughput degradation |
| < 10     | Unusable | Noise floor investigation required |

### Common Wireless Client Issues

| Symptom | Likely Cause | Investigation |
|---------|-------------|---------------|
| Low RSSI | Client too far from AP, physical obstructions | Check AP location, consider adding AP |
| Low SNR with OK RSSI | High noise floor | Check for interferers (microwave, Bluetooth, rogue APs) |
| Frequent disconnects | Sticky client, aggressive roaming | Check roaming threshold, 802.11r/k/v config |
| Slow throughput | Band steering failure, co-channel interference | Check band distribution, channel plan |
| Authentication failures | 802.1X/RADIUS issue | Check ISE logs, certificate validity |
| DHCP failure | Scope exhaustion, VLAN mismatch | Check DHCP scope, verify VLAN assignment |

---

## Client Operations Report Format

```
Client Operations Report
=========================
Catalyst Center: $CCC_HOST
Time Window: 2025-01-15 14:00 - 15:00 UTC

Client Overview
---------------
Total Connected: 2,655
  Wired: 750 (28.2%)
  Wireless: 1,905 (71.8%)

Wireless Band Distribution
---------------------------
  2.4 GHz: 285 (15.0%) -- HEALTHY (below 30% threshold)
  5 GHz:  1,502 (78.8%) -- HEALTHY
  6 GHz:    118 (6.2%)  -- HEALTHY (Wi-Fi 6E adoption growing)

Top SSIDs
----------
  Corporate-WiFi: 1,245 clients (65.4%)
  Guest-WiFi:       412 clients (21.6%)
  IoT-Devices:      248 clients (13.0%)

OS Distribution
----------------
  Windows:  1,102 (41.5%)
  macOS:      534 (20.1%)
  iOS:        445 (16.8%)
  Android:    312 (11.8%)
  Linux:       98 (3.7%)
  Other:      164 (6.2%)

Site Distribution
------------------
  Global/USA/NYC:   1,245 (46.9%)
  Global/USA/CHI:     876 (33.0%)
  Global/USA/LAX:     534 (20.1%)
```

---

## GAIT Audit Trail

After completing any client operations session, record the findings in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Catalyst Center client operations on $CCC_HOST: 2,655 total clients (750 wired, 1,905 wireless). Band distribution healthy: 15% on 2.4GHz, 79% on 5GHz, 6% on 6GHz. Top SSID: Corporate-WiFi (1,245 clients). OS mix: Windows 42%, macOS 20%, iOS 17%. No anomalies detected in the last 1-hour window.","artifacts":[]}}'
```
