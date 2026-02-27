---
name: te-network-monitoring
description: Cisco ThousandEyes — test management, agent inventory, test results, dashboards, path visualization, user/account management
version: 1.0.0
tags: [cisco, thousandeyes, monitoring, network-tests, agents, dashboards, path-vis]
---

# ThousandEyes Network Monitoring

Query Cisco ThousandEyes network intelligence via two MCP servers — the community server (9 tools, local stdio) for core monitoring and the official server (~20 tools, remote HTTP) for advanced analysis. Monitor synthetic tests, inspect agent health, view path visualizations, query dashboards, and investigate network events.

## MCP Servers

### Community Server (local, stdio)

- **Repository**: [CiscoDevNet/thousandeyes-mcp-community](https://github.com/CiscoDevNet/thousandeyes-mcp-community)
- **Transport**: stdio (Python)
- **Install**: `git clone` + `pip install -r requirements.txt`
- **Script**: `src/server.py`
- **Python**: 3.12+
- **Requires**: `TE_TOKEN`
- **Status**: Alpha/MVP, read-only

### Official Server (remote, HTTP)

- **Repository**: [CiscoDevNet/ThousandEyes-MCP-Server-official](https://github.com/CiscoDevNet/ThousandEyes-MCP-Server-official)
- **Endpoint**: `https://api.thousandeyes.com/mcp`
- **Transport**: Remote HTTP (via `npx mcp-remote`)
- **Auth**: Bearer token (`Authorization: Bearer <TE_TOKEN>`)
- **No local install** — hosted by Cisco
- **Requires**: `TE_TOKEN`, Node.js (for npx), org not opted out of AI features

## Community Server Tools (9)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `te_list_tests` | `aid?, name_contains?, test_type?` | List all configured tests with filtering by name, type, or account group |
| `te_list_agents` | `agent_types?, aid?` | List enterprise, enterprise-cluster, and cloud agents |
| `te_get_test_results` | `test_id, test_type, window?/start?/end?/aid?/agent_id?` | Fetch network, page-load, and web-transaction test results |
| `te_get_path_vis` | `test_id, window?/start?/end?/aid?/agent_id?/direction?` | Path visualization — hop-by-hop network path data |
| `te_list_dashboards` | `aid?, title_contains?` | List all ThousandEyes dashboards |
| `te_get_dashboard` | `dashboard_id, aid?` | Dashboard details including widget inventory |
| `te_get_dashboard_widget` | `dashboard_id, widget_id, window?/start?/end?/aid?` | Widget data for a specific dashboard widget |
| `te_get_users` | none | List users in the ThousandEyes account |
| `te_get_account_groups` | none | List account groups accessible to the authenticated org |

## Official Server Tools (~20)

### Core Monitoring
| Tool | What It Does |
|------|--------------|
| List Tests | View all configured tests (web, network, DNS, voice) |
| Get Test Details | Detailed information about a specific test |
| List Events | Find network and application problems within time ranges |
| Get Event Details | Deep dive into specific events with impacted targets |
| List Alerts | View triggered or cleared alert rules |
| Get Alert Details | Comprehensive alert information with conditions and targets |
| Search Outages | Find network and application outages with filters |
| Instant Tests | **Active troubleshooting** — run tests on demand |

### Advanced Analysis
| Tool | What It Does |
|------|--------------|
| Get Anomalies | Detect metric anomalies in test data over time |
| Get Metrics | Retrieve aggregated metrics for dashboards and reports |
| Views Explanations | **AI-powered** — explain specific test results and visualizations |

### Endpoint Monitoring
| Tool | What It Does |
|------|--------------|
| List Endpoint Agents and Tests | List endpoint agents with filtering |
| Get Endpoint Agent Metrics | Time series data from endpoint agents |

### Network Path & BGP Analysis
| Tool | What It Does |
|------|--------------|
| Get Path Visualization | Network paths and hop-by-hop routing |
| Get Full Path Visualization | Comprehensive path data for all agents |
| Get BGP Test Results | BGP reachability and routing information |
| Get BGP Route Details | Detailed AS path and routing information |

### Account Management
| Tool | What It Does |
|------|--------------|
| Get Account Groups | List available account groups |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **Test** | Synthetic monitoring probe — HTTP, page load, web transaction, network (ICMP/TCP), DNS, voice, SIP |
| **Agent** | ThousandEyes vantage point — Enterprise (on-prem), Enterprise Cluster (distributed), Cloud (Cisco-hosted global) |
| **Path Visualization** | Hop-by-hop network path from agent to target — shows each router, latency per hop, loss, MPLS labels |
| **Event** | Detected network or application problem — outage, latency spike, packet loss, DNS failure |
| **Alert Rule** | Threshold-based trigger — fires when metrics exceed defined conditions |
| **Dashboard** | Custom visualization with widgets — aggregated views of test data, metrics, and alerts |
| **Endpoint Agent** | Lightweight agent on user workstations — monitors real user experience (WiFi, VPN, SaaS) |
| **Instant Test** | On-demand test execution — active troubleshooting without waiting for scheduled test cycles |
| **BGP Route** | BGP reachability data — AS path, prefix, origin, route visibility from ThousandEyes BGP monitors |

## Workflow: Network Performance Assessment

When a user asks "how's the network performing?":

1. **List tests**: `te_list_tests` — discover all configured monitoring tests
2. **Test results**: `te_get_test_results` for key network tests — latency, loss, jitter
3. **Alerts**: List Alerts (official) — any active alert conditions
4. **Events**: List Events (official) — recent network/application problems
5. **Dashboards**: `te_list_dashboards` + `te_get_dashboard_widget` — executive summary metrics
6. **Report**: network performance dashboard with test-by-test metrics and alert status

## Workflow: Path Troubleshooting

When investigating "traffic to example.com is slow from the London office":

1. **Find test**: `te_list_tests` filtered by name or target
2. **Path visualization**: `te_get_path_vis` for the relevant test — hop-by-hop path
3. **Full path**: Get Full Path Visualization (official) — all agents, all paths
4. **BGP routes**: Get BGP Route Details (official) — is traffic taking an unexpected AS path?
5. **Anomalies**: Get Anomalies (official) — metric deviations over time
6. **Report**: path analysis with hop-by-hop latency, loss source, and routing assessment

## Workflow: Outage Investigation

When responding to a ThousandEyes alert:

1. **Alerts**: List Alerts (official) — active alert details, affected tests
2. **Events**: List Events (official) + Get Event Details — timeline, impacted targets
3. **Outages**: Search Outages (official) — broader outage scope (ISP, CDN, SaaS)
4. **Path vis**: `te_get_path_vis` — where in the path is the problem?
5. **Instant test**: Instant Tests (official) — run on-demand tests from multiple agents
6. **Report**: outage timeline with root cause (ISP node X, hop Y, BGP route change)

## Workflow: Endpoint Experience

When investigating "users complain about slow VPN":

1. **Endpoint agents**: List Endpoint Agents and Tests (official) — find agents on affected users
2. **Metrics**: Get Endpoint Agent Metrics (official) — WiFi signal, VPN latency, DNS response
3. **Path vis**: Get Path Visualization (official) — user-to-VPN-gateway path
4. **Correlate**: compare with enterprise agent test results — is it user-side or network-side?
5. **Report**: endpoint experience analysis with WiFi, VPN, and path diagnostics

## Workflow: BGP Monitoring

When auditing BGP health:

1. **BGP tests**: `te_list_tests` filtered by type=bgp
2. **BGP results**: Get BGP Test Results (official) — reachability, prefix visibility
3. **Route details**: Get BGP Route Details (official) — AS paths, origin validation
4. **Anomalies**: Get Anomalies (official) — BGP metric deviations
5. **Report**: BGP health summary with route stability assessment

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `pyats-routing` | ThousandEyes external BGP view + pyATS internal routing state = full picture |
| `pyats-troubleshoot` | ThousandEyes path vis (internet view) + pyATS show commands (device view) |
| `aws-network-ops` | ThousandEyes cloud agent tests + AWS VPC flow logs for hybrid visibility |
| `gcp-cloud-monitoring` | ThousandEyes metrics + GCP Cloud Monitoring for cross-platform correlation |
| `meraki-monitoring` | ThousandEyes synthetic tests + Meraki Dashboard live diagnostics |
| `fmc-firewall-ops` | ThousandEyes path vis through firewall + FMC rule audit |
| `servicenow-change-workflow` | ThousandEyes alerts trigger ServiceNow incidents |
| `gait-session-tracking` | Record all ThousandEyes investigations in GAIT audit trail |
| `slack-network-alerts` | Deliver ThousandEyes alert summaries to Slack channels |

## Important Rules

- **Read-only** — community server is read-only; official server has Instant Tests (on-demand test execution)
- **API rate limits** — ThousandEyes API usage counts against your org's rate limit; avoid rapid-fire queries
- **Account group scope** — queries default to the authenticated user's account group; specify `aid` for cross-group queries
- **AI features** — official server requires org not opted out of ThousandEyes AI features
- **Time windows** — use `window` (seconds) or `start`/`end` (ISO 8601) for time-bounded queries
- **Record in GAIT** — log all ThousandEyes investigations for audit trail

## Environment Variables

- `TE_TOKEN` — ThousandEyes API v7 OAuth bearer token (used by both community and official servers)
