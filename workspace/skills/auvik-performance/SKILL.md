---
name: auvik-performance
description: "Auvik time-series performance stats for devices, interfaces, services, and hardware components — plus SNMP poller history for custom OID values. Use when checking device CPU or memory utilization over time, reviewing interface throughput or packet loss, checking service (ping) latency, pulling component-level stats (fan temperature, PSU power), or querying custom SNMP poller values."
license: Apache-2.0
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["AUVIK_USERNAME", "AUVIK_API_KEY", "AUVIK_BASE_URL"] } } }
---

# Auvik Performance

Query time-series performance statistics from the Auvik monitoring platform: device CPU, memory, bandwidth, and availability; interface throughput and error rates; service (ping) latency; hardware component metrics; and custom SNMP poller values. All data is read-only and sourced from Auvik's collected telemetry.

## MCP Server

- **Server**: `auvik-mcp` (NetClaw MCP, Feature 036)
- **Command**: `python3 mcp-servers/auvik-mcp/auvik_mcp_server.py` (stdio transport)
- **Auth**: Basic auth via `AUVIK_USERNAME` + `AUVIK_API_KEY`
- **Read-only**: GET operations only — no write or configuration changes

## Available Tools

| Tool | What It Does |
|------|--------------|
| `auvik_get_device_statistics` | Time-series device stats (CPU, memory, bandwidth, packet rates) or availability stats (uptime, outage); `stat_id`, `from_time`, `interval` required |
| `auvik_get_interface_statistics` | Time-series interface stats (bandwidth, utilization, packet loss, discards, multicast, unicast, broadcast); `stat_id`, `from_time`, `interval` required |
| `auvik_get_service_statistics` | Time-series service (ping) stats — `pingTime` (latency) or `pingPacket` (packet loss); `stat_id`, `from_time`, `interval` required |
| `auvik_get_component_statistics` | Time-series hardware component stats (temperature, power, utilization, capacity); `component_type`, `stat_id`, `from_time`, `interval` required |
| `auvik_get_oid_statistics` | Point-in-time current OID values from `/v1/stat/oid/deviceMonitor`; no time window — returns the most recent polled value |
| `auvik_list_snmp_poller_settings` | List configured SNMP poller definitions; `tenants` required; `with_devices=true` lists devices assigned to a poller |
| `auvik_get_snmp_poller_history` | Historical SNMP poller time-series; `tenants` and `from_time` required; `value_type=int` requires `interval`; `value_type=string` accepts `compact` |

## Key Concepts

**Tenants = MSP clients.** Performance tools accept an optional `tenants` parameter. Scope to a specific client to avoid cross-tenant data mixing.

**Identifier resolution.** `device` and `parent_device` parameters accept hostnames, IPs, or partial names — resolved automatically to Auvik IDs. The `interface` parameter on `auvik_get_interface_statistics` also resolves from name or parent device. Ambiguous matches return `ResolutionCandidate[]`.

**`from_time` and `interval` are required on all time-series tools.** `from_time` accepts ISO-8601 datetimes or relative shorthand (e.g., `-1h`, `-7d`, `-30d`) which the server converts to ISO-8601. `interval` must be `minute`, `hour`, or `day`. `thru_time` is optional — defaults to now.

**`stat_id` enums by tool.** Each tool has a fixed set of valid `stat_id` values:

| Tool | Valid `stat_id` values |
|------|------------------------|
| `auvik_get_device_statistics` (standard) | `bandwidth`, `cpuUtilization`, `memoryUtilization`, `storageUtilization`, `packetUnicast`, `packetMulticast`, `packetBroadcast` |
| `auvik_get_device_statistics` (availability; set `availability=true`) | `uptime`, `outage` |
| `auvik_get_interface_statistics` | `bandwidth`, `utilization`, `packetLoss`, `packetDiscard`, `packetMulticast`, `packetUnicast`, `packetBroadcast` |
| `auvik_get_service_statistics` | `pingTime`, `pingPacket` |
| `auvik_get_component_statistics` | `capacity`, `counters`, `idle`, `latency`, `power`, `queueLatency`, `rate`, `readiness`, `ready`, `speed`, `swap`, `swapRate`, `temperature`, `totalLatency`, `utilization` |

**`component_type` on `auvik_get_component_statistics`.** Valid values: `cpu`, `cpuCore`, `disk`, `fan`, `memory`, `powerSupply`, `systemBoard`. Both `component_type` and `stat_id` are required.

**SNMP poller flow.** Custom SNMP polling is a two-step operation: (1) `auvik_list_snmp_poller_settings` to discover poller IDs and associated devices; (2) `auvik_get_snmp_poller_history` to pull time-series values for a specific poller. `tenants` is required on both calls. `value_type=int` returns numeric time-series (requires `interval`); `value_type=string` returns string-valued OID snapshots (use `compact=true` to reduce payload size).

**`auvik_get_oid_statistics` vs. `auvik_get_snmp_poller_history`.** `auvik_get_oid_statistics` returns the most recent polled value for any OID on a device — no time window, no interval. Use it for a quick "what is the current value?" check. Use `auvik_get_snmp_poller_history` for trend analysis over time.

**Pagination.** `auvik_get_oid_statistics` and `auvik_list_snmp_poller_settings` support cursor pagination. Time-series tools return data arrays directly. Use `fetch_all=false` + `page_first` for large poller inventories.

## Workflow

### Device Health Check (CPU and Memory Trend)

1. **Start GAIT branch**: `gait_branch` with name like `auvik-perf-check-<device>-2026-06-21`
2. **CPU utilization**: `auvik_get_device_statistics` with `stat_id=cpuUtilization`, `device=<hostname>`, `from_time=-24h`, `interval=hour`
3. **Memory utilization**: re-run with `stat_id=memoryUtilization`, same device and window
4. **Bandwidth**: re-run with `stat_id=bandwidth` to check overall traffic load
5. **Availability**: `auvik_get_device_statistics` with `availability=true`, `stat_id=uptime`, same device and window — confirm no outage periods during the review window
6. **Record in GAIT**: commit performance findings with peak values, average utilization, and any anomalies noted

### Interface Throughput Review

1. **Identify interfaces**: `auvik-inventory` (`auvik_list_interfaces`) with `parent_device=<hostname>` — enumerate interface names
2. **Bandwidth stats**: `auvik_get_interface_statistics` with `stat_id=bandwidth`, `parent_device=<hostname>`, `from_time=-7d`, `interval=hour`
3. **Packet loss**: re-run with `stat_id=packetLoss` — identify any interfaces with elevated loss
4. **Discards**: re-run with `stat_id=packetDiscard` — input/output queue drops signal congestion
5. **Record in GAIT**: commit interface performance summary with top-utilization interfaces and any loss/discard findings

### Custom SNMP Poller Investigation

1. **List poller settings**: `auvik_list_snmp_poller_settings` with `tenants=<client>` — discover available custom pollers and their IDs
2. **Find poller devices**: re-run with `poller_id=<id>`, `with_devices=true` — confirm which devices report to this poller
3. **Pull numeric history**: `auvik_get_snmp_poller_history` with `tenants=<client>`, `value_type=int`, `snmp_poller_setting_id=<id>`, `from_time=-30d`, `interval=hour`
4. **Pull string history** (if applicable): re-run with `value_type=string`, `compact=true`
5. **Spot-check current value**: `auvik_get_oid_statistics` with `device=<hostname>`, `oid=<oid-string>` for a point-in-time reading
6. **Record in GAIT**: commit poller findings with OID, device, value trend, and any threshold concerns

### Component Temperature / Power Audit

1. **Fan temperature**: `auvik_get_component_statistics` with `component_type=fan`, `stat_id=temperature`, `parent_device=<hostname>`, `from_time=-24h`, `interval=hour`
2. **PSU power**: re-run with `component_type=powerSupply`, `stat_id=power`
3. **Memory utilization (component-level)**: re-run with `component_type=memory`, `stat_id=utilization`
4. **Disk capacity**: re-run with `component_type=disk`, `stat_id=capacity`
5. **Record in GAIT**: commit component health summary with peak values

## Integration with Other Skills

| Skill | How They Work Together |
|-------|------------------------|
| `gait-session-tracking` | **Mandatory** — start a branch before querying, record every turn, close with `gait_log` |
| `auvik-inventory` | Discover device and interface names to use as `device` and `parent_device` params here |
| `auvik-network-alerts` | Correlate performance anomalies with alerts that fired in the same time window |
| `auvik-lifecycle` | High CPU/memory on aging devices combined with EoL status accelerates refresh priority |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AUVIK_USERNAME` | Yes | Auvik user email (Basic-auth username) |
| `AUVIK_API_KEY` | Yes | Auvik API key (Basic-auth password) |
| `AUVIK_BASE_URL` | No | Regional cluster URL; defaults to `https://auvikapi.us1.my.auvik.com` — swap `us1` for your region |
| `AUVIK_VERIFY_SSL` | No | Set `false` to skip TLS verification (not recommended) |
| `AUVIK_TIMEOUT` | No | HTTP timeout in seconds (default: `30`) |
| `AUVIK_MAX_PAGES` | No | Pagination safety cap for poller settings (default: `50`) |

## Important Rules

- **Read-only** — this skill queries Auvik-collected telemetry only. It cannot configure SNMP pollers, change polling intervals, or modify device settings.
- **`stat_id`, `from_time`, and `interval` are required** on all time-series tools. Omitting any one returns a `ValidationError`.
- **`component_type` is also required** on `auvik_get_component_statistics` — specify the hardware subsystem (e.g., `fan`, `memory`) before choosing the `stat_id`.
- **`tenants` is required** on `auvik_list_snmp_poller_settings` and `auvik_get_snmp_poller_history` — the Auvik API enforces this for custom poller endpoints.
- **`auvik_get_oid_statistics` returns point-in-time data only** — it does not accept `from_time` or `interval`. Use `auvik_get_snmp_poller_history` for trend analysis.
- **Refer to devices by name or IP**, not by Auvik internal IDs. The resolver handles lookup; raw IDs in prompts are fragile and tenant-specific.
- **Record every session in GAIT** — all performance queries, trend findings, and SNMP poller investigations must be committed to the audit trail.
