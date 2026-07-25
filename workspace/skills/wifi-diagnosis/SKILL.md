---
name: wifi-diagnosis
description: "Diagnose Wi-Fi and internet connectivity using Home / Network Guardian observability. Prefer adapter metrics (UniFi Integration exporter first; other wireless vendors via stubs later). Analyzes AP retries, WAN health, speedtests, and client distribution."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PROMETHEUS_URL"] } } }
---

# Wi-Fi & Internet Diagnosis (multi-vendor adapters)

Diagnose Wi-Fi client experience, AP health, WAN connectivity, and bandwidth
issues using Home observability. **Wireless v1 adapter = UniFi** (Integration API
exporter → Prometheus `unifi_*`). Other vendors (generic SNMP, etc.) plug in via
the same metric contracts when available. Provide root-cause analysis, evidence,
and actionable recommendations (including "add another AP").

## When to Use

- User reports slow Wi-Fi, dropped connections, or poor streaming quality
- Alert fires: `WifiHighTxRetries24GHz`, `WifiHighTxRetries5GHz`,
  `WifiHighTxRetries6GHz`, `WifiTxRetriesCritical`, `AccessPointOffline`,
  `InternetDown`, `WanHighLatency`, `WanHighLoss`, `SpeedtestBelowSLA`
- User asks "why is my Wi-Fi slow?", "should I add an AP?", "is it the ISP?"
- User asks to troubleshoot a specific AP or client segment
- Periodic health review of the wireless network

## Observability Stack (Network Guardian)

Query via Prometheus (and optional VictoriaMetrics / Loki when configured).
Addresses come from **environment**, not hard-coded pilot hosts.

| Service | Address | Query via |
|---------|---------|-----------|
| Prometheus | `$PROMETHEUS_URL` | PromQL (recording rules + raw metrics) |
| VictoriaMetrics | `$VICTORIAMETRICS_URL` when set | PromQL (SNMP counters, long-term) |
| Loki | `$LOKI_URL` when set | LogQL (syslog, UniFi CEF, NetFlow) |
| Pushgateway | via Prometheus scrape job when deployed | speedtest results |
| Grafana | `$GRAFANA_URL` when set | Dashboards for visual reference |
| Home API | `$HOME_API_URL` or `$NETWORK_GUARDIAN_URL` | diary events |

**Docker Home:** Prometheus often at `http://127.0.0.1:9090`. **K3s Home / pilot:**
port-forward or ClusterIP / Grafana datasource proxy — always prefer `$PROMETHEUS_URL`.

## Available Metrics

### Wi-Fi (adapter metrics → Prometheus)

**UniFi adapter (v1):** unifi-exporter Integration API scrape.
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
| `convergence:health_score` | `site` | Derived 0-100. Penalized for loss/latency/edge-down. |
| `convergence:wan_latency_ms:avg` | `site` | Average WAN latency in ms |
| `convergence:wan_loss_ratio:5m` | `site` | Fraction of failed probes (0-1) |

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
# (look for the same AP name in both disconnect and connect within a window)
{device_name="unifi"} |~ "Client (Connected|Disconnected)" |~ "Basement"
```

## Operator knowledge base (vendor Wi‑Fi docs)

When the operator has uploaded UniFi / wireless vendor documentation via the HUD
**Knowledge** panel (`doc_type=vendor`), search it while diagnosing:

```
rag_search(
  query="UniFi band steering min RSSI channel width TX retries",
  collection="documents"
)
```

Use hits for **configuration procedures and limits**, not for live client counts
(those come from Prometheus / UniFi MCP). Cite `citation` fields in recommendations.

If the corpus has no UniFi docs, say so and continue with metrics — suggest uploading
the UniFi Network / Integration API PDF as type **vendor**.

## Diagnosis Workflow

### Step 1: Categorize the complaint
- **Slow Wi-Fi for one device** → likely client-side or AP-overload
- **Slow for everyone** → AP problem, WAN problem, or ISP
- **Intermittent drops** → interference, channel congestion, or flapping
- **Throughput under the paid rate** → ISP or path issue

### Step 2: Query the data (in this order)

1. **Health overview** — single query gives the big picture:
   ```promql
   {convergence:health_score, convergence:wan_latency_ms:avg, convergence:wan_loss_ratio:5m}
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

**Before recommending band steering or min-RSSI, VERIFY their current state:**

When the UniFi adapter is configured, use the `unifi-network` MCP server
(Integration API tools; do not raw-curl `/proxy/network/api/v1/*`):

```
# One-shot: all APs with channel, channelWidthMHz, and live txRetriesPct
integration_get_ap_radios()

# Single AP by MAC (e.g. 60:22:32:9a:da:8d)
integration_get_device(mac="<ap_mac>")
integration_get_device_stats(mac="<ap_mac>")

# Optional: after load_network_tools(), SSID list (legacy path may hang)
list_wlans()
```

Key settings to look for:
- **Channel + width per band** — from `integration_get_device` / `integration_get_ap_radios`
  (`channel`, `channelWidthMHz`, `frequencyGHz`). 40 MHz on 2.4 or 160 MHz on 5
  with overlapping neighbors is a common root cause of high retries.
- **Live TX retries** — from `integration_get_device_stats` or Prometheus
  `unifi_radio_tx_retries_pct` for trends.
- **Band steering / min-RSSI / TX power** — Integration API does **not** expose these
  today; note as unknown and recommend checking UniFi UI (do not invent values).

**Include the CURRENT state in your report.** Don't recommend "enable band
steering" if it's already on — instead note that it's on but insufficient
(suggest reducing 2.4 TX power or adding an AP). If it's OFF, flag it as a
quick win.

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
  (legacy `list_clients` after `load_network_tools` if it responds; Integration
  client list may time out on some controllers).
- **Channel / width:** ✅ via `integration_get_ap_radios` / `integration_get_device`.
- **Channel utilization / interference details:** RF scan via UniFi MCP `rf_scan`
  (legacy, may hang) or UniFi UI. Not continuously collected in metrics.
- **Individual client throughput:** not exposed by the Integration API. Use the UniFi
  MCP for a client-level lookup or check pfSense NetFlow data for that client's IP.
- **Roaming events:** ✅ **AVAILABLE** in UniFi syslog (Loki, `device_name="unifi"`,
  event 402 "WiFi Client Roamed"). Use LogQL to count and analyze roaming direction.
  This was previously listed as unavailable — it IS available via the SIEM syslog
  integration, not the metrics API.
- **Disconnect reasons (deauth codes):** the CEF log includes the event but not the
  IEEE 802.11 reason code. If you need deauth reasons, check the UniFi controller
  UI or enable debug logging (not recommended in production).
- **Physical environment:** no data tells you about walls, floors, microwaves, or
  new neighbor APs. When interference is suspected (both bands degraded, sudden
  onset), recommend an RF scan as the investigative step.## Example Triage (Real Scenario)

**User says:** "Wi-Fi is slow in the basement, my MacBook keeps buffering."

**Your analysis:**
1. `convergence:health_score` = 99 → WAN is fine, not an internet issue
2. `unifi_ap_clients{device="U6-Pro - Basement..."}` = 27, Sophie's Office = 7 →
   heavy imbalance, Basement AP serves 80% of clients
3. `unifi_radio_tx_retries_pct{device="U6-Pro - Basement...", band="2.4GHz"}` = 23% →
   degraded (many IoT devices on 2.4 GHz)
4. `unifi_radio_tx_retries_pct{device="U6-Pro - Basement...", band="5GHz"}` = 13% →
   borderline; if the MacBook is on 5 GHz and still slow, the AP is loaded
5. `speedtest_download_bits_per_second` = 910 Mbps → ISP is delivering fine
6. **Logs (roaming analysis):**
   - `count_over_time({device_name="unifi"} |~ "Client Roamed" [6h])` = 3 events →
     very few roams (should be dozens with 34 clients moving around a house)
   - `{device_name="unifi"} |~ "Client Roamed"` → all 3 roams were TO Sophie's
     Office, none FROM Sophie's Office back to Basement → one-directional, confirms
     clients near Sophie's AP eventually leave Basement, but most stay stuck
   - `count_over_time({device_name="unifi"} |~ "Client Disconnected" |~ "Basement" [6h])` = 8 →
     some clients are being dropped from Basement (signal edge?) but reconnecting
     to the same AP (not roaming to Sophie's)

**Diagnosis:**
> The Basement AP is overloaded (27 clients, 23% 2.4 GHz retries, 13% 5 GHz retries).
> Roaming logs confirm clients are **not roaming away** from the Basement AP — only
> 3 roam events in 6 hours, and clients that disconnect from Basement reconnect to
> the same AP rather than Sophie's Office. This proves the second AP's coverage
> doesn't reach most of the house adequately enough to trigger a roam.
>
> The MacBook is likely on 5 GHz but competing with other 5 GHz clients on that AP,
> and when it experiences weak signal at the edge of coverage, it stays stuck rather
> than roaming because it has nowhere better to go.

**Recommendations:**
1. **Short-term:** Enable min-RSSI on the Basement AP (e.g., -75 dBm) — forces
   weak-signal clients to disassociate, giving them a chance to find a better AP.
   Enable band steering to push capable devices to 5 GHz and free 2.4 for IoT.
2. **Medium-term:** **Add a third AP** on the main floor between basement and
   Sophie's office — this provides a stepping-stone that gives clients something
   to roam *to*, reduces client density on Basement, and improves coverage overlap.
3. **Consider 802.11k/v roaming assistance** — if not already enabled, this helps
   clients discover nearby APs proactively rather than waiting for signal to degrade.
4. **Verify:** After changes, monitor:
   - `unifi_radio_tx_retries_pct` should drop on Basement bands
   - `unifi_ap_clients` should rebalance (more clients on the new/office AP)
   - Roaming events in Loki should increase
   Track for 24-48h to confirm sustained improvement.

## Grafana Dashboards for Context

| Dashboard | UID | Shows |
|-----------|-----|-------|
| Network Guardian — Home Pilot | `network-guardian` | KPIs, latency/loss, throughput, AP table, TX retries, events, speedtest |
| WAN Speedtest — Bandwidth Validation | `wan-speedtest` | Per-server download/upload history, latency, jitter, packet loss |
| Network Interfaces | `network-interfaces` | All pfSense interface throughput/errors (deeper than the WAN panel) |

## Alerts That May Trigger This Skill

### Band-Aware TX Retry Alerts (per-band thresholds)

| Alert | Band | Threshold | Severity | First action |
|-------|------|-----------|----------|--------------|
| `WifiHighTxRetries24GHz` | 2.4 GHz | >35% for 10m | warning | Check for new interference, misbehaving client, or channel congestion beyond normal IoT noise |
| `WifiHighTxRetries5GHz` | 5 GHz | >15% for 10m | warning | Check client density; DFS radar events in logs; AP placement/coverage |
| `WifiHighTxRetries6GHz` | 6 GHz | >10% for 10m | warning | Check firmware; client compatibility; this band should be near-zero |
| `WifiTxRetriesCritical` | Any | >35% for 10m | critical | Full diagnosis workflow — clients severely impacted |

### Degraded Tier (informational, no autonomous triage)

| Alert | Band | Threshold | Meaning |
|-------|------|-----------|---------|
| `WifiDegraded24GHz` | 2.4 GHz | >20% for 30m | Chronic congestion; track time-of-day correlation |
| `WifiDegraded5GHz` | 5 GHz | >10% for 30m | Worth monitoring; investigate if sustained across hours |

### Other Alerts

| Alert | Meaning | First action |
|-------|---------|--------------|
| `AccessPointOffline` | AP offline 5m | Check uplink (switch port), AP CPU/mem before it went down, reboot history |
| `InternetDown` | All WAN probes fail 2m | Check pfSense gateway status, dpinger logs, ISP outage |
| `WanHighLatency` | >80ms avg WAN RTT 5m | Speedtest to ISP-local server; dpinger; check for WAN saturation |
| `SpeedtestBelowSLA` | <70% of 1 Gbps for 2h | Compare ISP-local vs other servers; file ISP ticket with evidence |
| `UniFiExporterDown` | No Wi-Fi data 10m | Check unifi-exporter (Docker profile / K3s) + `UNIFI_API_KEY` + path to controller |

## Log Event to Network Guardian Dashboard

After completing a diagnosis (autonomous or interactive), write a curated event
to the Network Guardian dashboard. This builds a human-readable diary of Wi-Fi
health investigations — not raw metrics, but concise outcome summaries.

```bash
curl -X POST "${HOME_API_URL:-$NETWORK_GUARDIAN_URL}/api/events?site=home" \
  -H "Authorization: Bearer ${HOME_API_TOKEN:-$NETWORK_GUARDIAN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"message":"<one-line summary>","severity":"<ok|info|watch|alert>","source":"netclaw"}'
```

**Severity badges:**
- **ok** (green) — issue resolved or confirmed benign
- **info** (blue) — informational finding, no action needed
- **watch** (amber) — degraded/monitoring, not yet actionable
- **alert** (red) — active problem requiring human intervention

**Example events for Wi-Fi diagnosis:**
- `{"message":"WifiHighTxRetries24GHz Basement AP: IoT camera on Wi-Fi instead of CAT5, airtime 91% — needs physical fix","severity":"watch","source":"netclaw"}`
- `{"message":"Client imbalance resolved: min-RSSI enabled, clients rebalancing across APs","severity":"ok","source":"netclaw"}`
- `{"message":"5GHz retries elevated on Sophie's Office AP: 14 clients on DFS channel, monitoring","severity":"info","source":"netclaw"}`


## Operator RF actions (not agent-automated)

**TX power:** UniFi Network Integration API does **not** expose TX power. Agents must
report `tx_power: unknown` — never invent values. Future: SNMP on APs if agents respond.

**Channel AI Optimize (human only):** AirView → Radios → Channel AI View → **Optimize**
→ **Apply Changes**. Changes **channels only** (not width/power). After apply, re-check
with `integration_get_ap_radios` + Prometheus `unifi_radio_tx_retries_pct`.

**Agent MoP should still recommend** width (2.4→20 MHz, 5→80 MHz), band steering, min
RSSI, and power when evidence supports it — operator applies in UniFi UI.
