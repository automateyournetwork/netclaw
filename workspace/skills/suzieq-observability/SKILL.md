---
name: suzieq-observability
description: "SuzieQ network observability — query current and historical network state, run validation assertions, get summary statistics, trace forwarding paths, and discover unique values across 20+ network tables. Use when investigating BGP/OSPF state, checking interface health, performing time-travel queries, validating network assertions, or tracing packet paths through the network via SuzieQ."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["SUZIEQ_API_URL", "SUZIEQ_API_KEY"] } } }
---

# SuzieQ Network Observability

## Server & Configuration

- **Server script:** `mcp-servers/suzieq-mcp/server.py`
- **Transport:** stdio (JSON-RPC 2.0)
- **Environment variables:** `SUZIEQ_API_URL`, `SUZIEQ_API_KEY`
- **Optional:** `SUZIEQ_VERIFY_SSL` (default: true), `SUZIEQ_TIMEOUT` (default: 30s)

## All 5 Available Tools

### 1. `suzieq_show`

Query detailed network state data from any SuzieQ table. Supports filtering by device, namespace, time range, and columns. Use for current or historical (time-travel) network state queries.

- `table` (string, required): SuzieQ table name (e.g., "bgp", "route", "interface")
- `namespace` (string): Filter by SuzieQ namespace
- `hostname` (string): Filter by device hostname
- `columns` (string): Comma-separated column names to return
- `start_time` (string): Start time for time-travel query (ISO 8601 or relative e.g., "1h", "2d")
- `end_time` (string): End time for time-travel query
- `view` (string): Data view: "latest", "all", or "changes"
- `filters` (string): Additional key=value pairs separated by ampersand

**Use when:** Querying current network state, investigating specific devices, performing time-travel queries for historical analysis.

### 2. `suzieq_summarize`

Get aggregated statistics and summary views of any SuzieQ network table. Returns counts, distributions, and per-device breakdowns.

- `table` (string, required): SuzieQ table name
- `namespace` (string): Filter by SuzieQ namespace
- `hostname` (string): Filter by device hostname
- `start_time` (string): Start time for historical summary
- `end_time` (string): End time for historical summary

**Use when:** Getting high-level network overview, distribution analysis, capacity planning.

### 3. `suzieq_assert`

Run validation assertions against network state. Checks conditions like "all BGP peers established" or "no interface errors".

- `table` (string, required): Must be one of: bgp, ospf, interface, evpnVni
- `namespace` (string): Filter by SuzieQ namespace
- `hostname` (string): Filter by device hostname

**Use when:** Validating network health, pre/post-change verification, compliance checks.

### 4. `suzieq_unique`

Get distinct values and their counts for a specific column in a SuzieQ table.

- `table` (string, required): SuzieQ table name
- `column` (string, required): Column name to get unique values for
- `namespace` (string): Filter by SuzieQ namespace
- `hostname` (string): Filter by device hostname

**Use when:** Understanding value distributions (unique VRFs, BGP states, interface types).

### 5. `suzieq_path`

Trace the forwarding path between two endpoints through the network.

- `namespace` (string, required): SuzieQ namespace
- `source` (string, required): Source IP address
- `destination` (string, required): Destination IP address
- `vrf` (string): VRF name (default: "default")

**Use when:** Troubleshooting connectivity, verifying forwarding paths, path analysis.

## Workflow

1. Start with `suzieq_show` or `suzieq_summarize` to understand current network state
2. Use `suzieq_assert` to validate health (BGP established, OSPF full, interfaces up)
3. Use `suzieq_unique` to explore value distributions for specific columns
4. Use `suzieq_path` to trace forwarding paths between endpoints
5. Use `start_time`/`end_time` on show/summarize for time-travel historical analysis

## Supported Tables

address, arpnd, bgp, device, devconfig, evpnVni, fs, ifCounters, interface, inventory, lldp, mac, mlag, namespace, network, ospf, route, sqPoller, topology, vlan
