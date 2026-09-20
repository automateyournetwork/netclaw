---
name: gtrace-path-analysis
description: "Network path tracing and monitoring — traceroute with MPLS/ECMP/NAT detection, continuous MTR monitoring, and distributed GlobalPing probes from 500+ worldwide locations. Use when tracing the path to a destination, diagnosing slow network routes, detecting MPLS or ECMP load balancing, running MTR for intermittent packet loss, or testing reachability from global vantage points. Works standalone from this host, no external platform required; if Cisco ThousandEyes agents are already deployed, prefer `te-path-analysis` for BGP route analysis and agent-based outage investigation. For public-probe-only checks with no local traceroute/MTR, `globalping-external-checks` has the critical guidance on interpreting GlobalPing's no-probe vs. unreachable responses."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "gtrace"], "env": ["GTRACE_MCP_BIN"] } } }
---

# Network Path Analysis with gtrace

## How to Call the gtrace MCP Tools

```bash
python3 $MCP_CALL "gtrace mcp" TOOL_NAME '{"param":"value"}'
```

## When to Use

- Trace the path between two endpoints and identify each hop (router, latency, loss)
- Detect MPLS labels, ECMP load balancing, and NAT translation points along the path
- Monitor a path continuously with MTR to identify intermittent packet loss or latency spikes
- Run distributed traceroutes from 500+ GlobalPing probe locations worldwide to compare paths from different vantage points
- Verify transit providers, peering, and routing policy by inspecting AS-level path data
- Troubleshoot asymmetric routing, suboptimal paths, or blackholes

## Available Tools

| Tool | Purpose | Requirements |
|------|---------|-------------|
| `traceroute` | Advanced traceroute with MPLS, ECMP, and NAT detection | cap_net_raw |
| `mtr` | Continuous MTR monitoring with packet loss and jitter stats | cap_net_raw |
| `globalping` | Distributed traceroute/ping from 500+ worldwide probe locations | Internet access (optional GLOBALPING_API_KEY) |

## Workflow: Path Troubleshooting

When asked "why is traffic slow to X?" or "trace the path to X":

### Step 1: Traceroute

Run an advanced traceroute to see every hop, latency, and any MPLS/ECMP/NAT indicators.

```bash
python3 $MCP_CALL "gtrace mcp" traceroute '{"target":"8.8.8.8"}'
```

For IPv6:

```bash
python3 $MCP_CALL "gtrace mcp" traceroute '{"target":"2001:4860:4860::8888"}'
```

### Step 2: Continuous Monitoring with MTR

If the traceroute shows packet loss or high latency at a specific hop, run MTR to monitor continuously and confirm the problem is persistent.

```bash
python3 $MCP_CALL "gtrace mcp" mtr '{"target":"8.8.8.8","count":100}'
```

### Step 3: Global Perspective

Compare paths from multiple worldwide locations to determine if the issue is local or global.

```bash
python3 $MCP_CALL "gtrace mcp" globalping '{"target":"8.8.8.8","from":"US,EU,Asia"}'
```

## Workflow: MPLS Path Verification

Verify MPLS label-switched paths and label stacks along the path:

```bash
python3 $MCP_CALL "gtrace mcp" traceroute '{"target":"10.0.0.1"}'
```

Look for MPLS label information in the hop details. Useful for verifying traffic engineering and MPLS VPN paths.

## Workflow: ECMP Load Balancing Verification

Detect if traffic is being load-balanced across multiple equal-cost paths:

```bash
python3 $MCP_CALL "gtrace mcp" traceroute '{"target":"192.168.1.1"}'
```

ECMP detection reveals when multiple next-hops exist at a given TTL, indicating load balancing.

## Tool Parameters

### traceroute
- `target` (required): IP address or hostname to trace

### mtr
- `target` (required): IP address or hostname to monitor
- `count` (optional): Number of probe rounds to send

### globalping
- `target` (required): IP address or hostname to probe
- `from` (optional): Comma-separated list of probe locations (countries, cities, regions, ASNs)

## Output Format

All tools return structured results including:
- **traceroute** — hop number, IP, hostname, RTT per probe, MPLS labels, ECMP paths, NAT detection
- **mtr** — hop number, loss%, sent/recv counts, best/avg/worst/stdev RTT
- **globalping** — per-probe-location results with path data, useful for global path comparison

## Important Rules

- Traceroute and MTR require `cap_net_raw` capability on the gtrace binary (set during install)
- GlobalPing uses the public GlobalPing API — set `GLOBALPING_API_KEY` for higher rate limits
- Always start with a single traceroute before running continuous MTR
- Use GlobalPing to differentiate local vs global path issues
- Cross-reference hop IPs with `asn_lookup` and `geo_lookup` from gtrace-ip-enrichment skill for full context
- Record all path analysis in GAIT

## Failure Behavior

- If a tool call fails with an authentication or connection error, check that `GTRACE_MCP_BIN` is set and valid before assuming a data or device problem.
- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
