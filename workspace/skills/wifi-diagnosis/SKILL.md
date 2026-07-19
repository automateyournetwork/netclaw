---
name: wifi-diagnosis
description: "Diagnose Wi-Fi and internet connectivity issues using the Network Guardian observability data. Analyzes UniFi AP metrics, WAN health, speedtests, and client distribution to identify problems (high retries, AP imbalance, capacity, ISP degradation) and recommend actions."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: [wifi, wireless, unifi, wan, speedtest, observability, diagnosis, network-guardian]
priority: 10
mcp_servers: [prometheus-mcp, unifi-network, pfsense-mcp, pyats-mcp]
---

# Wi-Fi & Internet Diagnosis (Network Guardian)

Diagnose Wi-Fi client experience, AP health, WAN connectivity, and bandwidth
issues using the Network Guardian observability stack. Provide root-cause
analysis, evidence, and actionable recommendations (including "add another AP").

## When to Use

- User reports slow Wi-Fi, dropped connections, or poor streaming quality
- Alert fires: `WifiHighTxRetries`, `AccessPointOffline`, `InternetDown`,
  `WanHighLatency`, `WanHighLoss`, `SpeedtestBelowSLA`
- User asks "why is my Wi-Fi slow?", "should I add an AP?", "is it the ISP?"
- User asks to troubleshoot a specific AP or client segment
- Periodic health review of the wireless network

## Observability Stack (Network Guardian)

All data lives in the K3s observability namespace. Query via Prometheus
(Prometheus + VictoriaMetrics datasources) and Loki.

| Service | Cluster address | Query via |
|---------|----------------|-----------|
| Prometheus | prometheus:9090 | PromQL (recording rules + raw metrics) |
| VictoriaMetrics | victoriametrics:8428 | PromQL (SNMP interface counters, long-term) |
| Loki | loki:3100 | LogQL (syslog from pfSense, switches, UniFi) |
| Pushgateway | pushgateway:9091 | PromQL (speedtest results via Prometheus scrape) |
| Grafana | https://grafana.internal.byrnbaker.me | Dashboards for visual reference |

**External:** Prometheus is also accessible from this host at the cluster VIP or
init-node IP (port-forward or NodePort). For PromQL queries from NetClaw, use
the `PROMETHEUS_URL` env var (typically `http://192.168.13.2:9090` via the
k3s-server-1 redirect, or through pfSense port-forward if configured).

## Available Metrics

### Wi-Fi / UniFi (from unifi-exporter → Prometheus)

| Metric | Labels | Meaning |
|--------|--------|---------|
| `unifi_up` | `site` | 1 = exporter can reach the UniFi controller |
| `unifi_device_up` | `device`, `model`, `role`, `mac` | 1 = AP/switch ONLINE |
| `unifi_device_cpu_pct` | (same) | AP CPU utilization % |
| `unifi_device_memory_pct` | (same) | AP memory utilization % |
| `unifi_device_uptime_seconds` | (same) | AP uptime |
| `unifi_device_uplink_rx_bps` | (same) | AP uplink throughput from controller |
| `unifi_device_uplink_tx_bps` | (same) | AP uplink throughput to controller |
| `unifi_radio_tx_retries_pct` | `device`, `band` | **Key Wi-Fi quality signal.** TX retry % per radio band. High = RF congestion, interference, too many clients, or poor client signal. >20% degraded, >35% problematic. |
| `unifi_ap_clients` | `device`, `mac` | Clients associated per AP |
| `unifi_site_clients_total` | `site` | Total connected clients |
| `unifi_site_clients_wireless` | `site` | Wireless client count |
| `unifi_site_clients_guest` | `site` | Guest-network clients |

### WAN / Internet health (from blackbox → Prometheus)

| Metric | Labels | Meaning |
|--------|--------|---------|
| `probe_success` | `job`, `target`, `instance` | 1 = probe succeeded |
| `probe_duration_seconds` | (same) | Probe RTT (TCP connect latency) |
| `guardian:health_score` | `site` | Derived 0-100. Penalized for loss/latency/edge-down. |
| `guardian:wan_latency_ms:avg` | `site` | Average WAN latency in ms |
| `guardian:wan_loss_ratio:5m` | `site` | Fraction of failed probes (0-1) |

### WAN Bandwidth (speedtest → Pushgateway → Prometheus)

| Metric | Labels | Meaning |
|--------|--------|---------|
| `speedtest_download_bits_per_second` | `server`, `provider`, `location` | Last download rate |
| `speedtest_upload_bits_per_second` | (same) | Last upload rate |
| `speedtest_ping_latency_ms` | (same) | Speedtest RTT |
| `speedtest_ping_jitter_ms` | (same) | Jitter (variability) |
| `speedtest_packet_loss_pct` | (same) | Loss during speedtest |
| `speedtest_up` | (same) | 1 = test succeeded |

### WAN Interface throughput (SNMP → VictoriaMetrics)

| Metric | Labels | Meaning |
|--------|--------|---------|
| `interface_octets_in_bytes_total` | `device_name="pfsense"`, `interface_name` | WAN download counter |
| `interface_octets_out_bytes_total` | (same) | WAN upload counter |
| Use `rate(...[5m])*8` to get bits/sec. Default WAN interface: `igc0.201`. |

### Logs (Loki, for context/evidence)

| Query pattern | What it returns |
|---------------|-----------------|
| `{device_name="unifi"}` | UniFi OS syslog — CEF-format Wi-Fi client lifecycle events |
| `{device_name="unifi"} \|~ "Client Roamed"` | Roaming events (client moved from one AP to another) |
| `{device_name="unifi"} \|~ "Client Disconnected"` | Client disconnection events (with which AP) |
| `{device_name="unifi"} \|~ "Client Connected"` | Client association events (with which AP + band) |
| `{device_name="pfsense"} \|= "dpinger"` | Gateway monitor events (WAN latency/loss from pfSense itself) |
| `{device_name="pfsense"} \|~ "Alarm\|delay"` | Gateway alarm state changes |
| `{device_name=~"HomeSwitch.*"}` | Switch port up/down, CDP, spanning tree events |
| `{device_name=~"HomeSwitch.*"} \|~ "UPDOWN\|changed state"` | Physical link state changes (AP lost uplink?) |

### UniFi CEF Log Events (critical for Wi-Fi diagnosis)

The UniFi logs use CEF (Common Event Format). Key event IDs:

| Event ID | Name | Diagnosis use |
|----------|------|---------------|
| 400 | WiFi Client Connected | Which AP + band a client associated to; spikes = flapping |
| 401 | WiFi Client Disconnected | Client left an AP; frequent = instability or weak signal |
| 402 | WiFi Client Roamed | Client moved between APs; *absence* of these proves clients are sticky |

**CEF fields in each log line:**
- `UNIFIconnectedToDeviceName` / `UNIFIlastConnectedToDeviceName` — the AP name
- `UNIFIconnectedToDeviceIp` / `UNIFIlastConnectedToDeviceIp` — AP IP
- `UNIFIconnectedToDeviceMac` / `UNIFIlastConnectedToDeviceMac` — AP MAC
- `UNIFIcategory=Client Devices`
- `UNIFIsite=Default`

**Log-based analysis patterns (use these in LogQL):**

```logql
# Count roaming events per hour (healthy networks should have regular roaming)
sum(count_over_time({device_name="unifi"} |~ "Client Roamed" [1h]))

# Roaming direction: which AP are clients roaming TO?
{device_name="unifi"} |~ "Client Roamed" | line_format "{{.body}}" |~ "connectedToDeviceName=([^ ]+)"

# Client disconnect frequency (high = flapping/instability)
sum(count_over_time({device_name="unifi"} |~ "Client Disconnected" [1h]))

# Disconnects FROM a specific AP (is the Basement AP dropping clients?)
{device_name="unifi"} |~ "Client Disconnected" |~ "Basement"

# Connection events TO a specific AP (are clients re-associating to the same AP?)
{device_name="unifi"} |~ "Client Connected" |~ "Basement"

# Flap detection: disconnect + reconnect to SAME AP within minutes
{device_name="unifi"} |~ "Client (Connected|Disconnected)" |~ "Basement"
```

## Diagnosis Workflow

### Step 1: Categorize the complaint

- **Slow Wi-Fi for one device** → likely client-side or AP-overload
- **Slow for everyone** → AP problem, WAN problem, or ISP
- **Intermittent drops** → interference, channel congestion, or flapping
- **Throughput under the paid rate** → ISP or path issue

### Step 2: Query the data (in this order)

1. **Health overview** — single query gives the big picture:
   ```promql
   {guardian:health_score, guardian:wan_latency_ms:avg, guardian:wan_loss_ratio:5m}
   ```
   If health <90, WAN latency >40ms, or loss >0: it's a WAN/ISP issue, not Wi-Fi.

2. **AP status + client distribution:**
   ```promql
   unifi_device_up{role="ap"}           # both APs online?
   unifi_ap_clients                     # how many clients on each?
   ```
   - If one AP has 25+ clients and another has <10: **client imbalance**. Clients
     aren't roaming to the less-loaded AP. Causes: physical layout (all devices
     near one AP), min-RSSI not set, or insufficient coverage from the second AP.

3. **TX retries (the critical Wi-Fi quality metric):**
   ```promql
   unifi_radio_tx_retries_pct           # per AP, per band
   ```
   Interpretation:
   - **<10%** = healthy
   - **10-20%** = moderate; acceptable on 2.4 GHz with many IoT devices
   - **20-35%** = degraded; clients experience buffering, slow page loads
   - **>35%** = problematic; likely RF interference, too many clients, or
     clients at the edge of coverage (weak signal forces retransmissions)

   **2.4 GHz vs 5 GHz:**
   - 2.4 GHz always has higher retries (crowded spectrum, neighbors, IoT)
   - 5 GHz retries >15% is a stronger signal of a problem
   - If both bands are high on one AP: that AP is overloaded or has interference

4. **AP resource usage:**
   ```promql
   unifi_device_cpu_pct{role="ap"}
   unifi_device_memory_pct{role="ap"}
   ```
   - CPU >80%: AP hardware bottleneck (rare with U6-Pro, but possible with
     high client count + heavy traffic)
   - Memory >90%: AP may be dropping management frames

5. **WAN throughput (is the internet pipe full?):**
   ```promql
   rate(interface_octets_in_bytes_total{device_name="pfsense",interface_name="igc0.201"}[5m])*8
   ```
   If near the line rate (e.g., >800 Mbps on a 1G link): congestion is
   WAN-side, not Wi-Fi. Even Wi-Fi clients will be slow.

6. **Speedtest history (ISP delivering the paid rate?):**
   ```promql
   speedtest_download_bits_per_second
   speedtest_upload_bits_per_second
   ```
   Compare by server label: ISP-local vs different-carrier vs cloud path.
   If ISP-local is good but cloud-path is slow: upstream routing issue.
   If ISP-local is degraded: ISP problem (use as evidence for a ticket).

7. **Logs (if above suggests a specific cause):**
   ```logql
   {device_name="unifi"} |~ "(?i)(disconnect|deauth|radar|channel)"
   {device_name="pfsense"} |= "dpinger"
   ```

8. **Roaming & client lifecycle analysis (critical for AP imbalance diagnosis):**

   This is the step that turns "clients are imbalanced" into a *proven cause*.

   ```logql
   # Are clients roaming at all? Count roam events in the last 6h:
   sum(count_over_time({device_name="unifi"} |~ "Client Roamed" [6h]))

   # Where do roaming clients go? (direction)
   {device_name="unifi"} |~ "Client Roamed"

   # How often do clients disconnect from the overloaded AP?
   {device_name="unifi"} |~ "Client Disconnected" |~ "Basement"

   # Are clients flapping (disconnect + reconnect to same AP)?
   {device_name="unifi"} |~ "Client (Connected|Disconnected)" |~ "Basement"
   ```

   **Interpretation:**
   - **Zero or near-zero roam events + imbalanced client counts** = clients are
     *sticky* — they won't leave the Basement AP even though Sophie's Office exists.
     This means: coverage from the second AP doesn't reach the clients well enough
     to trigger a roam, OR min-RSSI / 802.11k/v roaming assistance isn't configured.
     → **Recommend: add an AP or enable min-RSSI.**
   - **Many roam events but clients return to the same AP quickly** = roaming is
     *attempted* but the second AP's signal is too weak, so clients bounce back.
     → **Recommend: relocate the second AP or add a third between them.**
   - **Many disconnect events from one AP without roaming** = clients are being
     *dropped* (interference, weak signal at the edge) rather than gracefully roaming.
     → **Recommend: increase coverage in that zone (add AP), check for interference.**
   - **Disconnect + reconnect to the SAME AP (flapping)** = RF environment is
     unstable (microwave, DFS radar, intermittent interference).
     → **Recommend: RF scan, change channels, check for interference sources.**

### Step 3: Diagnose and recommend

**Common patterns and recommendations:**

| Observation | Likely cause | Recommendation |
|-------------|-------------|----------------|
| One AP has 25+ clients, other <10 | Client imbalance; insufficient coverage from AP 2 | Consider adding an AP (or relocating the underused one) to balance coverage. Enable band steering/min-RSSI if not set. |
| TX retries >30% on 2.4 GHz, one AP | RF congestion on 2.4 from neighbors/IoT | Switch non-IoT clients to 5 GHz (band steering). Reduce 2.4 GHz TX power on that AP. Consider a Wi-Fi 6E AP if 5 GHz is also crowded. |
| TX retries >20% on 5 GHz | Too many clients or clients far from AP | **Add another AP** to reduce client density and improve coverage. Check for physical obstructions (floor/walls). |
| TX retries high on BOTH bands of one AP, normal on other | The overloaded AP covers a high-density area | **Add another AP** in that zone to split the load. |
| All APs high retries suddenly | Interference source (microwave, baby monitor, new neighbor AP) | Check for new sources with an RF scan (`unifi_trigger_rf_scan` via the UniFi MCP). Change channels. |
| WAN latency high but Wi-Fi retries normal | ISP or WAN issue, not Wi-Fi | Check speedtest history and dpinger logs. File ISP ticket with evidence. |
| Speedtest below SLA on ISP-local server | ISP under-delivering | Capture speedtest history as evidence. File ISP ticket. |
| Speedtest good on ISP-local, poor on cloud | Upstream peering/routing issue | Not directly actionable; document for the ISP, try a different cloud provider region. |

**"Should I add another AP?" decision tree:**

1. Is one AP serving >70% of total clients? → Yes (imbalance)
2. Are TX retries on that AP's 5 GHz band >15% sustained? → Yes (density problem)
3. Is the AP's CPU >60% regularly? → Yes (hardware saturation)
4. Are clients complaining about speed in a specific physical area not near the overloaded AP? → Yes (coverage gap)

If ≥2 of those are true: **recommend adding an AP** and suggest placement (between
the overloaded zone and the underserved area).

## What the Data Cannot Tell You (Limitations)

- **Per-client RSSI/signal strength:** the UniFi Integration API does not expose it.
  TX retries are the proxy. If per-client data is needed, use the UniFi MCP
  (`unifi_list_clients` via the `unifi-network` MCP server) for a point-in-time
  snapshot of connected clients and their association quality.
- **Channel utilization / interference details:** requires an RF scan (via the UniFi
  MCP `unifi_trigger_rf_scan`). Not continuously collected in metrics.
- **Individual client throughput:** not exposed by the Integration API. Use the UniFi
  MCP for a client-level lookup or check pfSense NetFlow data for that client's IP.
- **Roaming events:** ✅ **AVAILABLE** in UniFi syslog (Loki, `device_name="unifi"`,
  event 402 "WiFi Client Roamed"). Use LogQL to count and analyze roaming direction.
- **Disconnect reasons (deauth codes):** the CEF log includes the event but not the
  IEEE 802.11 reason code. If you need deauth reasons, check the UniFi controller
  UI or enable debug logging (not recommended in production).
- **Physical environment:** no data tells you about walls, floors, microwaves, or
  new neighbor APs. When interference is suspected (both bands degraded, sudden
  onset), recommend an RF scan as the investigative step.

## Required MCP Servers

| MCP Server | Purpose |
|-----------|---------|
| **unifi-network** | Ad-hoc queries to the UniFi controller (list clients, device details, trigger RF scans, radio config) |
| **pfsense** | Firewall rules, gateway status, ARP/DHCP, connectivity diagnostics, interface info |
| **pyats-mcp** | Switch show commands (interface status, CDP neighbors, VLAN verify) — HomeSwitch01/02/03 |

### Optional (enrichment)

| MCP Server | Purpose |
|-----------|---------|
| **nautobot-mcp-v2** | Source of truth: device inventory, VLANs, IP prefixes, cabling |
| **proxmox** | VM status (is the UniFi controller VM healthy?) |
| **rancher** | K3s pod status (is the unifi-exporter / OTel / Prometheus running?) |

## Network Topology (relevant to Wi-Fi)

```
ISP (1 Gbps symmetric, Lumen/CenturyLink)
  → pfSense (igc0.201 WAN, 192.168.100.1 gateway)
    → HomeSwitch01/02 (Cisco 3850, core, VLAN 3 management)
      → U6-Pro Basement Laundry Room (192.168.3.15, ~27 clients)
      → U6-Pro Sophie's Office (192.168.3.16, ~7 clients)
    → K3s cluster (VLAN 13, observability stack)
      → unifi-exporter → Prometheus → Alertmanager → NetClaw webhook
    → UniFi OS Server VM (192.168.100.10:11443, VLAN 100)
```

**Key facts:**
- APs are on VLAN 3 (management), clients bridge to their respective VLANs
- The UniFi controller VM is on VLAN 100 (HomeLan)
- The observability stack is on VLAN 13 (K3s)
- pfSense rule 95 allows VLAN13 → controller:11443 (exporter path)
- WAN interface confirmed: `igc0.201`
- ISP: Lumen/CenturyLink, Denver CO, 1 Gbps symmetric

## Alerts That May Trigger This Skill

| Alert | Meaning | First action |
|-------|---------|--------------|
| `WifiHighTxRetries` | TX retries >35% for 10m on a band | Check client count + both bands; correlate with time-of-day patterns |
| `AccessPointOffline` | AP offline 5m | Check uplink (switch port), AP CPU/mem before it went down, reboot history |
| `InternetDown` | All WAN probes fail 2m | Check pfSense gateway status, dpinger logs, ISP outage |
| `WanHighLatency` | >80ms avg WAN RTT 5m | Speedtest to ISP-local server; dpinger; check for WAN saturation |
| `SpeedtestBelowSLA` | <70% of 1 Gbps for 2h | Compare ISP-local vs other servers; file ISP ticket with evidence |
| `UniFiExporterDown` | No Wi-Fi data 10m | Check the exporter pod + API key + VLAN13→controller firewall rule |

## Grafana Dashboards for Context

| Dashboard | UID | Shows |
|-----------|-----|-------|
| Network Guardian — Home Pilot | `network-guardian` | KPIs, latency/loss, throughput, AP table, TX retries, events, speedtest |
| WAN Speedtest — Bandwidth Validation | `wan-speedtest` | Per-server download/upload history, latency, jitter, packet loss |
| Network Interfaces | `network-interfaces` | All pfSense interface throughput/errors (deeper than the WAN panel) |

## Example Triage (Real Scenario)

**User says:** "Wi-Fi is slow in the basement, my MacBook keeps buffering."

**Analysis:**
1. `guardian:health_score` = 99 → WAN is fine, not an internet issue
2. `unifi_ap_clients{device="U6-Pro - Basement..."}` = 27, Sophie's Office = 7 →
   heavy imbalance, Basement AP serves 80% of clients
3. `unifi_radio_tx_retries_pct{device="U6-Pro - Basement...", band="2.4GHz"}` = 23% →
   degraded (many IoT devices on 2.4 GHz)
4. `unifi_radio_tx_retries_pct{device="U6-Pro - Basement...", band="5GHz"}` = 13% →
   borderline; if the MacBook is on 5 GHz and still slow, the AP is loaded
5. `speedtest_download_bits_per_second` = 910 Mbps → ISP is delivering fine
6. **Logs (roaming analysis):**
   - `count_over_time({device_name="unifi"} |~ "Client Roamed" [6h])` = 3 events →
     very few roams
   - All 3 roams were TO Sophie's Office, none FROM Sophie's Office back to Basement
   - `count_over_time({device_name="unifi"} |~ "Client Disconnected" |~ "Basement" [6h])` = 8 →
     some clients being dropped but reconnecting to same AP (not roaming)

**Diagnosis:**
> The Basement AP is overloaded (27 clients, 23% 2.4 GHz retries, 13% 5 GHz retries).
> Roaming logs confirm clients are **not roaming away** from the Basement AP — only
> 3 roam events in 6 hours, and clients that disconnect reconnect to the same AP.
> Coverage from Sophie's Office doesn't reach most of the house adequately.

**Recommendations:**
1. **Short-term:** Enable min-RSSI on the Basement AP (-75 dBm). Enable band steering.
2. **Medium-term:** **Add a third AP** on the main floor between basement and
   Sophie's office for coverage overlap and load balancing.
3. **Consider 802.11k/v roaming assistance** if not already enabled.
4. **Verify:** After changes, monitor TX retries + AP clients + roaming events for 24-48h.

## Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `PROMETHEUS_URL` | `http://192.168.13.X:9090` (or port-forward) | PromQL queries |
| `LOKI_URL` | `http://192.168.13.X:3100` (or port-forward) | LogQL queries |
