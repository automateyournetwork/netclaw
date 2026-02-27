---
name: te-path-analysis
description: Cisco ThousandEyes — path visualization, BGP route analysis, outage investigation, instant tests, endpoint agent diagnostics
version: 1.0.0
tags: [cisco, thousandeyes, path-vis, bgp, outage, instant-test, endpoint, troubleshooting]
---

# ThousandEyes Path Analysis & Troubleshooting

Deep network path analysis and active troubleshooting via Cisco ThousandEyes — visualize hop-by-hop network paths, analyze BGP routing, investigate outages, run instant on-demand tests, and diagnose endpoint agent connectivity. Combines community (local) and official (remote) MCP servers.

## MCP Servers

- **Community**: `src/server.py` (stdio, Python 3.12+) — `te_get_path_vis` for path visualization
- **Official**: `https://api.thousandeyes.com/mcp` (remote HTTP) — full path vis, BGP, instant tests, anomalies, endpoint agents

## Key Capabilities

### Path Visualization

| Source | Tool | What It Does |
|--------|------|--------------|
| Community | `te_get_path_vis` | Hop-by-hop path from a specific agent to the test target |
| Official | Get Path Visualization | Network paths with routing details |
| Official | Get Full Path Visualization | Comprehensive path data aggregated across all agents |

Path visualization shows every network hop between agent and target:
- **IP address** and **DNS name** of each hop
- **Latency** per hop (pinpoints where delay is introduced)
- **Packet loss** per hop (identifies lossy links)
- **MPLS labels** (reveals traffic engineering paths)
- **Network owner** (ISP/carrier identification per hop)

### BGP Route Analysis

| Tool | What It Does |
|------|--------------|
| Get BGP Test Results | BGP reachability — which BGP monitors see the prefix, which don't |
| Get BGP Route Details | AS path, origin AS, prefix length, route stability |

BGP analysis provides external routing visibility:
- **Prefix reachability** from ThousandEyes' global BGP monitor fleet
- **AS path** — is traffic routing through expected carriers?
- **Route changes** — detect BGP hijacks, leaks, or suboptimal routing
- **Origin validation** — verify the prefix originates from the correct AS

### Outage Investigation

| Tool | What It Does |
|------|--------------|
| Search Outages | Find network and application outages with time/scope filters |
| List Events | Network/application problems with affected targets |
| Get Event Details | Deep dive: impacted tests, affected agents, timeline |

### Active Troubleshooting

| Tool | What It Does |
|------|--------------|
| Instant Tests | Run tests on demand from selected agents — don't wait for scheduled cycles |
| Get Anomalies | Detect metric deviations from baseline over time |
| Views Explanations | AI-powered explanation of test results and visualizations |

### Endpoint Diagnostics

| Tool | What It Does |
|------|--------------|
| List Endpoint Agents and Tests | Endpoint agents on user workstations with test associations |
| Get Endpoint Agent Metrics | WiFi signal, VPN tunnel latency, DNS response, HTTP performance |

## Workflow: "Why Is Site X Slow?"

The classic ThousandEyes troubleshooting workflow:

1. **Identify test**: `te_list_tests` (community) filtered by target site
2. **Check results**: `te_get_test_results` (community) — is latency elevated? Packet loss?
3. **Path visualization**: `te_get_path_vis` (community) — hop-by-hop analysis
4. **Full path**: Get Full Path Visualization (official) — all agents, compare paths
5. **Pinpoint hop**: identify the hop where latency spikes or loss appears
6. **BGP check**: Get BGP Route Details (official) — is routing suboptimal?
7. **Anomalies**: Get Anomalies (official) — when did the degradation start?
8. **Report**: "Latency increase traced to hop 7 (ISP-X backbone router 203.0.113.45). AS path changed at 14:32 UTC — traffic now routing through AS 64512 instead of direct peering. BGP route via AS 65001 withdrawn."

## Workflow: Internet Outage Triage

When ThousandEyes detects a broad outage:

1. **Search outages**: Search Outages (official) — scope: ISP, CDN, SaaS provider?
2. **Events**: List Events (official) — which tests are affected?
3. **Event details**: Get Event Details (official) — impacted targets, severity, timeline
4. **Path vis**: `te_get_path_vis` (community) for affected tests — where does the path break?
5. **BGP**: Get BGP Test Results (official) — prefix still reachable? Route withdrawn?
6. **Instant test**: Instant Tests (official) — verify from multiple cloud agents
7. **Report**: outage scope, affected services, root cause, estimated provider recovery

## Workflow: Endpoint VPN Troubleshooting

When users report VPN issues:

1. **List endpoint agents**: List Endpoint Agents and Tests (official) — affected users
2. **Endpoint metrics**: Get Endpoint Agent Metrics (official) — WiFi signal, DNS, VPN latency
3. **Path visualization**: Get Path Visualization (official) — user to VPN gateway path
4. **Compare**: run enterprise agent test to same VPN gateway — is it user-side?
5. **Anomalies**: Get Anomalies (official) — when did metrics degrade?
6. **Report**: "User WiFi signal -72 dBm (poor), DNS response 450ms (ISP DNS slow). VPN tunnel latency 180ms due to WiFi retransmissions. Recommend: switch to 5 GHz band, use corporate DNS."

## Workflow: BGP Hijack / Leak Detection

When validating BGP route security:

1. **BGP tests**: `te_list_tests` (community) filtered by BGP test type
2. **BGP results**: Get BGP Test Results (official) — reachability from global monitors
3. **Route details**: Get BGP Route Details (official) — AS paths from all vantage points
4. **Anomalies**: unexpected AS in path? Prefix originated from wrong AS?
5. **Path vis**: Get Full Path Visualization (official) — confirm traffic follows expected path
6. **Cross-reference**: `pyats-routing` for internal BGP state confirmation
7. **Report**: BGP security assessment with route origin validation

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `te-network-monitoring` | Monitoring provides context (tests, dashboards), path analysis provides deep investigation |
| `pyats-routing` | ThousandEyes external BGP + pyATS internal BGP = complete routing picture |
| `pyats-troubleshoot` | ThousandEyes internet path + pyATS device-level CLI diagnostics |
| `meraki-security-appliance` | ThousandEyes path through MX + Meraki VPN status for SD-WAN troubleshooting |
| `aws-network-ops` | ThousandEyes cloud agent + AWS VPC flow logs for hybrid path analysis |
| `fmc-firewall-ops` | ThousandEyes path vis shows traffic traversing FTD + FMC rule analysis |
| `servicenow-change-workflow` | Outage events trigger ServiceNow incidents with ThousandEyes evidence |
| `gait-session-tracking` | Record all path analysis and troubleshooting in GAIT |

## Important Rules

- **Instant Tests consume test units** — use judiciously; each run counts against your ThousandEyes license
- **Path visualization requires network layer tests** — HTTP server tests won't show full path data
- **BGP monitors are global** — ThousandEyes has 300+ BGP vantage points; results reflect internet-wide routing
- **Endpoint agents need permission** — endpoint data is privacy-sensitive; respect data governance
- **Time ranges matter** — narrow queries to the incident window to reduce API load and improve relevance
- **Record in GAIT** — log all path analysis, outage investigations, and BGP findings

## Environment Variables

- `TE_TOKEN` — ThousandEyes API v7 OAuth bearer token (shared with te-network-monitoring)
