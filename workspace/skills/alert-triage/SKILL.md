---
name: alert-triage
description: "Investigate alerts from the home/edge observability stack via adapters (firewall, wireless, SoT). Receives enriched alert context (device name, IP, platform, role) from the alert receiver webhook and uses MCP tools matched to platform. Multi-vendor: edge firewalls (pfSense first), wireless controllers (UniFi first), switches, hypervisors, and Linux hosts."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PROMETHEUS_URL"] }, "optional": { "env": ["RAG_DATA_DIR"] } } }
---

# Alert Triage

Investigate alerts received from the observability stack (Prometheus → Alertmanager → NetClaw Alert Receiver).

## Delegation (MANDATORY for Border — iN2N / Risk of NetClaws)

This install is an iN2N **risk** (name from `N2N_RISK_NAME`, e.g. a home pilot):
the Border (main gateway) is the **brain** — it understands the request and
**follows skill direction**. Heavy investigation runs on **member claws** with
scoped tools and their own models (typically `{risk}/guardian-claw`).

### Border first tool call (hard rule)

If you are the **Border** on an autonomous alert / alert-receiver webhook:

1. **Your first tool call MUST be** `n2n_route(..., target_hint="alert-triage")`.
2. **Do not** call `pfsense-*`, `prometheus-*`, `grafana-*`, `message`, `exec`,
   or other investigation/delivery tools **before** `n2n_route` has returned a
   `task_id` and you have finished polling it.
3. Skipping straight to device tools is a **skill failure**, even for synthetic
   `ConvergencePipeTest` alerts — the point of those tests is the full pipe
   including member investigation.

If you are the **Border** (you have `n2n_route` and are NOT already a member
executing a delegated task), you MUST delegate alert investigation to
`guardian-claw` rather than investigating with the full toolset yourself.

**How to know you are already the member (NEVER re-delegate):**
- Your prompt starts with `You are the iN2N MEMBER` or
  `Execute the 'alert-triage' skill for the following request`
- Your identity / env is `byrns-risk/guardian-claw` (or any `*/guardian-claw`)
- You were handed this task by iN2N (member worker), not by a human chat

If any of those apply: **skip `n2n_route` entirely**. Investigate with Steps 1–8
below and return findings. Re-calling `n2n_route` from a member causes nested
tasks that look like “timeouts” to the Border.

**How to delegate (Border only — efficient path):**
1. Call `n2n_route(request_text="<the full alert context you received>", target_hint="alert-triage")`
2. You will get back a `task_id` and `member_id` (typically `{risk}/guardian-claw`).
3. **Prefer `n2n_task_wait(task_id, timeout_seconds=45)`** (repeat until terminal).  
   Each call waits up to ~45s (MCP-safe). If response has `still_running` or state
   `working`/`submitted`, **call `n2n_task_wait` again** with the same `task_id`.  
   Members often take 30–120s — **never** stop after one `working` status.
4. If `n2n_task_wait` is unavailable, poll `n2n_task_status` **until terminal**
   (every ~5–15s). Only declare timeout after **≥ 3 minutes** wall-clock on
   *this* `task_id`.
5. On **completed**: call `n2n_task_result(task_id=...)` if the wait payload has no
   findings body, then **return the member's findings** — do **not** re-investigate.
6. **STOP HERE** on success. Do NOT execute Steps 7 or 8 yourself — the member
   handles Discord + Guardian diary when it is the investigator. Your job is wait +
   surface the member report (hook sessions use `deliver=false`; diary is SoT).
7. On **failed** / **true timeout** / `n2n_route` error: fall back to **direct
   investigation** using the procedure below (white-NOC safety valve).

**When to skip delegation (investigate directly):**
- You ARE the guardian-claw member (already executing a delegated task) — see above
- `n2n_route` returns an error (no capable member / member unreachable)
- Delegation failed or truly timed out after polling **this** task_id ≥ 3 minutes
- The user explicitly asks YOU (Border) to investigate in an interactive session

## When to Use

- Alert receiver triggers investigation (autonomous mode)
- User asks "what's alerting?" or "check on <device>"
- User asks to investigate a specific alert or device issue
- Follow-up from monitoring-onboard after new alerts fire

## Observability Stack

| Service | Address | Query via | Use |
|---------|---------|-----------|-----|
| Prometheus | `$PROMETHEUS_URL` (Docker Home: `http://127.0.0.1:9090`; pilot may use Grafana datasource proxy) | `prometheus-mcp` | Metrics, targets, `up`/probe status |
| Grafana | `$GRAFANA_URL` when configured | `grafana-mcp` | Dashboards + query Loki/VictoriaMetrics datasources |
| Loki | `$LOKI_URL` or via Grafana Loki datasource | `grafana-mcp` (Loki datasource) | Logs, syslog, **NetFlow flow records** |
| VictoriaMetrics | `$VICTORIAMETRICS_URL` or Grafana datasource | `grafana-mcp` | `goflow2_*` flow metrics |
| Alertmanager | `$ALERTMANAGER_URL` (default often `:9093`) | HTTP `/api/v2/alerts` | Check firing alerts |
| UniFi Network | `$UNIFI_HOST` (local console) | `unifi-network` | AP radios (channel/width), live stats, devices |
| Home API / diary | `$HOME_API_URL` or `$NETWORK_GUARDIAN_URL` | HTTP `/api/events` | Investigation diary POST/PATCH |

### NetFlow / connection data (IMPORTANT — this exists, use it)

When NetFlow/IPFIX is deployed (pilot OBS / full stack), do **not** tell the user to
"enable NetFlow" without checking. To find **what a host is connecting to**
(destination IP, port, protocol), prefer existing flow data when present:

- **goflow2** (`v2.1.3`, `-format=json`) receives IPFIX on `4739/udp` → writes
  `/flows/netflow.jsonl` → OTel collector tails it → Loki (`service_name="netflow"`).
- **Loki** (via `grafana-mcp`, Loki datasource). goflow2 v2 emits **snake_case** JSON
  keys (NOT the PascalCase `SrcAddr` in some older dashboards):
  ```logql
  {service_name="netflow"} | json | src_addr="192.168.100.45"
  {service_name="netflow"} | json | dst_port="179" | proto="TCP"
  ```
  Fields: `src_addr`, `dst_addr`, `src_port`, `dst_port`, `proto`, `sampler_address`,
  `bytes`, `packets`, `etype`, `type`, `time_received_ns`.
  Note: `proto` and `etype` are **strings** (`"TCP"`, `"IPv6"`) — filter with quotes
  (`dst_port="179"`), a numeric filter like `dst_port=179` will not match.
- **VictoriaMetrics** (via `grafana-mcp`, `grafana.internal.byrnbaker.me (VictoriaMetrics proxy)`): `goflow2_*` counters
  for volume/rate, labels `sampler_address`, `dst_port`, etc.
- Grafana dashboard: `lab-network/netflow-traffic.json`.

**Verify before relying on it:** the NetFlow overlay is defined but may not always be
running. Before concluding, check data is actually present — query
`{service_name="netflow"}` (no filter) for the last 5m, or check VictoriaMetrics for
`goflow2_flow_traffic_packets_total`. If both are empty, NetFlow is down/not exporting;
say so and fall back to `search_firewall_states` (live pfSense connections). Do not
tell the user to "enable NetFlow" — the pipeline exists; if it's empty it needs
restarting (`docker compose ... -f docker-compose.netflow.yml up -d` on the OBS host)
or pfSense isn't sending IPFIX to `K3s cluster (goflow2 IPFIX)`.

## Alert Context

When triggered by the alert receiver, you will receive:
- **alertname** — what fired (e.g., InstanceDown, HighCPU)
- **device_name** — resolved hostname
- **device_ip** — management IP
- **device_platform** — pfsense, ios, proxmox, linux
- **device_role** — firewall, switch, hypervisor, etc.
- **severity** — critical, warning, info
- **summary** — human-readable description
- **status** — firing or resolved

## Investigation Principles (read first)

1. **Use the data you already have before recommending new tooling.** Before you
   suggest "enable X", "install a flow exporter", "forward syslog", or "SSH in and
   run Y", check whether that capability already exists. This network already has:
   pfSense MCP (ARP, DHCP, states, logs, NAT), NetFlow (goflow2 → Loki/VictoriaMetrics),
   Prometheus, Loki, Grafana, SNMP. Recommending something already configured is a
   failure, not a help.
2. **Reach for an MCP tool before declaring "I can't."** Never say "I can't SSH into
   pfSense" as a dead end — the `pfsense-mcp` answers ARP, DHCP leases, firewall
   states, NAT, and logs over its REST API. If you don't know a tool exists, list
   your available tools before concluding data is unavailable.
3. **State what you checked.** If a query returns empty, say what you queried and the
   window. Do not fabricate a root cause (e.g. "syslog only maps 192.168.220.x") from
   a guess — verify against the live config or data before asserting it.
4. **Match the tool to the question:**
   | Question | Tool |
   |----------|------|
   | What is host X connecting to / on what port? | NetFlow (Loki `{service_name="netflow"}`) + `search_firewall_states` |
   | What/where is host X (IP, MAC, name)? | `get_arp_table`, `search_dhcp_leases` |
   | What's the LAN/DHCP lease range? | `get_dhcp_server_config` |
   | Why is X being blocked? | `diagnose_blocked_traffic`, `get_firewall_log` |
   | Is the block count real/excessive? | `analyze_blocked_traffic` (compare to threshold) |


## Operator knowledge base (HUD uploads → `rag_search`)

The HUD **Knowledge** panel (and Slack ingest) puts vendor PDFs / handbooks into
the shared offline corpus at `$RAG_DATA_DIR` (default `~/.openclaw/rag`), collection
`documents`. **You have `rag-mcp` tools** — use them during investigations.

**When to search (before guessing remediation or MoP steps):**
| Situation | Example `rag_search` |
|-----------|----------------------|
| UniFi / Wi‑Fi AP alerts | `query="UniFi radio channel width retries"`, `collection="documents"`, filter `doc_type: vendor` |
| pfSense / edge firewall | `query="pfSense gateway group failover"`, filter `doc_type: vendor` |
| Cisco switch / VLAN | `query="Catalyst VLAN VTP configuration"`, filter `doc_type: vendor` |
| Customer change policy | filter `doc_type: customer` |
| Install / upgrade MoP | filter `doc_type: install-guide` or `standard` |

**Rules:**
1. Prefer **live metrics/MCP** for current state; use RAG for **procedures, limits, CLI syntax, known caveats**.
2. Call `rag_search` early when the alert implies vendor-specific remediation (radio settings, firewall features, switch features).
3. Cite returned `citation` fields in investigation notes and Discord reports.
4. If `corpus_empty` or no hits: say so — do not invent handbook content. Suggest operator upload the PDF as type **vendor**.
5. Prior **investigation cases** use `collection="investigations"` (Stage 7). Vendor manuals use `collection="documents"` (default).

## Procedure

### Step 1: Confirm Alert is Active

Query Prometheus or Alertmanager to verify the alert is still firing:

```
# Via Prometheus instant query
up{instance="<device_name>"} == 0

# Or check Alertmanager API
GET ${ALERTMANAGER_URL:-http://127.0.0.1:9093}/api/v2/alerts?filter=alertname="<alertname>"
```

**GATE:** If alert already resolved, post brief all-clear and stop.

### Step 2: Gather Metrics Context (15-minute window)

Query Prometheus for relevant metrics based on alert type:

| Alert Type | Key Queries |
|------------|-------------|
| InstanceDown | `up{instance="<name>"}`, `probe_success{instance="<name>"}` |
| HighCPU | `node_cpu_seconds_total{instance="<name>"}`, `process_cpu_seconds_total` |
| HighMemory | `node_memory_MemAvailable_bytes{instance="<name>"}` |
| DiskFull | `node_filesystem_avail_bytes{instance="<name>"}` |
| InterfaceDown | `ifOperStatus{instance="<name>"}` (via SNMP exporter) |
| HighTraffic | `node_network_receive_bytes_total{instance="<name>"}` |

Use range queries for trend: `query_range?query=<expr>&start=<15m-ago>&end=now&step=60s`

### Step 3: Device-Specific Investigation

**Adapter rule:** match tools to the configured firewall / wireless / SoT adapters
(`convergence.yaml` / env). pfSense MCP and UniFi Integration API are the v1 defaults;
Cisco IOS uses pyATS; other vendors use their MCP when installed. Never claim a
vendor path you cannot query.

Based on **device_platform** (adapter-driven; use available tools, do not invent vendors):

#### pfSense (`platform: pfsense`)

Use the `pfsense-mcp` tools (these are the real tool names — you do NOT need SSH):

Health / config:
- `system_status` — uptime, CPU, memory, disk, temp, version
- `search_interfaces` / `search_interface_configs` — interface states, IPs, traffic
- `search_firewall_rules` / `find_blocked_rules` — active ruleset, block/reject rules
- `search_services` — service states (DNS, DHCP, unbound, OpenVPN)

Who/where is a host (answers "what is host X, what's it connecting to, what's its IP"):
- `get_arp_table` — live IP↔MAC on each interface (filter by `ip_address` / `mac_address`)
- `search_dhcp_leases` — active/expired leases (hostname, IP, MAC)
- `get_dhcp_server_config` — the DHCP pool ranges per interface (answers "what's the LAN lease range")
- `search_firewall_states` — live active connections (source, dest, port, proto, state)
- `search_nat_port_forwards` / `search_nat_outbound_mappings` — NAT translations

Logs / blocked traffic:
- `get_firewall_log` — filterlog entries (filter by source/dest IP, port, protocol, action)
- `search_logs_by_ip` — all log activity for one IP
- `analyze_blocked_traffic` — grouped block analysis with threat scoring
- `diagnose_blocked_traffic` — why a specific source is being blocked (rules + log + alias)
- `diagnose_connectivity` — ping + ARP + gateway check to a target

For "what port / where is host X connecting?" prefer **NetFlow** (see NetFlow
section) for historical flows, and `search_firewall_states` for live connections.
The pfSense filterlog only records what the firewall *blocked or passed by rule* —
NetFlow is the authoritative source for full connection detail.

#### Cisco IOS/IOS-XE (`platform: ios` or `iosxe`)

Use pyATS MCP:
- `pyats_run_command(device="<name>", command="show ip interface brief")`
- `pyats_run_command(device="<name>", command="show processes cpu")`
- `pyats_run_command(device="<name>", command="show logging last 30")`
- `pyats_run_command(device="<name>", command="show interfaces status")`

#### Proxmox (`platform: proxmox`)

Use Proxmox MCP:
- Check node status (CPU, memory, storage)
- List VMs/containers and their states
- Check recent tasks/events
- Review cluster health if multi-node

#### Linux (`platform: linux`)

Use SSH or node_exporter queries:
- System load, memory, disk via Prometheus queries
- Loki logs: `{hostname="<name>"} |~ "error|critical|failed"`

#### UniFi AP / Wi-Fi (`platform: unifi` or alertname matches `Wifi*`)

**Prefer MCP tools over raw curl.** `unifi-network` is on guardian-claw (and Border).
On UniFi OS / Network Integration API controllers, use the **Integration API tools**; do **not**
guess `/proxy/network/api/v1/...` paths — those return `NoSiteContext` / `InvalidObject`.

1. Prometheus first (trends): `unifi_radio_tx_retries_pct`, `unifi_ap_clients`,
   `unifi_device_up{role="ap"}`
2. Live radio config + retries via UniFi MCP (always available — no `load_network_tools` needed):
   - `integration_get_ap_radios` — **one-shot** all APs: channel, width, txRetriesPct, CPU
   - `integration_list_devices` / `integration_get_device(mac=...)` — per-AP detail
   - `integration_get_device_stats(mac=...)` — CPU/mem/uplink + per-band retries
3. Loki CEF: `{device_name="unifi"} |~ "Client (Connected|Disconnected|Roamed)"`
4. **TX power is not exposed** by the Integration API (and is not invented). Say
   `tx_power: unknown` if needed. SNMP on APs may fill this later if OIDs respond.

If a legacy tool (`list_devices` after `load_network_tools`) hangs, abandon it and
use the `integration_*` tools above.

**Remediation (human only — do not auto-mutate radios):**
- Channel width (e.g. 2.4 → 20 MHz, 5 GHz → 80 MHz), band steering, min RSSI, TX power
  → UniFi UI / operator MoP.
- **Channel AI Optimize:** operator path only — *AirView → Radios → Channel AI View →
  Optimize → Apply Changes* (channels only; does not change width/power). Agent may
  **recommend** this; there is no safe MCP “Apply Optimize” API today.
- After operator applies changes, re-run `integration_get_ap_radios` + retry trends
  to confirm.

**Guardian event id:** when the prompt includes `Guardian event id: <uuid>`, always
**PATCH** that event — never POST a duplicate case.

### Step 4: Log Correlation

Query Loki for device logs around the alert time:

```
{hostname="<device_name>"} |~ "(?i)(error|critical|warning|down|fail)"
```

Time window: alert start time ± 5 minutes.

### Step 5: Root Cause Classification

| Class | Evidence |
|-------|----------|
| **unreachable** | `up==0`, no response to ping/SSH, interface down |
| **resource-exhaustion** | CPU > 90%, memory > 95%, disk > 95% |
| **service-failure** | Specific service down while host is up |
| **network-issue** | Interface errors, packet loss, routing change |
| **configuration-error** | Recent config change correlating with failure |
| **external** | Upstream dependency down affecting this device |

### Step 6: Triage Report

```
╔══════════════════════════════════════════════════════════════╗
║              ALERT TRIAGE — <alertname>                      ║
╠══════════════════════════════════════════════════════════════╣
║ Device: <name> (<ip>)                                       ║
║ Platform: <platform> | Role: <role>                         ║
║ Severity: <severity> | Status: <firing|resolved>            ║
╠══════════════════════════════════════════════════════════════╣
║ FINDINGS:                                                   ║
║   • <metric evidence>                                       ║
║   • <device command output summary>                         ║
║   • <log evidence>                                          ║
╠══════════════════════════════════════════════════════════════╣
║ ROOT CAUSE: <classification>                                ║
║ DETAIL: <plain language explanation>                         ║
║ RECOMMENDATION: <specific action>                           ║
║ REMEDIATION SAFE? <yes — auto-fixable | no — needs human>   ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 6b: Enrich external IPs (threat intelligence)

For any **external/public** source IP in the alert (port scans, WAN blocks,
suspicious inbound), enrich before concluding. Skip private/RFC1918 addresses.

- `greynoise_community_lookup(ip)` — free, no key. Is it benign internet noise /
  a known scanner (Censys, Shodan) or targeted? Best first signal for scans.
- `threatintel_lookup_ip(ip)` / `abuseipdb_check` / `otx_get_pulses` — reputation,
  abuse confidence score, and threat-pulse membership.
- gtrace `asn_lookup(ip)` / `geo_lookup(ip)` — ownership (org/ASN) and location.

Fold the verdict into ROOT CAUSE (e.g. "EXTERNAL — benign scanner (Censys)").

### Step 7: Deliver findings to Discord (MANDATORY — investigation is incomplete without this)

You MUST post the completed triage report to the Discord alerts channel. This is
a core operational requirement of the alert-triage skill, not an external
instruction.

**Home NOC alerts channel:** use env `DISCORD_ALERT_CHANNEL_ID` / `DISCORD_CHANNEL_ID`
on guardian-claw (numeric snowflake). **Never** send the literal text
`${DISCORD_ALERT_CHANNEL_ID}` — shell-style variables are **not** expanded inside
the message tool.

Use the `message` tool (works on Border / gateway with Discord plugin):

```
message send --channel discord --target channel:<DISCORD_ALERT_CHANNEL_ID> --message "<triage report>"
```

Or `exec` (expand env in shell):
```bash
openclaw message send --channel discord --target "channel:${DISCORD_ALERT_CHANNEL_ID}" --message "<triage report>"
```

**Member claw fallback (when `message` says channel unavailable):** scoped members
do not load the Discord plugin. Post via webhook instead (env on guardian-claw):

```bash
# Prefer DISCORD_WEBHOOK_URL if set; content max ~1900 chars
curl -sS -X POST "${DISCORD_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1][:1900]))' "<triage report>")}"
```

If both message tool and webhook fail, still produce the Step 6 report in your
reply so the operator can see it in the session / n2n task result.

**The investigation is NOT complete until the triage report is posted to Discord
(or session-logged if Discord is unavailable).**

### Step 8: Log investigation outcome to Network Guardian (POST/PATCH lifecycle)

After Discord delivery, **complete the Guardian case diary**. This is Stage 6 of
Convergence — investigation outcomes must land as structured case updates, not
only a one-line message.

The alert receiver already **POST**ed a diary row with status `investigating`
when the alert arrived. Your alert context may include:

```
Guardian event id: <uuid>
Alert fingerprint: <fingerprint>
Guardian site: home
```

**Use the site id from the alert context** (default `home`). Never invent site ids. Expand
`${HOME_API_URL:-$NETWORK_GUARDIAN_URL}` / `${HOME_API_TOKEN:-$NETWORK_GUARDIAN_TOKEN}` via shell
(or use the env values already on the member); never send the literal `${…}` strings.

**Critical (Convergence Docker diary):** diary URL must be the **same stack** the
alert-receiver used when it created the case (usually `http://127.0.0.1:3080` for
Docker Convergence). Do **not** open a second case on a different host. When
`Guardian event id` is present, **always PATCH that id** — never POST a new event
unless PATCH returns 404.

#### Preferred — PATCH the open case (when event id is present)

```bash
curl -sS -X PATCH "${HOME_API_URL:-$NETWORK_GUARDIAN_URL}/api/events/<Guardian-event-id>?site=home" \
  -H "Authorization: Bearer ${HOME_API_TOKEN:-$NETWORK_GUARDIAN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "<resolved|escalated>",
    "severity": "<ok|info|watch|alert>",
    "message": "<one-line summary of finding and outcome>",
    "investigation_notes": "<concise findings from Steps 1-6; evidence checked>",
    "root_cause": "<classification: plain-language detail>"
  }'
```

Expect HTTP 200. If PATCH returns 404, fall back to POST below.

#### Fallback — POST a complete outcome (no event id)

```bash
curl -sS -X POST "${HOME_API_URL:-$NETWORK_GUARDIAN_URL}/api/events?site=home" \
  -H "Authorization: Bearer ${HOME_API_TOKEN:-$NETWORK_GUARDIAN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "<one-line summary of finding and outcome>",
    "severity": "<ok|info|watch|alert>",
    "category": "<wan|wifi|security|bandwidth|monitoring|system>",
    "source": "netclaw",
    "alert_name": "<alertname>",
    "alert_fingerprint": "<fingerprint if known>",
    "status": "<resolved|escalated>",
    "investigation_notes": "<concise findings>",
    "root_cause": "<classification: detail>"
  }'
```

**Status after investigation:**
| Outcome | `status` |
|---------|----------|
| Closed / all-clear / benign / synthetic test | `resolved` |
| Needs human action | `escalated` |
| Only if you cannot classify | `logged` (last resort) |

**Severity mapping:**
| Triage outcome | Event severity |
|----------------|----------------|
| Alert resolved / all-clear / synthetic healthy | `ok` |
| Informational finding, no action needed | `info` |
| Degraded but not critical, monitoring | `watch` |
| Active problem requiring human action | `alert` |

**Do not leave the case stuck at `investigating`.** The diary is useless without
`investigation_notes` and `root_cause`.

**Example PATCH body:**
```json
{
  "status": "resolved",
  "severity": "ok",
  "message": "ConvergencePipeTest on pfsense: synthetic test — pfSense healthy, no action",
  "investigation_notes": "Confirmed synthetic pipe test. system_status: CPU 11%, memory OK, WAN up.",
  "root_cause": "external: synthetic ConvergencePipeTest (no fault)"
}
```

### Step 9: Snapshot case to RAG (Stage 7 — learn for next time)

After Step 8 succeeds with a **resolved** or **escalated** case that has
`investigation_notes` + `root_cause`, snapshot it into the local RAG knowledge
base so the next similar alert can reuse the finding.

**Preferred (links `rag_document_id` on the Guardian event):**

```bash
curl -sS -X POST "${ALERT_RECEIVER_URL:-http://127.0.0.1:8099}/snapshot" \
  -H "Content-Type: application/json" \
  -d '{"event_id":"<Guardian-event-id>","site":"home"}'
```

Expect `{"status":"success","snapshot_id":"snap_…"}`. If the endpoint is
unreachable, fall back to the `rag_snapshot` tool with a short markdown
narrative (alert name, device, findings, root cause).

**Do not snapshot** empty cases or pure noise without notes. Skip if Step 8 failed.

## Prior investigations + vendor docs (Stage 7 — at start of investigation)

The alert receiver may inject **PRIOR INVESTIGATION HITS** into the alert
context from local RAG (`collection=investigations`). When present:

1. Read them first (before deep diagnostics).
2. If a prior root cause class fits, do a **quick live confirm** then reuse it.
3. Search prior cases:
   `rag_search(query="<alertname> <device>", collection="investigations")`
4. Search operator-uploaded vendor / standard docs (HUD Knowledge):
   `rag_search(query="<platform> <feature> <symptom>", collection="documents")`
   Optional filters: `doc_type` = `vendor` | `standard` | `customer` | `install-guide`

## Autonomous Mode

When triggered by the alert receiver webhook:
1. Execute the full procedure without asking for permission
2. Do NOT remediate — investigation and reporting only
3. Always produce the Step 6 triage report
4. **Always deliver the report to Discord** (Step 7) — this is not optional
5. Complete Guardian case (Step 8) and **RAG snapshot (Step 9)** when resolved/escalated
6. If alert status is "resolved", post a brief all-clear to the same channel

## Interactive Follow-ups

After a triage, the user often asks follow-up questions ("what port is X connecting
to?", "what's the DHCP range?", "look at the ARP table"). The Investigation
Principles apply here too:
- Answer with the MCP tool that fits the question (see the table above), don't
  default to "SSH in and run this command."
- If the user says "we already have X configured, why aren't you using it?" —
  they're right. Stop recommending, query the existing data source, and answer.

## Escalation

| Finding | Action |
|---------|--------|
| pfSense unreachable | Check upstream connectivity, physical link |
| Switch interface down | Check cable, negotiate settings, SFP |
| Proxmox node high memory | Identify top VMs, check for memory leaks |
| Multiple devices down | Likely upstream/power issue — investigate in order |
| Root cause unclear | Gather more data, ask human for guidance |

## Example PromQL

```promql
# Is the device up?
up{instance="pfsense"}

# CPU usage over last 15m
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",instance="r640-pve"}[5m])) * 100)

# Memory usage
1 - (node_memory_MemAvailable_bytes{instance="r640-pve"} / node_memory_MemTotal_bytes{instance="r640-pve"})

# Network traffic
rate(node_network_receive_bytes_total{instance="r640-pve"}[5m]) * 8
```
