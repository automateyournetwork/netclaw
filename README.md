<p align="center">
  <img src="netclaw.jpg" alt="NetClaw — A CCIE-level AI agent that claws through your network" width="600">
</p>

# NetClaw

A CCIE-level AI network engineering coworker. Built on [OpenClaw](https://github.com/openclaw/openclaw) with Anthropic Claude, 82 skills, and 37 MCP server backends for complete network automation with ITSM gating, source-of-truth reconciliation, immutable audit trails, packet capture analysis, GitHub config-as-code, Cisco CML lab simulation, ContainerLab containerized network labs, Cisco NSO orchestration, Cisco SD-WAN vManage monitoring, Grafana observability (dashboards, Prometheus, Loki, alerting, incidents), Prometheus direct PromQL monitoring, Kubeshark Kubernetes traffic analysis, Cisco Meraki Dashboard management, Cisco ThousandEyes network intelligence, AWS cloud networking, Cisco Secure Firewall policy auditing, Itential network orchestration, Juniper JunOS device automation, Arista CloudVision Portal monitoring, F5 BIG-IP pyATS iControl REST coverage, UML diagram generation, live BGP/OSPF control-plane participation, Slack-native operations, and Microsoft 365 integration.

---

## Quick Install

```bash
git clone https://github.com/automateyournetwork/netclaw.git
cd netclaw
./scripts/install.sh          # installs everything, then launches the setup wizard
```

That's it. The installer clones 37 MCP servers, deploys 82 skills, then launches a two-phase setup:

**Phase 1: `openclaw onboard`** (OpenClaw's built-in wizard)
- Pick your AI provider (Anthropic, OpenAI, Bedrock, Vertex, 30+ options)
- Set up the gateway (local mode, auth, port)
- Connect channels (Slack, Discord, Telegram, WhatsApp, etc.)
- Install the daemon service

**Phase 2: `./scripts/setup.sh`** (NetClaw platform credentials)
- Network devices (testbed.yaml editor)
- Platform credentials (NetBox, Nautobot, Infrahub, Itential, ServiceNow, ACI, ISE, F5, Catalyst Center, NVD, Microsoft Graph, GitHub, CML, NSO, Meraki, FMC, ThousandEyes, RADKit, AWS, GCP, ContainerLab, SD-WAN, Grafana, Prometheus, Kubeshark)
- Your identity (name, role, timezone for USER.md)

After setup, start NetClaw:

```bash
openclaw gateway              # terminal 1
openclaw chat --new           # terminal 2
```

Reconfigure anytime:
- `openclaw configure` — AI provider, gateway, channels
- `./scripts/setup.sh` — network platform credentials

---

## What It Does

NetClaw is an autonomous network engineering agent powered by Claude that can:

- **Monitor** device health — CPU, memory, interfaces, hardware, NTP, logs — fleet-wide in parallel
- **Troubleshoot** connectivity, routing adjacencies, performance, and flapping using OSI-layer methodology with multi-hop parallel state collection
- **Analyze** routing protocols — OSPF (LSDB, LSA types, area design), BGP (11-step path selection, NOTIFICATION codes), EIGRP (DUAL states)
- **Audit** security posture — ACLs, AAA, CoPP, management plane hardening, CIS benchmarks, ISE NAD verification, NVD CVE scanning
- **Discover** topology via CDP/LLDP, ARP, routing peers — reconcile against NetBox cables
- **Configure** devices with full ITSM-gated change management — ServiceNow CR, baseline, apply, verify, rollback
- **Reconcile** NetBox or Nautobot source of truth against live device state — flag IP drift, undocumented links, missing interfaces; query Nautobot IPAM for IP addresses, prefixes, VRF/tenant/site filtering when the org uses Nautobot instead of NetBox
- **Manage** ACI fabric — health audits, policy analysis, safe tenant/VRF/BD/EPG changes with fault delta rollback
- **Investigate** endpoints via ISE — auth history, posture, profiling, human-authorized quarantine
- **Audit** Cisco Secure Firewall policies via FMC — search access rules by IP/FQDN, resolve FTD device policies, cross-FMC consistency checks, and SGT-based policy review
- **Manage** Cisco Meraki infrastructure via Dashboard API (~804 endpoints) — org inventory, networks, devices, wireless SSIDs, RF profiles, switch ports, VLANs, MX firewall rules, site-to-site VPN, content filtering, security events, camera analytics, live diagnostics (ping, cable test), and configuration change audit
- **Monitor** network paths via Cisco ThousandEyes — synthetic test results, agent health, hop-by-hop path visualization (latency, loss, MPLS labels per hop), BGP route analysis (AS path, reachability, origin validation), outage investigation, anomaly detection, instant on-demand tests, endpoint VPN diagnostics, and AI-powered views explanations — via both community (9 tools, local stdio) and official (~20 tools, remote HTTP) MCP servers
- **Access** remote devices via Cisco RADKit cloud relay — discover device inventory, inspect device attributes and capabilities, execute CLI commands with timeout/truncation controls, and perform SNMP GET operations on air-gapped or cloud-unreachable devices without direct SSH/SNMP connectivity
- **Automate** Juniper JunOS devices via PyEZ/NETCONF — CLI command execution, configuration management, Jinja2 template rendering, device facts collection, and batch operations across router fleets
- **Monitor** Arista fabric via CloudVision Portal REST API — device inventory, event stream, connectivity monitor status, and device tag management for fleet-wide health assessment
- **Monitor** Cisco SD-WAN fabric via vManage API (read-only) — device inventory (vManage, vSmart, vBond, vEdge), WAN Edge serial/chassis details, device and feature templates, centralized policies, active alarms, audit events, interface statistics, BFD session health, OMP route analysis, DTLS/TLS control connections, and running config retrieval
- **Observe** infrastructure via Grafana (75+ tools) — search/view/modify dashboards, query Prometheus metrics with PromQL (interface traffic, CPU, BGP state, error rates, histogram percentiles), query Loki logs with LogQL (syslog, SNMP traps, application logs), manage alerting rules and contact points, track incidents with timeline activities, view OnCall schedules and current responders, annotate dashboards, render panel images, and generate deep links
- **Query** Prometheus directly (6 tools) — execute instant and range PromQL queries, browse available metrics with pagination, retrieve metric metadata (type, help, unit), inspect scrape target health and status, and verify Prometheus server availability. Supports basic auth, bearer tokens (Grafana Cloud, Thanos, Cortex), and multi-tenant org IDs
- **Inspect** Kubernetes traffic with Kubeshark (6 tools) — capture L4/L7 traffic across cluster pods, export pcaps for Wireshark analysis, create point-in-time snapshots, filter with KFL expressions, list TCP/UDP flows with RTT metrics, and get top-talker summaries. Automatic TLS decryption via eBPF. Dissects HTTP, gRPC, GraphQL, Redis, Kafka, DNS
- **Participate** in BGP and OSPF as a live routing peer — inject/withdraw routes, query RIB/LSDB, adjust LOCAL_PREF and OSPF cost, peer with real routers over GRE tunnels via native protocol speakers (RFC 4271/5340)
- **Scan** for CVE vulnerabilities against the NVD database with CVSS severity correlation and exposure confirmation
- **Manage** F5 BIG-IP load balancers — virtual servers, pools, iRules, stats, and change management
- **Audit** F5 BIG-IP via iControl REST API — LTM virtual servers, pools, nodes, 40+ monitor types, 60+ profile types, iRules, GTM wide IPs, system health (CPU, memory, disk), HA sync-status, certificates, analytics (HTTP, TCP, DNS, DoS), live-update signature freshness
- **Operate** Catalyst Center — device inventory, client monitoring, site management, and troubleshooting
- **Calculate** IPv4 and IPv6 subnets — VLSM planning, wildcard masks, allocation standards
- **Alert** via Slack — severity-formatted notifications, incident workflows, and user-aware routing
- **Diagram** your network with Draw.io topology maps (color-coded by reconciliation status)
- **Visualize** protocol hierarchies as interactive Markmap mind maps
- **Generate** UML and infrastructure diagrams via Kroki — 27+ types including network topology (nwdiag), rack layouts (rackdiag), packet headers (packetdiag), protocol state machines, sequence diagrams, C4 architecture, Mermaid, D2, Graphviz, ERD — output as SVG, PNG, PDF
- **Reference** IETF RFCs and Wikipedia for standards-compliant configuration
- **Store** reports, config backups, and diagrams on SharePoint via Microsoft Graph
- **Generate** Visio topology diagrams from CDP/LLDP discovery and upload to SharePoint
- **Notify** via Microsoft Teams — health alerts, change updates, and report delivery to Teams channels
- **Analyze** packet captures — upload a pcap to Slack and NetClaw runs deep tshark analysis: protocol hierarchy, conversations, endpoints, DNS/HTTP extraction, expert info, and filtered inspection
- **Track** network changes in GitHub — create issues from findings, commit config backups, open PRs for changes, link to ServiceNow CRs
- **Orchestrate** network services via Cisco NSO — retrieve device configs from NSO's CDB, check sync status, inspect operational state, discover service types and deployed instances, platform inventory, and NED management — all via RESTCONF from Slack
- **Simulate** network topologies in Cisco CML — create labs, add nodes, wire links, start/stop labs, execute CLI commands, capture packets on lab links, and manage CML users — all from natural language via Slack
- **Deploy** containerized network labs via ContainerLab — deploy multi-vendor topologies (SR Linux, cEOS, IOS XR, NX-OS, FRR, cRPD), inspect running labs, execute commands on nodes, and destroy labs when done — all through the ContainerLab API
- **Inspect** AWS cloud networking — VPCs, Transit Gateways, Cloud WAN, VPN tunnels, Network Firewalls, flow logs, ENI details, and route tables via 27 read-only AWS Network tools
- **Monitor** AWS CloudWatch — query metrics (VPN tunnel state, NAT GW drops, TGW traffic), check alarms, run Logs Insights queries, analyze VPC flow logs
- **Audit** AWS security — IAM users/roles/policies (read-only), CloudTrail API event history, credential rotation compliance, MFA enforcement
- **Analyze** AWS costs — service breakdowns, network cost drivers (NAT GW, TGW, VPN, data transfer), monthly trends, forecasts, anomaly investigation
- **Diagram** AWS architecture — auto-discover and render VPCs, subnets, TGWs, load balancers as visual topology diagrams (requires graphviz)
- **Audit** every action in an immutable Git-based trail (GAIT) — there is always an answer to "what did the AI do and why"

---

## Architecture

```
Human (Slack / WebChat) --> NetClaw (CCIE Agent on OpenClaw)
                                |
                                |-- DEVICE AUTOMATION:
                                |     MCP: pyATS           --> IOS-XE / NX-OS / IOS-XR devices
                                |     MCP: Juniper JunOS   --> PyEZ / NETCONF (CLI, config, templates)
                                |     MCP: F5 BIG-IP       --> iControl REST (virtuals, pools, iRules)
                                |     MCP: Catalyst Center --> DNA-C API (devices, clients, sites)
                                |     MCP: Arista CVP      --> CloudVision REST API (inventory, events, tags)
                                |
                                |-- INFRASTRUCTURE:
                                |     MCP: Cisco ACI       --> APIC / ACI fabric
                                |     MCP: Cisco ISE       --> Identity, posture, TrustSec
                                |     MCP: NetBox          --> DCIM/IPAM source of truth (read-write)
                                |     MCP: Nautobot        --> IPAM source of truth (5 tools, alternative to NetBox)
                                |     MCP: Infrahub        --> Schema-driven SoT, GraphQL, branches (10 tools)
                                |     MCP: ServiceNow      --> Incidents, Changes, CMDB
                                |
                                |-- MICROSOFT 365:
                                |     MCP: Microsoft Graph  --> OneDrive, SharePoint, Visio, Teams
                                |
                                |-- SECURITY & COMPLIANCE:
                                |     MCP: NVD CVE         --> NIST vulnerability database
                                |
                                |-- VERSION CONTROL:
                                |     MCP: GitHub           --> Issues, PRs, code search, Actions (Docker)
                                |
                                |-- PACKET ANALYSIS:
                                |     MCP: Packet Buddy     --> pcap/pcapng deep analysis via tshark
                                |
                                |-- NETWORK ORCHESTRATION:
                                |     MCP: Cisco NSO          --> Device config, sync, services via RESTCONF
                                |     MCP: Itential IAP       --> Config mgmt, compliance, workflows, lifecycle (65+ tools)
                                |
                                |-- FIREWALL SECURITY:
                                |     MCP: Cisco FMC          --> Access policy search, FTD targeting, multi-FMC
                                |
                                |-- CLOUD-MANAGED NETWORKING:
                                |     MCP: Cisco Meraki       --> Dashboard API (~804 endpoints): wireless, switching, security, cameras
                                |
                                |-- NETWORK INTELLIGENCE:
                                |     MCP: ThousandEyes (community) --> Tests, agents, path vis, dashboards (9 tools, stdio)
                                |     MCP: ThousandEyes (official)  --> Alerts, outages, BGP, instant tests, endpoints (~20 tools, remote HTTP)
                                |
                                |-- REMOTE DEVICE ACCESS:
                                |     MCP: Cisco RADKit  --> Cloud-relayed CLI, SNMP, device inventory (5 tools, stdio)
                                |
                                |-- SD-WAN:
                                |     MCP: Cisco SD-WAN      --> vManage API (12 read-only tools: devices, templates, policies, alarms)
                                |
                                |-- OBSERVABILITY:
                                |     MCP: Grafana            --> Dashboards, Prometheus, Loki, alerting, incidents, OnCall (75+ tools via uvx)
                                |     MCP: Prometheus         --> Direct PromQL queries, metric discovery, target health (6 tools via pip)
                                |     MCP: Kubeshark          --> K8s L4/L7 traffic capture, TLS decryption, pcap export, flow analysis (6 tools, remote HTTP)
                                |
                                |-- PROTOCOL PARTICIPATION:
                                |     MCP: Protocol MCP      --> BGP/OSPF/GRE speakers (10 tools, scapy)
                                |
                                |-- LAB & SIMULATION:
                                |     MCP: Cisco CML         --> Lab lifecycle, topology, nodes, captures
                                |     MCP: ContainerLab      --> Containerized labs (SR Linux, cEOS, FRR) via API
                                |
                                |-- AWS CLOUD:
                                |     MCP: AWS Network        --> VPC, TGW, Cloud WAN, VPN, Firewall (27 tools)
                                |     MCP: AWS CloudWatch     --> Metrics, alarms, logs, flow log analysis
                                |     MCP: AWS IAM            --> Users, roles, policies (read-only)
                                |     MCP: AWS CloudTrail     --> API event audit trail
                                |     MCP: AWS Cost Explorer  --> Spending analysis, forecasts
                                |     MCP: AWS Diagram        --> Architecture visualization (graphviz)
                                |
                                |-- GCP CLOUD (remote HTTP):
                                |     MCP: Compute Engine     --> VMs, disks, templates (28 tools)
                                |     MCP: Cloud Monitoring   --> Metrics, alerts, time series (6 tools)
                                |     MCP: Cloud Logging      --> Log search, VPC flow logs, audit (6 tools)
                                |     MCP: Resource Manager   --> Project discovery (1 tool)
                                |
                                |-- UTILITIES:
                                |     MCP: Subnet Calc     --> IPv4 + IPv6 CIDR calculator
                                |     MCP: GAIT            --> Git-based AI audit trail
                                |     MCP: Wikipedia       --> Technology context
                                |     MCP: Markmap         --> Mind map visualizations
                                |     MCP: Draw.io         --> Network topology diagrams
                                |     MCP: UML MCP         --> 27+ diagram types via Kroki
                                '     MCP: RFC Lookup      --> IETF standards reference
```

---

## OpenClaw Workspace Files

NetClaw ships with the full set of OpenClaw workspace markdown files. These are injected into the agent's system prompt at session start to define its identity, behavior, and operating procedures.

| File | Purpose | Loaded When |
|------|---------|-------------|
| **[SOUL.md](SOUL.md)** | Core personality, CCIE expertise, 12 non-negotiable rules, protocol knowledge base | Every session |
| **[AGENTS.md](AGENTS.md)** | Operating instructions: memory system, safety rules, change management workflow, Slack behavior, escalation matrix | Every session |
| **[IDENTITY.md](IDENTITY.md)** | Name, creature type, vibe, emoji — NetClaw's identity card | Every session |
| **[USER.md](USER.md)** | Your preferences, timezone, role, network details — personalization layer (edit this) | Every session |
| **[TOOLS.md](TOOLS.md)** | Local infrastructure notes: device IPs, SSH hosts, Slack channels, site info (edit this) | Every session |
| **[HEARTBEAT.md](HEARTBEAT.md)** | Periodic health checks: device reachability, OSPF/BGP state, CPU/memory, syslog scan | Every heartbeat cycle |

**How they work:** OpenClaw reads these files at session start and injects them under "Project Context" in the system prompt. Each file is capped at 20,000 characters. Sub-agents only receive AGENTS.md and TOOLS.md.

**What to customize:** Edit `USER.md` with your name, timezone, and preferences. Edit `TOOLS.md` with your device IPs, Slack channels, and site information. The rest define NetClaw's behavior and expertise — modify only if you want to change how the agent operates.

---

## MCP Servers (37)

| # | MCP Server | Repository | Transport | Function |
|---|------------|------------|-----------|----------|
| 1 | pyATS | [automateyournetwork/pyATS_MCP](https://github.com/automateyournetwork/pyATS_MCP) | stdio (Python) | Device CLI, Genie parsers, config push, dynamic test execution |
| 2 | F5 BIG-IP | [czirakim/F5.MCP.server](https://github.com/czirakim/F5.MCP.server) | stdio (Python) | iControl REST API — virtuals, pools, iRules, profiles, stats |
| 3 | Catalyst Center | [richbibby/catalyst-center-mcp](https://github.com/richbibby/catalyst-center-mcp) | stdio (Python) | DNA-C API — devices, clients, sites, interfaces |
| 4 | Cisco ACI | [automateyournetwork/ACI_MCP](https://github.com/automateyournetwork/ACI_MCP) | stdio (Python) | APIC interaction, policy management, fabric health |
| 5 | Cisco ISE | [automateyournetwork/ISE_MCP](https://github.com/automateyournetwork/ISE_MCP) | stdio (Python) | Identity policy, posture, TrustSec, endpoint control |
| 6 | NetBox | [netboxlabs/netbox-mcp-server](https://github.com/netboxlabs/netbox-mcp-server) | stdio (Python) | Read-write DCIM/IPAM source of truth |
| 7 | Nautobot | [aiopnet/mcp-nautobot](https://github.com/aiopnet/mcp-nautobot) | stdio (Python) | IPAM source of truth — IP addresses, prefixes, VRF/tenant/site filtering (5 tools, alternative to NetBox) |
| 8 | OpsMill Infrahub | [opsmill/infrahub-mcp](https://github.com/opsmill/infrahub-mcp) | stdio (Python) | Schema-driven SoT: nodes, GraphQL queries, versioned branches (10 tools) | `INFRAHUB_ADDRESS`, `INFRAHUB_API_TOKEN` |
| 9 | Itential IAP | [itential/itential-mcp](https://github.com/itential/itential-mcp) | stdio (Python) | Network automation orchestration: config mgmt, compliance, workflows, golden config, lifecycle (65+ tools) | `ITENTIAL_MCP_PLATFORM_HOST`, `ITENTIAL_MCP_PLATFORM_USER`, `ITENTIAL_MCP_PLATFORM_PASSWORD` |
| 10 | ServiceNow | [echelon-ai-labs/servicenow-mcp](https://github.com/echelon-ai-labs/servicenow-mcp) | stdio (Python) | Incidents, change requests, CMDB |
| 11 | Microsoft Graph | [@anthropic-ai/microsoft-graph-mcp](https://www.npmjs.com/package/@anthropic-ai/microsoft-graph-mcp) | npx | OneDrive, SharePoint, Visio, Teams, Exchange via Graph API |
| 12 | GitHub | [github/github-mcp-server](https://github.com/github/github-mcp-server) | Docker (Go) | Issues, PRs, code search, Actions, config-as-code workflows |
| 13 | Packet Buddy | Built-in | stdio (Python) | pcap/pcapng deep analysis via tshark — upload pcaps to Slack |
| 14 | Cisco CML | [xorrkaz/cml-mcp](https://github.com/xorrkaz/cml-mcp) | stdio (Python) | Lab lifecycle, topology, nodes, links, captures, CLI exec, admin |
| 15 | Cisco NSO | [NSO-developer/cisco-nso-mcp-server](https://github.com/NSO-developer/cisco-nso-mcp-server) | stdio (Python) | Device config, state, sync, services, NED IDs via RESTCONF |
| 16 | Cisco FMC | [CiscoDevNet/CiscoFMC-MCP-server-community](https://github.com/CiscoDevNet/CiscoFMC-MCP-server-community) | HTTP (Python) | Secure Firewall access policy search, FTD targeting, multi-FMC (4 tools) |
| 17 | Cisco Meraki | [CiscoDevNet/meraki-magic-mcp-community](https://github.com/CiscoDevNet/meraki-magic-mcp-community) | stdio (Python) | Meraki Dashboard API — ~804 endpoints: orgs, networks, wireless, switching, security, cameras, diagnostics |
| 18 | ThousandEyes (community) | [CiscoDevNet/thousandeyes-mcp-community](https://github.com/CiscoDevNet/thousandeyes-mcp-community) | stdio (Python) | Tests, agents, path visualization, dashboards, users, account groups (9 read-only tools) |
| 19 | ThousandEyes (official) | [CiscoDevNet/ThousandEyes-MCP-Server-official](https://github.com/CiscoDevNet/ThousandEyes-MCP-Server-official) | Remote HTTP | Alerts, outages, BGP routes, instant tests, endpoint agents, anomalies, AI views (~20 tools) |
| 20 | Cisco RADKit | [CiscoDevNet/radkit-mcp-server-community](https://github.com/CiscoDevNet/radkit-mcp-server-community) | stdio (Python) | Cloud-relayed remote device access — CLI exec, SNMP GET, device inventory, attribute inspection (5 tools) |
| 21 | AWS Network | [awslabs/aws-network-mcp-server](https://github.com/awslabs/mcp) | uvx (Python) | VPC, TGW, Cloud WAN, VPN, Network Firewall, flow logs (27 tools) |
| 22 | AWS CloudWatch | [awslabs/cloudwatch-mcp-server](https://github.com/awslabs/mcp) | uvx (Python) | CloudWatch metrics, alarms, Logs Insights queries |
| 23 | AWS IAM | [awslabs/iam-mcp-server](https://github.com/awslabs/mcp) | uvx (Python) | IAM users, roles, policies (read-only mode) |
| 24 | AWS CloudTrail | [awslabs/cloudtrail-mcp-server](https://github.com/awslabs/mcp) | uvx (Python) | API event audit trail, security investigation |
| 25 | AWS Cost Explorer | [awslabs/cost-explorer-mcp-server](https://github.com/awslabs/mcp) | uvx (Python) | Spending analysis, forecasts, anomaly detection |
| 26 | AWS Diagram | [awslabs/aws-diagram-mcp-server](https://github.com/awslabs/mcp) | uvx (Python) | Architecture diagrams from live infrastructure (graphviz) |
| 27 | GCP Compute Engine | [Google Cloud](https://docs.cloud.google.com/compute/docs/reference/mcp) | Remote HTTP | VMs, disks, templates, instance groups, snapshots (28 tools) |
| 28 | GCP Cloud Monitoring | [Google Cloud](https://docs.cloud.google.com/monitoring/api/ref_v3/mcp) | Remote HTTP | Time series metrics, alert policies, active alerts (6 tools) |
| 29 | GCP Cloud Logging | [Google Cloud](https://docs.cloud.google.com/logging/docs/reference/v2/mcp) | Remote HTTP | Log search, VPC flow logs, firewall logs, audit logs (6 tools) |
| 30 | GCP Resource Manager | [Google Cloud](https://docs.cloud.google.com/mcp/supported-products) | Remote HTTP | Project discovery (1 tool) |
| 31 | NVD CVE | [marcoeg/mcp-nvd](https://github.com/marcoeg/mcp-nvd) | stdio (Python) | NIST NVD vulnerability database with CVSS scoring |
| 32 | Subnet Calculator | [automateyournetwork/GeminiCLI_SubnetCalculator_Extension](https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension) | stdio (Python) | IPv4 + IPv6 CIDR subnet calculator |
| 33 | GAIT | [automateyournetwork/gait_mcp](https://github.com/automateyournetwork/gait_mcp) | stdio (Python) | Git-based AI tracking and audit |
| 34 | Wikipedia | [automateyournetwork/Wikipedia_MCP](https://github.com/automateyournetwork/Wikipedia_MCP) | stdio (Python) | Standards and technology context |
| 35 | Markmap | [automateyournetwork/markmap_mcp](https://github.com/automateyournetwork/markmap_mcp) | stdio (Node) | Hierarchical mind map generation |
| 36 | Draw.io | [@drawio/mcp](https://github.com/jgraph/drawio-mcp) | npx | Network topology diagram generation |
| 37 | RFC Lookup | [@mjpitz/mcp-rfc](https://github.com/mjpitz/mcp-rfc) | npx | IETF RFC search and retrieval |
| 38 | Juniper JunOS | [Juniper/junos-mcp-server](https://github.com/Juniper/junos-mcp-server) | stdio (Python) | PyEZ/NETCONF — CLI execution, config management, Jinja2 templates, device facts, batch operations (10 tools) |
| 39 | Arista CVP | [noredistribution/mcp-cvp-fun](https://github.com/noredistribution/mcp-cvp-fun) | stdio (Python/uv) | CloudVision Portal REST API — device inventory, events, connectivity monitor, tag management (4 tools) |
| 40 | UML MCP | [antoinebou12/uml-mcp](https://github.com/antoinebou12/uml-mcp) | stdio (Python) | 27+ UML/diagram types via Kroki — class, sequence, nwdiag, rackdiag, packetdiag, C4, Mermaid, D2, Graphviz, ERD, BPMN (2 tools) |
| 41 | Protocol MCP | [automateyournetwork/WontYouBeMyNeighbour](https://github.com/automateyournetwork/WontYouBeMyNeighbour) | stdio (Python) | Live BGP/OSPF/GRE control-plane participation — peer with routers, inject/withdraw routes, query RIB/LSDB, adjust metrics (10 tools) |
| 42 | ContainerLab | [seanerama/clab-mcp-server](https://github.com/seanerama/clab-mcp-server) | stdio (Python) | Containerized network lab lifecycle — deploy, inspect, exec, destroy labs (SR Linux, cEOS, FRR, IOS-XR, NX-OS) via ContainerLab API (6 tools) |
| 43 | Cisco SD-WAN | [siddhartha2303/cisco-sdwan-mcp](https://github.com/siddhartha2303/cisco-sdwan-mcp) | stdio (Python) | vManage read-only monitoring — fabric devices, WAN Edge inventory, templates, policies, alarms, BFD, OMP routes, control connections (12 tools) |
| 44 | Grafana | [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) | uvx (Go) | Observability platform — dashboards, Prometheus PromQL, Loki LogQL, alerting, incidents, OnCall, annotations, panel rendering (75+ tools) |
| 45 | Prometheus | [pab1it0/prometheus-mcp-server](https://github.com/pab1it0/prometheus-mcp-server) | stdio (Python) | Direct PromQL monitoring — instant/range queries, metric discovery with pagination, metric metadata, scrape target health, system health check (6 tools) |
| 46 | Kubeshark | [kubeshark/kubeshark](https://github.com/kubeshark/kubeshark) | remote HTTP (Go) | Kubernetes L4/L7 traffic analysis — capture, pcap export, snapshots, KFL filtering, TCP/UDP flow stats, TLS decryption via eBPF (6 tools) |

All MCP servers communicate via stdio (JSON-RPC 2.0) through `scripts/mcp-call.py`. GitHub MCP runs via Docker. CML MCP is pip-installed (`cml-mcp`). NSO MCP is pip-installed (`cisco-nso-mcp-server`). FMC MCP runs as an HTTP server on port 8000. Meraki Magic MCP runs via FastMCP stdio (~804 Dashboard API endpoints). ThousandEyes community MCP runs via stdio (9 read-only tools); ThousandEyes official MCP is a remote HTTP endpoint hosted by Cisco at `https://api.thousandeyes.com/mcp` (~20 tools via `npx mcp-remote`). RADKit MCP runs via FastMCP stdio with certificate-based cloud relay auth (5 tools for remote device access). Nautobot MCP runs via MCP SDK stdio (5 IPAM tools, alternative to NetBox). Infrahub MCP runs via stdio (10 tools for schema-driven SoT, GraphQL queries, and versioned branches). Itential MCP is pip-installed (`itential-mcp`) and runs via stdio (65+ tools for network automation orchestration). JunOS MCP runs via stdio (10 tools for PyEZ/NETCONF device automation). Arista CVP MCP runs via uv/stdio (4 tools for CloudVision Portal device inventory, events, connectivity monitoring, and tag management). UML MCP runs via stdio (2 tools for 27+ diagram types via Kroki multi-engine rendering). Protocol MCP runs via stdio (10 tools for live BGP/OSPF/GRE control-plane participation using scapy-based protocol speakers). ContainerLab MCP runs via stdio (6 tools for containerized network lab lifecycle management via ContainerLab API). SD-WAN MCP runs via stdio (12 read-only tools for Cisco SD-WAN vManage fabric monitoring). Grafana MCP runs via `uvx mcp-grafana` (75+ tools for dashboards, Prometheus, Loki, alerting, incidents, OnCall). Prometheus MCP is pip-installed (`prometheus-mcp-server`) and runs via stdio (6 tools for direct PromQL queries, metric discovery, and scrape target health). Kubeshark MCP is a remote HTTP endpoint running inside a Kubernetes cluster (6 tools for L4/L7 traffic capture, pcap export, flow analysis, and TLS decryption via eBPF; access via `kubectl port-forward svc/kubeshark-hub 8898:8898`). AWS MCPs run via `uvx` (uv tool runner). GCP MCPs are remote HTTP endpoints hosted by Google (OAuth 2.0 auth). No persistent connections, no port management.

---

## Skills (82)

### pyATS Device Skills (9)

| Skill | What the Agent Knows |
|-------|---------------------|
| **pyats-network** | All 8 pyATS MCP tools: `show commands` with Genie structured parsing (100+ IOS-XE parsers), `ping` from device, `configure`, `running-config`, `logging`, `device list`, `Linux commands`, `dynamic AEtest scripts`. Direct Python pyATS with Genie Learn (34 features) and Genie Diff for state comparison. |
| **pyats-health-check** | 8-step health procedure with threshold tables and severity ratings. Cross-references NetBox for expected vs actual interface state. Fleet-wide parallel execution via pCall. GAIT audit trail. |
| **pyats-routing** | Full routing table analysis with route source codes and ECMP. OSPF: neighbor states, LSA types 1-7, LSDB analysis, SPF runs. BGP: 11-step best path selection, NOTIFICATION error codes, policy verification. EIGRP: DUAL states, SIA detection. Redistribution audit. |
| **pyats-security** | 9-step CIS-style audit: management plane, AAA, ACLs, CoPP, routing auth, infrastructure security, encryption, SNMP. Integrates ISE NAD verification and NVD CVE vulnerability scanning (CVSS >= 7.0). Fleet-wide pCall. GAIT audit trail. |
| **pyats-topology** | 7-step discovery via CDP/LLDP/ARP/routing peers/interface mapping/VRF/FHRP. Reconciles against NetBox cables (DOCUMENTED/UNDOCUMENTED/MISSING/MISMATCH). Color-coded Draw.io diagrams. Fleet-wide pCall. GAIT audit trail. |
| **pyats-config-mgmt** | 5-phase change workflow: Baseline, Plan, Apply, Verify, Document. ServiceNow CR gating (create, approve, close/escalate). GAIT audit at every phase. Compliance templates for security baseline and VTY hardening. |
| **pyats-troubleshoot** | Structured OSI-layer methodology for 4 symptom types: connectivity loss, adjacency down, slow performance, interface flapping. Multi-hop parallel state collection via pCall. NetBox cross-reference for expected state. GAIT audit trail. |
| **pyats-dynamic-test** | Generates and executes deterministic pyATS aetest scripts with embedded TEST_DATA. Sandboxed execution: no filesystem, network, or subprocess access. 300-second timeout. |
| **pyats-parallel-ops** | Fleet-wide parallel operations. pCall grouping by role/site. Failure isolation (one device timeout doesn't block others). Result aggregation with severity sorting. Scaling guidelines from 1 to 50+ devices. |

### pyATS Linux Host Skills (3)

| Skill | Source | Description |
|-------|--------|-------------|
| **pyats-linux-system** | [pyATS MCP](https://github.com/automateyournetwork/pyATS_MCP) | Linux host system ops — process monitoring (ps -ef), Docker container stats (docker stats --no-stream), filesystem inspection (ls -l), tool verification (curl -V) |
| **pyats-linux-network** | [pyATS MCP](https://github.com/automateyournetwork/pyATS_MCP) | Linux host network ops — interfaces (ifconfig), routing tables (ip route show table all), network connections (netstat -rn, route) |
| **pyats-linux-vmware** | [pyATS MCP](https://github.com/automateyournetwork/pyATS_MCP) | VMware ESXi host ops — VM inventory (vim-cmd vmsvc/getallvms), snapshot inspection (vim-cmd vmsvc/snapshot.get) |

### pyATS JunOS Skills (3)

| Skill | MCP Server | Description |
|-------|------------|-------------|
| **pyats-junos-system** | [pyATS MCP](https://github.com/automateyournetwork/pyats_mcp) (stdio) | JunOS chassis health, hardware inventory, version, NTP, SNMP, files/logs, firewall counters, DDoS, services accounting |
| **pyats-junos-interfaces** | [pyATS MCP](https://github.com/automateyournetwork/pyats_mcp) (stdio) | JunOS interfaces (terse/extensive/optics), LACP, CoS, LLDP, ARP, IPv6 NDP, BFD sessions, traffic monitoring |
| **pyats-junos-routing** | [pyATS MCP](https://github.com/automateyournetwork/pyats_mcp) (stdio) | JunOS OSPF/v3, BGP, route table (by protocol/table/instance), MPLS/LDP/RSVP, TED, PFE, ping, traceroute |

### pyATS ASA Firewall Skills (1)

| Skill | MCP Server | Description |
|-------|------------|-------------|
| **pyats-asa-firewall** | [pyATS MCP](https://github.com/automateyournetwork/pyats_mcp) (stdio) | Cisco ASA firewalls — VPN sessions (AnyConnect, WebVPN, IKEv2), failover, interfaces, routing, ASP drops, service policies, resource usage |

### pyATS F5 BIG-IP Skills (2)

| Skill | MCP Server | Description |
|-------|------------|-------------|
| **pyats-f5-ltm** | [pyATS MCP](https://github.com/automateyournetwork/pyats_mcp) (stdio) | F5 BIG-IP LTM/GTM operations via pyATS iControl REST — virtual servers, pools, nodes, monitors, profiles, iRules, persistence, GTM wide IPs, DNS, data groups |
| **pyats-f5-platform** | [pyATS MCP](https://github.com/automateyournetwork/pyats_mcp) (stdio) | F5 BIG-IP platform operations via pyATS iControl REST — system, networking, HA/CM, auth, analytics, security, APM, live-update, ADC certs, file management |

### Domain Skills (9)

| Skill | What It Does |
|-------|-------------|
| **netbox-reconcile** | Diffs NetBox intent vs device reality. Detects 7 discrepancy types: IP_DRIFT, MISSING_INTERFACE, UNDOCUMENTED_LINK, CABLE_MISMATCH, VLAN_MISMATCH, STATUS_MISMATCH, MTU_MISMATCH. Opens ServiceNow incidents for CRITICAL findings. Generates Markmap drift summary. GAIT audit. |
| **nautobot-sot** | Nautobot IPAM source of truth (5 tools, alternative to NetBox): query IP addresses with filtering by status (active/reserved/deprecated), role (loopback/secondary/anycast), VRF, tenant; look up network prefixes by site and role; full-text search across all IP data; retrieve IP details by Nautobot UUID; verify API connectivity. Supports pagination (up to 1000 results). Integrates with pyATS topology for intended-vs-actual reconciliation. |
| **infrahub-sot** | OpsMill Infrahub schema-driven source of truth (10 tools): get_schema_mapping for all available kinds, get_nodes/get_node_details for infrastructure objects (InfraDevice, InfraInterface, InfraIPAddress, InfraPrefix), get_related_nodes for relationship traversal, query_graphql for custom queries and mutations, get_branches/branch_create/branch_delete for versioned change management, branch_diff for change review. Supports GraphQL-based schema introspection and branch-based workflows for safe infrastructure changes. |
| **aci-fabric-audit** | ACI fabric health: node status, firmware, policy tree walk (Tenant/VRF/BD/EPG), contract analysis, fault analysis with health scores, endpoint learning verification. Severity-rated consolidated report. GAIT audit. |
| **aci-change-deploy** | Safe ACI policy changes: ServiceNow CR gating, pre-change fault baseline, dependency-ordered deployment (Tenant > VRF > BD > AP > EPG), post-change fault delta, automatic rollback on fault increase. GAIT audit. |
| **ise-posture-audit** | ISE audit: authorization policy review (default-allow detection), posture compliance assessment, profiling coverage analysis, TrustSec SGT matrix analysis (permit-all detection), active session health. |
| **ise-incident-response** | Endpoint investigation: lookup by MAC/IP/username, auth history, posture/profile review, risk assessment. **Human decision point required** before any quarantine action. ServiceNow Security Incident creation. GAIT audit. |
| **servicenow-change-workflow** | Full ITSM lifecycle: pre-change incident check, CR creation, approval gate, execution coordination, post-change verification, rollback procedure, CR closure/escalation. Supports Normal, Standard, and Emergency change types. |
| **gait-session-tracking** | Mandatory Git-based audit trail. Session branch creation, turn recording (prompt/response/artifacts), session log display. 9 GAIT tools: status, init, branch, checkout, record_turn, log, show, pin, summarize_and_squash. |

### F5 BIG-IP Skills (3)

| Skill | What It Does |
|-------|-------------|
| **f5-health-check** | Monitor F5 virtual server stats, pool member health, log analysis. Systematic health assessment with severity ratings. GAIT audit. |
| **f5-config-mgmt** | Safe F5 object lifecycle: create/update/delete pools, virtuals, iRules with baseline/plan/apply/verify workflow. ServiceNow CR gating. GAIT audit. |
| **f5-troubleshoot** | F5 troubleshooting: virtual server not responding, pool members down, persistence issues, iRule errors, SSL problems, performance degradation. |

### Catalyst Center Skills (3)

| Skill | What It Does |
|-------|-------------|
| **catc-inventory** | Device inventory via Catalyst Center: filter by hostname/IP/platform/role/reachability, site hierarchy, interface details. Cross-reference with pyATS. |
| **catc-client-ops** | Client monitoring: wired/wireless clients, filter by SSID/band/site/OS, client details by MAC, count analytics, time-based trending. |
| **catc-troubleshoot** | CatC troubleshooting: device unreachable, client connectivity, interface down, site-wide outage triage. Integration with pyATS for CLI-level follow-up. |

### Microsoft 365 Skills (3)

| Skill | What It Does |
|-------|-------------|
| **msgraph-files** | OneDrive/SharePoint file operations: upload, download, search, organize network documentation, config backups, audit reports, and diagram artifacts |
| **msgraph-visio** | Visio diagram generation from CDP/LLDP discovery data. Upload .vsdx files to SharePoint, create sharing links. Physical, logical, reconciliation, and ACI fabric diagram types. |
| **msgraph-teams** | Teams channel notifications: health alerts, security alerts, change completion, incident updates, report delivery, diagram sharing. Severity-coded HTML messages with threading. |

### GitHub Skills (1)

| Skill | What It Does |
|-------|-------------|
| **github-ops** | Config-as-code workflows: create issues from network findings, commit config backups to repos, open PRs for changes with ServiceNow CR references, search code for configuration patterns, trigger Actions workflows. |

### Packet Analysis Skills (1)

| Skill | What It Does |
|-------|-------------|
| **packet-analysis** | Deep pcap analysis via tshark. Upload a `.pcap` or `.pcapng` file to Slack and NetClaw analyzes it: protocol hierarchy, IP/TCP/UDP conversations, top endpoints, DNS queries, HTTP requests, expert info (retransmissions, errors), filtered packet inspection, and full JSON decode. 12 MCP tools for comprehensive L2-L7 packet investigation. |

### Cisco CML Skills (5)

| Skill | What It Does |
|-------|-------------|
| **cml-lab-lifecycle** | Full lab lifecycle: create, start, stop, wipe, delete, clone, import/export CML labs. Build labs from natural language descriptions ("build me a 3-router OSPF lab"). Export topologies as YAML for sharing or GitHub commits. |
| **cml-topology-builder** | Build topologies: add nodes (IOSv, NX-OS, IOS-XR, ASAv, servers), create interfaces, wire links, set link conditioning (bandwidth, latency, jitter, loss for WAN simulation), control link states (up/down for failure simulation), add visual annotations (text, rectangles, ellipses, lines). Grid-based layout. |
| **cml-node-operations** | Node operations: start/stop individual nodes, set startup configs (IOS, NX-OS, IOS-XR templates), execute CLI commands via pyATS, retrieve console logs for troubleshooting, download running configs, wipe and reconfigure nodes. |
| **cml-packet-capture** | Capture packets on CML lab links: start/stop captures with BPF filters, download pcap files, and hand off to Packet Buddy for deep tshark analysis. Protocol-specific capture workflows for BGP, OSPF, STP, ICMP troubleshooting. |
| **cml-admin** | CML server administration: user/group management, system info (CPU, RAM, disk), licensing status, resource usage monitoring, capacity planning for new labs. |

### ContainerLab Skills (1)

| Skill | What It Does |
|-------|-------------|
| **clab-lab-management** | Containerized network lab lifecycle via ContainerLab API (6 tools): authenticate with clab-api-server, list running labs, deploy multi-vendor topologies (SR Linux, cEOS, IOS XR, NX-OS, FTDv, FRR, cRPD, generic Linux), inspect lab details with management IPs, execute commands on individual or all nodes, and graceful lab destruction with cleanup. Supports spine-leaf fabrics, multi-vendor interop labs, and protocol testing topologies. Requires ContainerLab API server running (Docker or native). GAIT audit trail. |

### Cisco NSO Skills (2)

| Skill | What It Does |
|-------|-------------|
| **nso-device-ops** | NSO device operations: retrieve full config from NSO's CDB, inspect operational state, check device sync status, sync-from-device to pull live config into NSO, get platform info (model, serial, OS), list NED IDs and device groups. RESTCONF API. |
| **nso-service-mgmt** | NSO service management: discover available service types (L3VPN, ACL, QoS, etc.), list deployed service instances, service health checks via sync verification, pre-change impact analysis (which services touch a device), service inventory reporting. |

### Itential IAP Skills (1)

| Skill | What It Does |
|-------|-------------|
| **itential-automation** | Itential Automation Platform network orchestration (65+ tools): platform health monitoring (get_health for adapters, applications, system status), device management (get_devices, get_device_configuration, backup_device_configuration, apply_device_configuration), compliance operations (get_compliance_plans, run_compliance_plan, describe_compliance_report), golden config management (get_golden_config_trees, render_template), workflow orchestration (get_workflows, start_workflow, describe_job, get_job_metrics_for_workflow), and lifecycle automation. Integrates with ServiceNow for change management gating. GAIT audit trail. |

### Cisco FMC Skills (1)

| Skill | What It Does |
|-------|-------------|
| **fmc-firewall-ops** | Cisco Secure Firewall policy search via FMC REST API (4 tools): list FMC profiles for multi-FMC environments, search access rules by IP/FQDN within a policy, resolve FTD devices to their assigned policies and search, FMC-wide rule search with network indicators (IP, FQDN), identity indicators (SGT, realm users/groups), and policy name filters. Read-only firewall rule audit, connectivity verification ("can Host A reach Host B?"), SGT policy review, and cross-FMC consistency analysis. |

### Cisco RADKit Skills (1)

| Skill | What It Does |
|-------|-------------|
| **radkit-remote-access** | Cloud-relayed remote device access via Cisco RADKit (5 tools): discover device inventory from RADKit service, inspect device attributes (type, platform, SNMP/NETCONF capabilities), execute CLI commands with timeout and line-limit controls through the cloud relay, perform SNMP GET operations for lightweight metric polling (uptime, interface counters, CPU), and structured command execution with status tracking. Bridges cloud-hosted agents to air-gapped or on-premises devices without direct SSH/SNMP connectivity — ideal for multi-site operations, secure environments requiring certificate-based auth, and hybrid cloud-to-on-prem workflows. |

### Juniper JunOS Skills (1)

| Skill | What It Does |
|-------|-------------|
| **junos-network** | Juniper device automation via PyEZ/NETCONF — CLI execution, config management, Jinja2 templates, device facts, batch operations (10 tools) |

### Arista CloudVision Skills (1)

| Skill | What It Does |
|-------|-------------|
| **arista-cvp** | CloudVision Portal — device inventory, events, connectivity monitoring, device tags (4 tools) |

### Protocol Participation Skills (1)

| Skill | What It Does |
|-------|-------------|
| **protocol-participation** | Live BGP/OSPF/GRE control-plane participation (10 tools): BGP peer status, Loc-RIB query, route injection/withdrawal, LOCAL_PREF adjustment, OSPF neighbor listing, LSDB query, interface cost adjustment, GRE tunnel status, consolidated protocol summary. Peers with real routers over GRE tunnels using native BGP-4 (RFC 4271) and OSPFv3 (RFC 5340) speakers. Route mutations gated by ServiceNow CR (unless `NETCLAW_LAB_MODE=true`). Docker-based FRR lab testbed included for testing. GAIT audit trail. |

### ContainerLab Skills (1)

| Skill | What It Does |
|-------|-------------|
| **clab-lab-management** | ContainerLab network lab lifecycle management via ContainerLab API (6 tools): authenticate, list existing labs, deploy new topologies (SR Linux, cEOS, FRR, Cisco IOS-XR/XE/NX-OS/FTDv, Juniper cRPD, generic Linux), inspect running labs (node status, management IPs), execute commands on lab nodes, and gracefully destroy labs with cleanup. Auto-authentication on every tool call. Requires ContainerLab API server running with PAM-authenticated Linux user. GAIT audit trail. |

### Cisco SD-WAN Skills (1)

| Skill | What It Does |
|-------|-------------|
| **sdwan-ops** | Cisco SD-WAN vManage read-only operations (12 tools): fabric device inventory (vManage, vSmart, vBond, vEdge), WAN Edge details (serial, chassis ID), device and feature templates, centralized policy definitions, active alarms, audit events, interface statistics per device, BFD session status, OMP routes (received/advertised), DTLS/TLS control connections, running configuration retrieval. All operations are read-only — no configuration changes possible. Cross-reference with pyATS for CLI-level device verification. GAIT audit trail. |

### Grafana Observability Skills (1)

| Skill | What It Does |
|-------|-------------|
| **grafana-observability** | Grafana observability platform (75+ tools): dashboard search/summary/property extraction/modification, Prometheus PromQL queries (instant/range, metric discovery, histogram percentiles), Loki LogQL queries (log search, label discovery, patterns, stats), alerting rules (list/create/update/delete, contact points), incident management (list/create/update, activity timeline), OnCall schedules (rotations, current on-call, alert groups), annotations, panel image rendering, deep link generation, and Sift investigation (error patterns, slow requests). Runs via `uvx mcp-grafana` (Go). Supports both self-hosted Grafana and Grafana Cloud. Read-only mode available (`--disable-write`). Dashboard and alert modifications gated by ServiceNow CR. GAIT audit trail. |

### Prometheus Monitoring Skills (1)

| Skill | What It Does |
|-------|-------------|
| **prometheus-monitoring** | Direct Prometheus access (6 tools): execute instant PromQL queries (`execute_query`), execute range queries with time intervals (`execute_range_query`), browse available metrics with pagination (`list_metrics`), retrieve metric type/help/unit metadata (`get_metric_metadata`), view scrape target details and health (`get_targets`), check Prometheus server availability (`health_check`). Supports basic auth, bearer token (Grafana Cloud, Thanos, Cortex), multi-tenant org ID, SSL control, and custom headers. Installed via `pip3 install prometheus-mcp-server`. Complementary to grafana-observability for direct PromQL access without dashboard overhead. GAIT audit trail. |

### Kubeshark Traffic Analysis Skills (1)

| Skill | What It Does |
|-------|-------------|
| **kubeshark-traffic** | Kubeshark Kubernetes L4/L7 traffic analysis (6 tools): capture traffic across cluster pods (`capture_traffic`), export pcaps for Wireshark/tshark analysis (`export_pcap`), create point-in-time traffic snapshots (`create_snapshot`), apply Kubeshark Filter Language expressions (`apply_filter`), list TCP/UDP flows with RTT metrics and byte counts (`list_l4_flows`), get top-talker summaries with protocol distribution (`get_l4_flow_summary`). Automatic TLS/HTTPS decryption via eBPF. Dissects HTTP, gRPC, GraphQL, Redis, Kafka, DNS with full request/response payloads. Remote HTTP MCP server running inside K8s cluster (port 8898). Integrates with packet-analysis for deeper pcap inspection. GAIT audit trail. |

### Cisco Meraki Skills (5)

| Skill | What It Does |
|-------|-------------|
| **meraki-network-ops** | Meraki Dashboard organization and network management via ~804 API endpoints: list organizations, org inventory, license status, network CRUD, device lifecycle (claim, unclaim, reboot), client discovery with usage/policy, uplink status, config change audit, action batches for bulk operations, and generic `call_meraki_api` for any Dashboard endpoint. Built-in caching (50-90% API reduction), auto-retry, rate limit handling. |
| **meraki-wireless-ops** | Meraki wireless management: list/update SSIDs (auth, VLAN, band, splash), RF profile creation with band selection and power settings, channel utilization analysis per AP, signal quality (SNR) monitoring, connection statistics (auth/DHCP success rates), per-client connectivity event investigation (roaming, deauth, failures). Workflows for wireless health, client troubleshooting, and RF optimization. |
| **meraki-switch-ops** | Meraki MS switch operations: port configuration (VLAN, type, PoE, BPDU guard, RSTP), live port statuses (speed, duplex, CRC errors, traffic, PoE draw), VLAN management (list, create), switch ACLs, QoS rules, and port cycling for PoE resets. Workflows for port audit, VLAN provisioning, and port troubleshooting. |
| **meraki-security-appliance** | Meraki MX security appliance: L3 outbound firewall rules (audit and modify), site-to-site Auto VPN (status, hub/spoke config), content filtering (URL categories, blocked/allowed lists), traffic shaping (global and per-rule bandwidth limits), IDS/IPS security event investigation. Workflows for firewall audit, VPN troubleshooting, content filter review, and security incident response. |
| **meraki-monitoring** | Meraki live diagnostics and monitoring: ping from device (latency, loss, jitter), cable test on switch ports (OK/open/short/length), LED blink for physical identification, wake-on-LAN, MV camera analytics (live person/vehicle counts, zones, snapshots, Sense ML detection), config change tracking (who changed what, when), API request history, webhook delivery logs. |

### ThousandEyes Skills (2)

| Skill | What It Does |
|-------|-------------|
| **te-network-monitoring** | ThousandEyes network monitoring via two MCP servers — community (9 tools, local stdio) for core monitoring: list tests, agents, test results, path visualization, dashboards, dashboard widgets, users, account groups; and official (~20 tools, remote HTTP) for advanced analysis: alerts, events, outages, instant tests, anomalies, metrics, AI-powered views explanations, endpoint agents, BGP results, path visualization. Workflows for network performance assessment, path troubleshooting, outage investigation, endpoint experience, and BGP monitoring. |
| **te-path-analysis** | Deep network path analysis and active troubleshooting via ThousandEyes — hop-by-hop path visualization (IP, DNS name, latency, packet loss, MPLS labels, network owner per hop), BGP route analysis (AS path, origin AS, prefix reachability, route stability from 300+ global BGP monitors), outage investigation (scope, timeline, affected services), instant on-demand tests (use judiciously — consumes test units), endpoint VPN diagnostics (WiFi signal, DNS, VPN latency), and anomaly detection. Workflows for "Why is site X slow?", internet outage triage, endpoint VPN troubleshooting, and BGP hijack/leak detection. |

### AWS Cloud Skills (5)

| Skill | What It Does |
|-------|-------------|
| **aws-network-ops** | AWS cloud networking via 27 read-only tools: list VPCs, get VPC details (subnets, route tables, NACLs, gateways), Transit Gateway details/routes/flow logs/peering/inspection, Cloud WAN core networks/routes/attachments/peering/logs/route simulation, VPN connections with tunnel status, Network Firewall rules and flow logs, ENI details, IP address lookup. Connectivity troubleshooting and VPC audit workflows. |
| **aws-cloud-monitoring** | CloudWatch monitoring: query metrics for any AWS service (VPN TunnelState, NAT GW ActiveConnectionCount/PacketsDropCount, TGW BytesIn/Out, ELB HealthyHostCount/TargetResponseTime, EC2 NetworkIn/Out), check alarms in ALARM state, run Logs Insights queries across log groups, analyze VPC and TGW flow logs for traffic patterns and rejected connections. |
| **aws-security-audit** | AWS security posture via IAM MCP (read-only) + CloudTrail MCP: IAM users/access keys/MFA status, roles/trust policies, overly permissive policies (`ec2:*`, `*:*`), CloudTrail API event search by user/service/resource/time, incident investigation timeline, compliance checks (root access, key rotation, unused credentials). |
| **aws-cost-ops** | AWS spending analysis via Cost Explorer MCP: cost breakdown by service/account/region/tag, daily/monthly trends, forecasts, anomaly detection. Network cost focus: NAT GW data processing ($0.045/GB), TGW data processing ($0.02/GB), VPN hourly + data, ELB LCU, cross-AZ/cross-region/internet transfer. Optimization recommendations. |
| **aws-architecture-diagram** | Generate visual AWS architecture diagrams from live infrastructure: auto-discover VPCs, subnets, TGWs, load balancers, render as PNG/SVG/PDF. Network topology, VPC detail, and multi-account hub-spoke diagram workflows. Requires graphviz. |

### GCP Cloud Skills (3)

| Skill | What It Does |
|-------|-------------|
| **gcp-compute-ops** | GCP Compute Engine (28 tools) + Resource Manager (1 tool): list/create/start/stop/delete VMs, inspect disks and templates, manage instance groups, discover machine types and images, check reservations and commitments, discover projects. Includes infrastructure audit, VM troubleshooting, and capacity planning workflows. |
| **gcp-cloud-monitoring** | Cloud Monitoring (6 tools): query time series data (CPU, network, disk, firewall, VPN, load balancer metrics), list alert policies and active violations, discover available metric types. Network monitoring, alert investigation, and resource health check workflows. |
| **gcp-cloud-logging** | Cloud Logging (6 tools): search log entries (VPC flow logs, firewall logs, admin activity audit, data access audit, DNS queries), discover available logs, inspect log buckets and views. VPC flow log analysis, firewall log investigation, audit trail, and troubleshooting workflows. |

### Reference & Utility Skills (7)

| Skill | Tool Backend | Purpose |
|-------|-------------|---------|
| **nvd-cve** | [marcoeg/mcp-nvd](https://github.com/marcoeg/mcp-nvd) (Python) | NVD vulnerability database — search by keyword, get CVE details with CVSS v3.1/v2.0 scores, exposure correlation |
| **subnet-calculator** | [SubnetCalculator MCP](https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension) | IPv4 + IPv6 subnet calculator — VLSM planning, wildcard masks, address classification, RFC 6164 /127 links |
| **wikipedia-research** | [Wikipedia_MCP](https://github.com/automateyournetwork/Wikipedia_MCP) | Protocol history, standards evolution, technology context. 6 tools: search, summary, content, references, categories, exists check. |
| **markmap-viz** | [markmap-mcp](https://github.com/automateyournetwork/markmap_mcp) (Node) | Interactive mind maps from markdown — OSPF area hierarchies, BGP peer trees, drift summaries |
| **drawio-diagram** | [@drawio/mcp](https://github.com/jgraph/drawio-mcp) (npx + [official skill-cli](https://github.com/jgraph/drawio-mcp/tree/main/skill-cli)) | Network topology diagrams — native `.drawio` files with CLI export (PNG/SVG/PDF with embedded XML), plus browser-based Mermaid/XML/CSV via MCP server. Color-coded by reconciliation status. |
| **rfc-lookup** | [@mjpitz/mcp-rfc](https://github.com/mjpitz/mcp-rfc) (npx) | IETF RFC search, retrieval, and section extraction — BGP (4271), OSPF (2328), NTP (5905) |
| **uml-diagram** | [UML MCP](https://github.com/antoinebou12/uml-mcp) (stdio) | 27+ UML/diagram types via Kroki — class, sequence, nwdiag, rackdiag, packetdiag, C4, Mermaid, D2, Graphviz, ERD, BPMN |

### Slack Integration Skills (4)

| Skill | Purpose |
|-------|---------|
| **slack-network-alerts** | Severity-formatted alert delivery (CRITICAL/HIGH/WARNING/INFO), reaction-based acknowledgment, fleet summary posts |
| **slack-report-delivery** | Rich Slack formatting for health checks, security audits, topology maps, reconciliation results, change reports |
| **slack-incident-workflow** | Full incident lifecycle in Slack: declaration, triage, automated investigation, status updates, resolution, post-incident review |
| **slack-user-context** | User-aware interactions: DND-respecting escalation, timezone-aware scheduling, role-based response depth, shift handoff summaries |

---

## Cloud

NetClaw extends into public cloud infrastructure. Each cloud provider gets its own set of MCP servers and skills, all driven from the same Slack/chat interface as on-prem operations.

### AWS

**6 MCP servers, 5 skills** — networking, monitoring, security, cost, and architecture visualization.

#### Credentials

You need an IAM user with programmatic access. Three values:

| Variable | Example | Description |
|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | `AKIAIOSFODNN7EXAMPLE` | IAM access key ID |
| `AWS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG/...` | IAM secret access key |
| `AWS_REGION` | `us-east-1` | Default region for API calls |

Or use a named AWS CLI profile instead: `AWS_PROFILE=my-profile`

Run `./scripts/setup.sh` — the wizard prompts for all three values.

#### IAM Policy (Minimum Permissions)

Create an IAM policy with these permissions and attach it to your NetClaw IAM user:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NetClawNetworkReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "ec2:GetTransitGateway*",
        "ec2:SearchTransitGateway*",
        "networkmanager:Get*",
        "networkmanager:List*",
        "networkmanager:Describe*",
        "network-firewall:Describe*",
        "network-firewall:List*",
        "elasticloadbalancing:Describe*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetClawCloudWatch",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
        "cloudwatch:DescribeAlarms",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetClawIAMReadOnly",
      "Effect": "Allow",
      "Action": [
        "iam:Get*",
        "iam:List*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetClawCloudTrail",
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents",
        "cloudtrail:GetTrailStatus",
        "cloudtrail:DescribeTrails"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetClawCostExplorer",
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues"
      ],
      "Resource": "*"
    },
    {
      "Sid": "NetClawDiagram",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "elasticloadbalancing:Describe*",
        "rds:Describe*",
        "lambda:List*",
        "ecs:Describe*",
        "ecs:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

#### What You Can Do

| Skill | Capabilities |
|-------|-------------|
| `aws-network-ops` | List VPCs, inspect subnets/route tables/NACLs, Transit Gateway routes/attachments/peering, Cloud WAN, VPN tunnel status, Network Firewall rules, flow logs, ENI lookup, IP search |
| `aws-cloud-monitoring` | CloudWatch metrics (VPN tunnel state, NAT GW drops, TGW traffic, ELB health), alarms, Logs Insights queries, VPC/TGW flow log analysis |
| `aws-security-audit` | IAM users/roles/policies (read-only), MFA compliance, access key rotation, CloudTrail API event history, incident investigation |
| `aws-cost-ops` | Spending by service/region/tag, monthly trends, forecasts, anomaly detection, network cost drivers (NAT GW $0.045/GB, TGW $0.02/GB) |
| `aws-architecture-diagram` | Auto-discover infrastructure, render VPC/subnet/TGW topology as PNG/SVG/PDF (requires `graphviz`) |

#### Prerequisites

- AWS account with IAM user (programmatic access)
- `graphviz` for architecture diagrams: `apt install graphviz` or `brew install graphviz`
- `uv` (installed automatically by `install.sh`) for running AWS MCP servers via `uvx`

#### Cost Notes

- **Cost Explorer API**: $0.01 per API request — NetClaw batches queries but be mindful of frequent polling
- **CloudWatch Logs Insights**: Charged per GB scanned — use narrow time ranges
- **All other operations**: Standard AWS API calls (no additional charge beyond normal AWS usage)

### GCP (Google Cloud Platform)

**4 remote MCP servers, 3 skills** — compute, monitoring, and logging.

#### Key Difference: Remote HTTP Servers

Google Cloud MCP servers are **remote HTTP endpoints hosted by Google** — nothing to install locally. They use Streamable HTTP transport and authenticate via OAuth 2.0 / Google IAM, not API keys.

| MCP Server | Endpoint | Tools |
|---|---|---|
| Compute Engine | `https://compute.googleapis.com/mcp` | 28 tools — VMs, disks, templates, instance groups, snapshots, reservations |
| Cloud Monitoring | `https://monitoring.googleapis.com/mcp` | 6 tools — time series metrics, alert policies, active alerts, metric discovery |
| Cloud Logging | `https://logging.googleapis.com/mcp` | 6 tools — log search, VPC flow logs, firewall logs, audit logs, buckets |
| Resource Manager | `https://cloudresourcemanager.googleapis.com/mcp` | 1 tool — project discovery (prerequisite for other servers) |

#### Credentials

You need a Google Cloud project and either a service account or user credentials:

| Variable | Example | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `my-project-123` | Your Google Cloud project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | `/path/to/key.json` | Path to service account key JSON file |

Or use `gcloud` CLI for user-based auth: `gcloud auth application-default login`

Run `./scripts/setup.sh` — the wizard prompts for project ID and optional service account key path.

#### IAM Roles (Minimum Permissions)

Grant these roles to your service account or user:

| Role | What It Grants |
|------|---------------|
| `roles/compute.viewer` | Read-only access to all Compute Engine resources |
| `roles/monitoring.viewer` | Read-only access to Cloud Monitoring metrics and alerts |
| `roles/logging.viewer` | Read-only access to Cloud Logging log entries |
| `roles/resourcemanager.projectViewer` | Read-only access to project metadata |

For write operations (create/delete VMs via Compute Engine MCP), add `roles/compute.instanceAdmin.v1` — but use ServiceNow CR gating for any changes.

#### What You Can Do

| Skill | Capabilities |
|-------|-------------|
| `gcp-compute-ops` | List/create/start/stop/delete VMs, inspect disks and templates, manage instance groups, discover machine types and images, check reservations and commitments |
| `gcp-cloud-monitoring` | Query time series metrics (CPU, network, disk), list alert policies and active violations, discover available metric types |
| `gcp-cloud-logging` | Search log entries (VPC flow logs, firewall logs, audit logs), discover available logs, inspect log buckets and views |

#### Prerequisites

- Google Cloud project with APIs enabled (Compute Engine, Cloud Monitoring, Cloud Logging)
- Service account key JSON file, or `gcloud` CLI installed and authenticated
- No local install required — servers are hosted by Google

#### Cost Notes

- **Cloud Logging**: Charged per GB scanned beyond 50 GB/month free tier
- **Cloud Monitoring**: Free for GCP metrics; custom metrics charged per time series
- **Compute Engine API calls**: No additional charge

#### Networking Gap

GCP's MCP servers currently cover Compute Engine (VMs) but **not the VPC fabric** — there are no MCP tools for VPC subnets, firewall rules, Cloud VPN, Cloud Interconnect, or Cloud Router. Google is adding more MCP servers regularly, so VPC-specific tools may arrive soon.

### Cisco ThousandEyes

**2 MCP servers, 2 skills** — network monitoring and deep path analysis.

#### Key Difference: Two Complementary MCP Servers

ThousandEyes uses **two MCP servers** that share a single API token:

| MCP Server | Transport | Tools | Strength |
|---|---|---|---|
| Community (`thousandeyes-mcp-community`) | stdio (Python, local) | 9 read-only tools | Core monitoring: tests, agents, path vis, dashboards |
| Official (`api.thousandeyes.com/mcp`) | Remote HTTP (Cisco-hosted) | ~20 tools | Advanced: alerts, outages, BGP, instant tests, endpoint agents, AI |

The community server runs locally via stdio. The official server is a remote HTTP endpoint hosted by Cisco — no local install, accessed via `npx mcp-remote` with Bearer token authentication.

#### Credentials

| Variable | Example | Description |
|----------|---------|-------------|
| `TE_TOKEN` | `eyJhbGci...` | ThousandEyes API v7 OAuth bearer token (used by both servers) |

Get your token from: **ThousandEyes > Account Settings > Users & Roles > OAuth Bearer Token**

Run `./scripts/setup.sh` — the wizard prompts for the token.

#### What You Can Do

| Skill | Capabilities |
|-------|-------------|
| `te-network-monitoring` | List tests/agents, query test results, path visualization, dashboard widgets, alerts, events, outages, endpoint agents, anomalies, AI views explanations |
| `te-path-analysis` | Hop-by-hop path analysis (latency, loss, MPLS per hop), BGP route analysis (AS paths, prefix reachability from 300+ global monitors), outage investigation, instant on-demand tests, endpoint VPN diagnostics, BGP hijack/leak detection |

#### Prerequisites

- Cisco ThousandEyes account with API v7 access
- Python 3.12+ (for community MCP server)
- Node.js / npx (for official MCP server via `mcp-remote`)
- Org must not be opted out of ThousandEyes AI features (for official server)

#### Cost Notes

- **Community server tools**: Read-only, no additional cost beyond normal API usage
- **Instant Tests** (official server): Consume ThousandEyes test units — use judiciously
- **API rate limits**: Queries count against your org's ThousandEyes API rate limit

---

## How Skills Work

Each skill is a `SKILL.md` file with YAML frontmatter and markdown instructions. OpenClaw loads them into the agent context at session start.

```markdown
---
name: pyats-health-check
description: "Comprehensive device health monitoring..."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Device Health Check

(Step-by-step procedures, show command examples, threshold tables,
 report templates — everything the agent needs to work autonomously)
```

The `metadata.openclaw.requires` block declares binary and environment variable dependencies. The markdown body is the agent's playbook.

Every tool call goes through `scripts/mcp-call.py`, which handles MCP JSON-RPC protocol: initialize, notify, tool call, terminate. No persistent server connections, no port management.

```
python3 mcp-call.py "<server-command>" <tool-name> '<arguments-json>'
```

---

## Standard Workflows

### Health Check
```
pyats-health-check (+ pyats-parallel-ops for fleet)
--> CPU/memory/interface/BGP/OSPF/log/environmental assessment
--> Cross-reference NetBox for expected interface states
--> Severity ratings: HEALTHY / WARNING / CRITICAL / UNKNOWN
--> GAIT audit trail
```

### Source of Truth Reconciliation (NetBox)
```
netbox-reconcile
--> NetBox intent pull (devices, interfaces, IPs, VLANs, cables)
--> pyATS actual state collection (pCall across fleet)
--> Diff engine: IP_DRIFT / MISSING / UNDOCUMENTED / CABLE_MISMATCH
--> ServiceNow incident per CRITICAL discrepancy
--> Markmap drift summary
--> GAIT commit
```

### Nautobot IPAM Audit
```
nautobot-sot
--> test_connection: verify Nautobot API reachability
--> get_prefixes(site="Chicago-DC"): all subnets at site
--> get_ip_addresses per prefix: utilization analysis
--> get_ip_addresses(status="deprecated"): stale allocations
--> search_ip_addresses: investigate specific IPs
--> Report: IPAM utilization by site, prefix, VRF, tenant
```

### Infrahub Infrastructure Audit
```
infrahub-sot
--> get_schema_mapping: discover all available schema kinds
--> get_nodes(kind="InfraDevice"): retrieve full device inventory
--> get_related_nodes per device: interfaces, IPs, connections
--> branch_create("audit-2024"): isolated branch for analysis
--> query_graphql: custom queries for cross-referencing relationships
--> Report: infrastructure inventory with relationship completeness
--> GAIT audit trail
```

### Infrahub Branch-Based Change
```
infrahub-sot
--> get_branches: list existing branches and their status
--> branch_create("vlan-changes"): create isolated change branch
--> get_nodes(kind="InfraVLAN", branch="vlan-changes"): current VLAN state
--> query_graphql: mutation to create/update VLANs on branch
--> branch_diff: review all changes before merge
--> Report: branch change summary with before/after comparison
--> GAIT audit trail
```

### Itential Compliance Audit
```
itential-automation
--> get_health: verify Itential platform status (adapters, applications, system)
--> get_devices: discover managed device inventory
--> get_compliance_plans: list available compliance plans
--> run_compliance_plan: execute compliance check against target devices
--> describe_compliance_report: review results (pass/fail per device, violation details)
--> Report: compliance posture with remediation recommendations
--> GAIT audit trail
```

### Itential Golden Config Deployment
```
itential-automation
--> get_golden_config_trees: retrieve approved golden config templates
--> render_template: generate device-specific config from template + variables
--> backup_device_configuration: snapshot current config before changes
--> apply_device_configuration: push rendered config to device
--> get_device_configuration: verify applied config matches intent
--> Report: deployment status with before/after diff
--> GAIT audit trail
```

### Itential Workflow Orchestration
```
itential-automation
--> get_workflows: list available automation workflows
--> start_workflow: launch selected workflow with parameters
--> describe_job: monitor job progress, status, and output
--> get_job_metrics_for_workflow: execution statistics and performance
--> Report: workflow execution summary with results and metrics
--> GAIT audit trail
```

### Configuration Change
```
servicenow-change-workflow + pyats-config-mgmt
--> Pre-check: no open P1/P2 on affected CIs
--> ServiceNow CR created, approved
--> pyats-config-mgmt: baseline --> apply --> verify
--> ServiceNow CR closed
--> GAIT full session audit
```

### ACI Policy Change
```
servicenow-change-workflow + aci-change-deploy
--> CR created with tenant/policy scope
--> Fabric baseline (faults, contract counters)
--> APIC change applied (dependency order)
--> Fault delta check
--> CR closed / escalated
--> GAIT full session audit
```

### Security Audit
```
pyats-security
--> Management plane, AAA, ACLs, CoPP, routing auth, SNMP, encryption
--> ISE: verify device registered as NAD
--> NVD CVE: software version vulnerability scan (CVSS >= 7.0)
--> Exposure correlation: CVE + running-config
--> GAIT commit
```

### Endpoint Incident Response
```
ise-incident-response
--> Endpoint lookup by MAC/IP/username
--> Auth history, posture, profile review
--> Human decision point
--> [If authorized] ISE quarantine
--> ServiceNow Security Incident
--> GAIT audit trail
```

### Topology Discovery
```
pyats-topology
--> CDP/LLDP/ARP/routing peer collection (pCall across fleet)
--> NetBox cable reconciliation (documented / undocumented / missing)
--> Draw.io diagram (color-coded by reconciliation status)
--> Markmap mind map
--> GAIT commit
```

### F5 Load Balancer Health
```
f5-health-check
--> Virtual server stats (connections, throughput)
--> Pool member status (up/down/disabled)
--> Log analysis for errors
--> Severity assessment
--> GAIT audit
```

### Visio Topology to SharePoint
```
pyats-topology + msgraph-visio + msgraph-files
--> CDP/LLDP/ARP discovery (pCall across fleet)
--> Generate topology diagram
--> Upload .vsdx to SharePoint Network Engineering/Topology/
--> Post sharing link to Teams #netclaw-reports
--> GAIT audit
```

### Catalyst Center Client Investigation
```
catc-client-ops + catc-troubleshoot
--> Client lookup by MAC address
--> Connection details: SSID, band, AP, VLAN, health score
--> pyATS follow-up for switch-port state
--> GAIT audit
```

### Packet Capture Analysis (Slack Upload)
```
packet-analysis
--> User uploads .pcap file to Slack channel
--> NetClaw downloads and saves the file
--> pcap_summary: packet count, duration, capture size
--> pcap_protocol_hierarchy: protocol breakdown (TCP 45%, UDP 30%, DNS 15%...)
--> pcap_conversations: who talked to whom (IP pairs, byte counts)
--> pcap_expert_info: retransmissions, RSTs, errors flagged by tshark
--> pcap_filter + pcap_packet_detail: drill into suspect packets
--> AI analysis: plain-English summary of findings and recommendations
```

### NSO Device Sync and Service Audit
```
nso-device-ops + nso-service-mgmt
--> get_device_groups: list all managed device groups
--> check_device_sync for each device: identify out-of-sync devices
--> sync_from_device for out-of-sync devices: pull live config into NSO
--> get_service_types + get_services: inventory of deployed services
--> Report: "4 devices out of sync (re-synced), 12 L3VPN services healthy"
```

### CML Lab Build (Natural Language)
```
cml-lab-lifecycle + cml-topology-builder + cml-node-operations
--> "Build me a 3-router OSPF lab"
--> create_lab: new lab titled "OSPF Lab"
--> get_node_defs: verify IOSv available
--> create_node x3: R1, R2, R3 with grid layout
--> create_interface + create_link: wire R1-R2, R2-R3, R1-R3
--> set_node_config: apply OSPF startup configs
--> start_lab: boot all nodes
--> execute_command: "show ip ospf neighbor" to verify adjacencies
--> Report: "OSPF lab is ready — 3 routers, full mesh, all neighbors FULL"
```

### CML Packet Capture + Analysis
```
cml-packet-capture + packet-analysis
--> start_capture on R1-R2 link with filter "tcp port 179"
--> execute_command: "clear ip bgp *" to trigger BGP events
--> stop_capture + download_capture
--> Packet Buddy: pcap_summary, pcap_protocol_hierarchy, pcap_expert_info
--> AI analysis: "BGP OPEN/KEEPALIVE exchange completed in 2.3s, no NOTIFICATION errors"
```

### FMC Firewall Rule Audit
```
fmc-firewall-ops
--> list_fmc_profiles: discover all managed FMC instances
--> search_access_rules: search by IP/FQDN across all policies
--> For each match: rule name, action (allow/block), zones, networks, ports
--> Cross-reference: overly permissive rules (any/any), redundant, shadowed
--> Report: formatted rule table with security assessment
```

### Meraki Organization Inventory
```
meraki-network-ops
--> getOrganizations: list all accessible Meraki orgs
--> getOrganizationInventory: all claimed devices (model, serial, MAC, network)
--> getOrganizationLicense: license status, expiration, device counts
--> getDeviceStatus per key device: online/offline, last seen
--> getDeviceUplink for MX appliances: WAN link health
--> Report: org-wide inventory dashboard with status and license health
```

### Meraki Wireless Health
```
meraki-wireless-ops + meraki-monitoring
--> getWirelessSSIDs: enabled SSIDs, auth types, VLANs
--> getWirelessConnectionStats: auth/DHCP success rates
--> getWirelessChannelUtilization: per-AP congestion hotspots
--> getWirelessSignalQuality: SNR trends over time
--> getWirelessRFProfiles: power and channel settings
--> Report: wireless health dashboard with per-SSID metrics
```

### Meraki Switch Port Audit
```
meraki-switch-ops + meraki-monitoring
--> getDeviceSwitchPorts: all port configs (VLAN, type, PoE, BPDU guard)
--> getDeviceSwitchPortStatuses: live speed, duplex, errors, PoE draw
--> getSwitchVlans: VLAN inventory
--> createDeviceLiveToolsCableTest: cable diagnostics on suspect ports
--> Report: port table with status, errors, and cable health
```

### Meraki MX Firewall + VPN Audit
```
meraki-security-appliance
--> getNetworkSecurityFirewallRules: L3 outbound rules
--> getNetworkVpnStatus: site-to-site VPN tunnel state
--> getNetworkSecurityVpnSiteToSite: hub/spoke config, subnets
--> getNetworkSecurityContentFiltering: blocked categories
--> getNetworkSecuritySecurityEvents: IDS/IPS detections
--> Report: MX security posture with VPN health and rule assessment
```

### RADKit Remote Device Health Check
```
radkit-remote-access
--> get_device_inventory_names: discover all devices on RADKit service
--> get_device_attributes per device: type, platform, capabilities
--> snmp_get: sysUpTime, sysDescr for quick health baseline
--> exec_cli_commands_in_device: "show processes cpu", "show memory statistics"
--> Report: remote device inventory with health status across all sites
```

### RADKit Remote CLI Troubleshooting
```
radkit-remote-access
--> get_device_inventory_names: find target device
--> get_device_attributes: confirm CLI access available
--> exec_cli_commands_in_device with timeout=60, max_lines=200:
    "show ip interface brief", "show ip route summary",
    "show logging last 50", "show ip ospf neighbor"
--> exec_command: structured output for programmatic analysis
--> Report: troubleshooting findings with device state from remote site
```

### JunOS Device Health Check
```
junos-network
--> get_router_list: discover all Juniper routers
--> execute_junos_command_batch(routers, "show chassis alarms"): check hardware alarms
--> execute_junos_command_batch(routers, "show bgp summary"): verify BGP peer state
--> Severity-sort findings (CRITICAL alarms first)
--> GAIT audit trail
```

### Arista Network Health Check
```
arista-cvp
--> get_inventory: retrieve all devices from CloudVision Portal
--> get_events: pull recent events and alerts across the fabric
--> get_connectivity_monitor: check connectivity monitor probe status
--> Correlate events with connectivity monitor results
--> Severity-sort findings (CRITICAL events first)
--> GAIT audit trail
```

### Protocol Health Check (BGP + OSPF + GRE)
```
protocol-participation
--> protocol_summary: consolidated BGP + OSPF + GRE state
--> bgp_get_peers: verify all BGP sessions are Established
--> ospf_get_neighbors: verify all OSPF adjacencies are Full
--> gre_tunnel_status: verify all GRE tunnels are UP
--> pyats-routing: cross-verify from device CLI side
--> GAIT audit trail
```

### Route Injection with Change Control
```
servicenow-change-workflow + protocol-participation
--> ServiceNow CR created and approved
--> bgp_get_rib(prefix): verify route doesn't already exist
--> bgp_inject_route(network, next_hop, local_pref)
--> bgp_get_rib(prefix): verify route in RIB
--> pyats-routing: verify route propagation on remote devices
--> ServiceNow CR closed
--> GAIT audit trail
```

### SD-WAN Fabric Health Check
```
sdwan-ops
--> get_devices: verify all controllers and edges are reachable
--> get_wan_edge_inventory: check serial numbers, versions, models
--> get_alarms: identify active issues (CRITICAL, MAJOR, MINOR)
--> get_control_connections per device: verify DTLS/TLS tunnels
--> get_bfd_sessions per device: check tunnel health
--> Report: fabric status summary with severity-sorted findings
--> GAIT audit trail
```

### Grafana Infrastructure Monitoring
```
grafana-observability
--> search_dashboards(title="Network"): find network-related dashboards
--> get_dashboard_summary(uid): lightweight overview of panels
--> query_prometheus(expr="rate(ifHCInOctets{device='core-rtr-01'}[5m])*8"): interface traffic
--> query_prometheus(expr="device_cpu_utilization{device=~'.*'}"): CPU across fleet
--> list_alert_rules(folder="Network"): check alerting thresholds
--> query_loki_logs(query='{host="core-rtr-01"} |= "error"'): syslog errors
--> Report: infrastructure metrics with alert status and log correlation
--> GAIT audit trail
```

### Grafana Alert Investigation
```
grafana-observability
--> list_alert_rules: find firing or pending alert rules
--> get_alert_rule_by_uid: threshold, conditions, datasource details
--> query_prometheus: check the metric that triggered the alert
--> query_loki_logs: correlate with log events around alert time
--> list_incidents: check if already tracked
--> list_contact_points: verify notification routes
--> Report: alert analysis with root cause and metric evidence
--> GAIT audit trail
```

### Prometheus Metric Investigation
```
prometheus-monitoring
--> health_check: verify Prometheus is reachable
--> list_metrics(page=1, page_size=50): discover available metric names
--> get_metric_metadata(metric="ifHCInOctets"): check type, help, unit
--> execute_query(query="up{job='snmp'}"): check which targets are up
--> execute_range_query(query="rate(ifHCInOctets{device='core-rtr-01'}[5m])*8", start, end, step="60s"): interface traffic trend
--> get_targets: verify SNMP exporter scrape health
--> Report: metric analysis with current values and trends
--> GAIT audit trail
```

### Kubeshark Service Troubleshooting
```
kubeshark-traffic
--> capture_traffic(filter="dst.pod.name == 'api-gateway'"): start targeted K8s capture
--> list_l4_flows: TCP/UDP connections with RTT, byte counts, duration
--> get_l4_flow_summary: top talkers, protocol distribution, traffic volume
--> apply_filter(kfl_expression="response.status >= 500"): isolate HTTP 5xx errors
--> export_pcap: export for Wireshark/tshark deep analysis
--> packet-analysis: analyze exported pcap with Packet Buddy
--> Report: service communication analysis with latency and error patterns
--> GAIT audit trail
```

### SD-WAN Policy Audit
```
sdwan-ops
--> get_device_templates: list all templates with device counts
--> get_feature_templates: inspect VPN, interface, routing, security templates
--> get_centralized_policies: review traffic engineering and security policies
--> get_running_config per device: confirm template-applied config
--> Report: template and policy audit with recommendations
--> GAIT audit trail
```

### JunOS OSPF/BGP Health Check
```
pyats-junos-routing + pyats-junos-system
--> show chassis alarms: check for hardware alarms
--> show ospf neighbor: verify all OSPF adjacencies are Full
--> show bgp summary: verify all BGP peers are Established
--> show route summary: route table size and protocol breakdown
--> Severity-sort findings (non-Full/non-Established first)
--> GAIT audit trail
```

### ASA VPN Monitoring
```
pyats-asa-firewall
--> show failover: verify active/standby state and failover health
--> show vpn-sessiondb summary: total active VPN sessions by type
--> show vpn-sessiondb anyconnect: detailed AnyConnect session list
--> show ip local pool: VPN address pool utilization
--> Flag pool exhaustion (>80% utilization)
--> GAIT audit trail
```

### Linux Host Fleet Health Check
```
pyats-linux-system + pyats-linux-network
--> pyats_list_devices: identify Linux hosts in testbed
--> pyats_run_linux_command("ps -ef") per host: process inventory
--> pyats_run_linux_command("docker stats --no-stream") per host: container CPU/memory
--> pyats_run_linux_command("ifconfig") per host: interface state and IP addressing
--> Severity-sort findings (CRITICAL container resource usage first)
--> GAIT audit trail
```

### ThousandEyes Path Troubleshooting
```
te-network-monitoring + te-path-analysis
--> te_list_tests: find tests targeting the slow site
--> te_get_test_results: check latency, packet loss, jitter
--> te_get_path_vis: hop-by-hop path from agent to target
--> Get Full Path Visualization (official): all agents, compare paths
--> Identify hop where latency spikes or loss appears
--> Get BGP Route Details (official): is routing suboptimal?
--> Get Anomalies (official): when did degradation start?
--> Report: "Latency increase at hop 7 (ISP backbone), AS path changed at 14:32 UTC"
```

### ThousandEyes Outage Investigation
```
te-path-analysis
--> Search Outages (official): scope — ISP, CDN, SaaS provider?
--> List Events (official): which tests are affected?
--> Get Event Details (official): impacted targets, severity, timeline
--> te_get_path_vis (community): where does the path break?
--> Get BGP Test Results (official): prefix still reachable? Route withdrawn?
--> Instant Tests (official): verify from multiple cloud agents
--> Report: outage scope, affected services, root cause, estimated recovery
```

### ThousandEyes Endpoint VPN Diagnostics
```
te-path-analysis
--> List Endpoint Agents and Tests (official): find affected users
--> Get Endpoint Agent Metrics (official): WiFi signal, DNS, VPN latency
--> Get Path Visualization (official): user to VPN gateway path
--> Compare with enterprise agent test: user-side vs network-side?
--> Get Anomalies (official): when did metrics degrade?
--> Report: "WiFi -72 dBm (poor), DNS 450ms (ISP slow), VPN 180ms — switch to 5 GHz, use corporate DNS"
```

### AWS VPC Network Audit
```
aws-network-ops
--> list_vpcs: discover all VPCs in region
--> get_vpc_network_details: subnets, route tables, IGW, NAT GW, NACLs per VPC
--> list_transit_gateways: check cross-VPC connectivity
--> list_vpn_connections: hybrid connectivity with tunnel state
--> list_network_firewalls: security posture
--> Report: formatted cloud network architecture summary
```

### AWS Connectivity Troubleshooting
```
aws-network-ops + aws-cloud-monitoring
--> find_ip_address: locate source and destination in VPC/subnet/ENI
--> get_eni_details: check security groups, subnet, route table
--> get_vpc_flow_logs: check for REJECT entries
--> get_firewall_rules: if traffic crosses Network Firewall
--> get_tgw_routes: if traffic crosses Transit Gateway
--> CloudWatch metrics: NAT GW drops, TGW blackhole routes
--> Report: root cause analysis with fix recommendation
```

### AWS Cost Analysis
```
aws-cost-ops
--> Network service spend: VPC, TGW, NAT GW, VPN, ELB, Direct Connect
--> Monthly trend: 6-month network cost history
--> Top drivers: rank by spend (NAT GW data processing usually #1)
--> Per-region breakdown
--> Forecast: projected next month
--> Report: network cost dashboard with optimization tips
```

### GCP Infrastructure Audit
```
gcp-compute-ops + gcp-cloud-monitoring
--> search_projects: discover all accessible GCP projects
--> list_instances: VMs per project with status, zone, machine type, IPs
--> list_instance_group_managers: autoscaled workloads
--> list_disks: persistent disk inventory
--> list_timeseries: CPU utilization, network throughput for flagged instances
--> list_alerts: any active monitoring violations
--> Report: GCP compute inventory with health status
```

### GCP Log Investigation
```
gcp-cloud-logging + gcp-cloud-monitoring
--> list_log_names: discover available log sources
--> list_log_entries: query VPC flow logs (denied traffic, top talkers)
--> list_log_entries: query firewall logs (rule hits, blocked connections)
--> list_log_entries: query audit logs (who changed what, when)
--> list_alerts: correlate with monitoring alert violations
--> Report: traffic analysis / security investigation with log evidence
```

### Config-as-Code (GitHub)
```
github-ops
--> Network finding discovered (e.g., security audit failure)
--> Create GitHub issue with device, symptom, recommended fix
--> After remediation: commit updated config to repo
--> Open PR with change details + ServiceNow CR reference
--> GAIT audit trail links to the PR
```

---

## Safety

NetClaw enforces non-negotiable constraints at every layer:

**Never guesses device state** — runs a show command or queries NetBox first, always.

**Never touches a device without a baseline** — pre-change state is captured and committed to GAIT before any config push.

**Never skips the Change Request** — ServiceNow CR must exist and be in `Approved` state before execution (except Emergency changes, which require immediate human notification).

**Never runs destructive commands** — `write erase`, `erase`, `reload`, `delete`, `format` are refused at the MCP server level.

**Never auto-quarantines an endpoint** — ISE endpoint group modification always requires explicit human confirmation.

**NetBox is read-write** — NetClaw has full API access to create and update devices, IPs, interfaces, VLANs, and cables in NetBox.

**Always verifies after changes** — if post-change verification fails, the CR is not closed and the human is notified.

**Always commits to GAIT** — every session ends with `gait_log` so the human can see the full audit trail.

---

## GAIT Audit Trail

Every NetClaw session produces an immutable Git-based record of:
- What was asked
- What data was collected (and from where)
- What was analyzed (and what conclusions were reached)
- What was changed (and on what device)
- What the verification result was
- What ServiceNow tickets were created or updated

This is not optional. It is how NetClaw earns trust in production environments.

---

## Project Structure

```
netclaw/
├── SOUL.md                               # Agent personality, expertise, rules
├── AGENTS.md                             # Operating instructions, memory, safety
├── IDENTITY.md                           # Name, creature type, vibe, emoji
├── USER.md                               # Your preferences (edit this)
├── TOOLS.md                              # Local infrastructure notes (edit this)
├── HEARTBEAT.md                          # Periodic health check checklist
├── MISSION01.md                          # Completed — core pyATS + 11 skills
├── MISSION02.md                          # Completed — full platform, 78 skills, 32 MCP
├── workspace/
│   └── skills/                           # 82 skill definitions (source of truth)
│       ├── pyats-network/                # Core device automation (8 MCP tools)
│       ├── pyats-health-check/           # Health + NetBox cross-ref + pCall
│       ├── pyats-routing/                # OSPF, BGP, EIGRP, IS-IS analysis
│       ├── pyats-security/               # Security + ISE + NVD CVE + pCall
│       ├── pyats-topology/               # Discovery + NetBox reconciliation + pCall
│       ├── pyats-config-mgmt/            # Change control + ServiceNow + GAIT
│       ├── pyats-troubleshoot/           # Troubleshooting + pCall + NetBox + GAIT
│       ├── pyats-dynamic-test/           # pyATS aetest script generation
│       ├── pyats-parallel-ops/           # Fleet-wide pCall operations
│       ├── pyats-linux-system/          # Linux host system ops (ps, docker stats, ls, curl)
│       ├── pyats-linux-network/         # Linux host network ops (ifconfig, ip route, netstat)
│       ├── pyats-linux-vmware/          # VMware ESXi host ops (vim-cmd vmsvc)
│       ├── pyats-junos-system/         # JunOS chassis health, hardware, NTP, SNMP, logs
│       ├── pyats-junos-interfaces/     # JunOS interfaces, LACP, CoS, LLDP, ARP, BFD
│       ├── pyats-junos-routing/        # JunOS OSPF/BGP, route table, MPLS/LDP/RSVP
│       ├── pyats-asa-firewall/         # Cisco ASA VPN sessions, failover, ASP drops
│       ├── pyats-f5-ltm/             # F5 BIG-IP LTM/GTM via pyATS iControl REST
│       ├── pyats-f5-platform/        # F5 BIG-IP platform ops via pyATS iControl REST
│       ├── netbox-reconcile/             # Source of truth drift detection
│       ├── nautobot-sot/                # Nautobot IPAM — IPs, prefixes, VRF/tenant
│       ├── infrahub-sot/               # Infrahub schema-driven SoT, GraphQL, branches
│       ├── itential-automation/        # Itential IAP orchestration, compliance, golden config
│       ├── aci-fabric-audit/             # ACI fabric health & policy audit
│       ├── aci-change-deploy/            # Safe ACI policy changes
│       ├── ise-posture-audit/            # ISE posture & TrustSec audit
│       ├── ise-incident-response/        # Endpoint investigation & quarantine
│       ├── servicenow-change-workflow/   # Full ITSM change lifecycle
│       ├── gait-session-tracking/        # Mandatory audit trail
│       ├── f5-health-check/              # F5 virtual server & pool health
│       ├── f5-config-mgmt/              # F5 object lifecycle management
│       ├── f5-troubleshoot/             # F5 troubleshooting workflows
│       ├── catc-inventory/              # Catalyst Center device inventory
│       ├── catc-client-ops/             # Catalyst Center client monitoring
│       ├── catc-troubleshoot/           # Catalyst Center troubleshooting
│       ├── msgraph-files/                # OneDrive/SharePoint file operations
│       ├── msgraph-visio/                # Visio diagram generation
│       ├── msgraph-teams/                # Teams channel notifications
│       ├── nvd-cve/                      # NVD vulnerability search (CVSS)
│       ├── subnet-calculator/            # IPv4 + IPv6 CIDR calculator
│       ├── wikipedia-research/           # Protocol history & context
│       ├── markmap-viz/                  # Mind map visualization
│       ├── drawio-diagram/              # Draw.io network diagrams
│       ├── uml-diagram/                 # 27+ UML/diagram types via Kroki
│       ├── rfc-lookup/                   # IETF RFC search
│       ├── github-ops/                  # GitHub issues, PRs, config-as-code
│       ├── packet-analysis/             # pcap analysis via tshark + Slack upload
│       ├── cml-lab-lifecycle/          # CML lab create, start, stop, delete, clone
│       ├── cml-topology-builder/       # CML nodes, interfaces, links, annotations
│       ├── cml-node-operations/        # CML node start/stop, configs, CLI exec
│       ├── cml-packet-capture/         # CML link packet capture + Packet Buddy
│       ├── cml-admin/                  # CML users, groups, system, licensing
│       ├── nso-device-ops/             # NSO device config, state, sync, platform
│       ├── nso-service-mgmt/           # NSO service types and instances
│       ├── fmc-firewall-ops/          # FMC access policy search, FTD targeting
│       ├── radkit-remote-access/     # RADKit cloud-relayed CLI, SNMP, device inventory
│       ├── junos-network/           # Juniper JunOS PyEZ/NETCONF automation
│       ├── arista-cvp/              # Arista CloudVision Portal inventory, events, tags
│       ├── protocol-participation/ # Live BGP/OSPF/GRE control-plane participation (10 tools)
│       ├── clab-lab-management/  # ContainerLab lab lifecycle via API (6 tools)
│       ├── sdwan-ops/            # Cisco SD-WAN vManage read-only monitoring (12 tools)
│       ├── grafana-observability/ # Grafana dashboards, Prometheus, Loki, alerting, incidents (75+ tools)
│       ├── prometheus-monitoring/ # Direct Prometheus PromQL queries, metric discovery, target health (6 tools)
│       ├── kubeshark-traffic/    # Kubeshark K8s L4/L7 traffic analysis, TLS decryption, pcap export (6 tools)
│       ├── meraki-network-ops/       # Meraki org inventory, networks, devices, clients
│       ├── meraki-wireless-ops/      # Meraki SSIDs, RF profiles, channel utilization
│       ├── meraki-switch-ops/        # Meraki switch ports, VLANs, ACLs, QoS
│       ├── meraki-security-appliance/ # Meraki MX firewall, VPN, content filtering
│       ├── meraki-monitoring/        # Meraki diagnostics, cameras, config change audit
│       ├── te-network-monitoring/   # ThousandEyes tests, agents, dashboards, alerts, events
│       ├── te-path-analysis/        # ThousandEyes path vis, BGP, outages, instant tests
│       ├── aws-network-ops/           # AWS VPC, TGW, Cloud WAN, VPN, Firewall (27 tools)
│       ├── aws-cloud-monitoring/      # AWS CloudWatch metrics, alarms, flow logs
│       ├── aws-security-audit/        # AWS IAM + CloudTrail security posture
│       ├── aws-cost-ops/              # AWS Cost Explorer spending analysis
│       ├── aws-architecture-diagram/  # AWS architecture visualization (graphviz)
│       ├── gcp-compute-ops/           # GCP VMs, disks, templates, instance groups
│       ├── gcp-cloud-monitoring/      # GCP metrics, alerts, time series
│       ├── gcp-cloud-logging/         # GCP log search, VPC flow logs, audit logs
│       ├── slack-network-alerts/         # Slack alert delivery
│       ├── slack-report-delivery/        # Slack report formatting
│       ├── slack-incident-workflow/      # Slack incident lifecycle
│       └── slack-user-context/           # Slack user-aware routing
├── testbed/
│   └── testbed.yaml                      # pyATS testbed (your network devices)
├── config/
│   └── openclaw.json                     # OpenClaw model config (template)
├── mcp-servers/                          # Created by install.sh (gitignored)
│   ├── pyATS_MCP/                        # Device automation
│   ├── markmap_mcp/                      # Mind map visualization
│   ├── gait_mcp/                         # Git-based audit trail
│   ├── netbox-mcp-server/                # DCIM/IPAM source of truth
│   ├── servicenow-mcp/                   # ITSM integration
│   ├── ACI_MCP/                          # Cisco ACI / APIC
│   ├── ISE_MCP/                          # Cisco ISE
│   ├── Wikipedia_MCP/                    # Technology context
│   ├── mcp-nvd/                          # NVD CVE database (Python)
│   ├── subnet-calculator-mcp/            # IPv4 + IPv6 subnet calculator
│   ├── f5-mcp-server/                    # F5 BIG-IP iControl REST
│   ├── catalyst-center-mcp/              # Cisco Catalyst Center / DNA-C
│   ├── packet-buddy-mcp/                 # pcap analysis via tshark (built-in)
│   ├── CiscoFMC-MCP-server-community/   # Cisco FMC firewall policy search
│   ├── meraki-magic-mcp-community/      # Cisco Meraki Dashboard (~804 API endpoints)
│   ├── thousandeyes-mcp-community/     # ThousandEyes monitoring (9 read-only tools)
│   ├── radkit-mcp-server-community/   # Cisco RADKit cloud-relayed device access (5 tools)
│   ├── mcp-nautobot/                  # Nautobot IPAM source of truth (5 tools)
│   ├── infrahub-mcp/                 # OpsMill Infrahub schema-driven SoT (10 tools)
│   ├── itential-mcp/                 # Itential IAP network automation (65+ tools)
│   ├── junos-mcp-server/            # Juniper JunOS PyEZ/NETCONF (10 tools)
│   ├── mcp-cvp-fun/                # Arista CloudVision Portal (4 tools)
│   ├── uml-mcp/                         # 27+ diagram types via Kroki (2 tools)
│   ├── protocol-mcp/                   # BGP/OSPF/GRE protocol speakers (10 tools)
│   ├── clab-mcp-server/               # ContainerLab lab management (6 tools)
│   └── cisco-sdwan-mcp/               # Cisco SD-WAN vManage monitoring (12 tools)
├── lab/
│   └── frr-testbed/                     # Docker FRR 3-router lab for protocol testing
├── scripts/
│   ├── install.sh                        # Full bootstrap installer (45 steps)
│   ├── setup.sh                          # Interactive setup wizard (API key, platforms, Slack)
│   ├── mcp-call.py                       # MCP JSON-RPC protocol handler
│   └── gait-stdio.py                     # GAIT server stdio wrapper
├── examples/
│   ├── 01_health_check.md
│   ├── 02_vulnerability_audit.md
│   ├── 03_topology_diagram.md
│   ├── 04_ospf_mindmap.md
│   ├── 05_rfc_config.md
│   └── 06_full_audit.md
├── .env.example
├── .gitignore
└── README.md
```

### What Goes Where

| Location | Purpose |
|----------|---------|
| `SOUL.md` | Agent system prompt. Defines personality, CCIE expertise, rules, and workflow orchestration |
| `AGENTS.md` | Operating instructions. Memory system, safety rules, change management, Slack behavior, escalation |
| `IDENTITY.md` | Agent identity card. Name, creature type, vibe, emoji |
| `USER.md` | About you. Preferences, timezone, role, network details. **Edit this.** |
| `TOOLS.md` | Local infrastructure. Device IPs, SSH hosts, Slack channels. **Edit this.** |
| `HEARTBEAT.md` | Periodic checks. Device reachability, OSPF/BGP state, CPU/memory, syslog. |
| `workspace/skills/` | Skill source files. `install.sh` copies these to `~/.openclaw/workspace/skills/` |
| `testbed/testbed.yaml` | pyATS device inventory. Referenced by `PYATS_TESTBED_PATH` env var |
| `config/openclaw.json` | Model config template. Sets primary/fallback model only — no MCP config |
| `mcp-servers/` | Tool backends cloned by `install.sh`. Gitignored — rebuilt on install |
| `scripts/mcp-call.py` | Handles MCP JSON-RPC protocol: initialize, notify, tool call, terminate |
| `scripts/gait-stdio.py` | Wraps GAIT MCP server for stdio mode (default is SSE) |

---

## What install.sh Does

1. **Checks prerequisites** — Node.js >= 18, Python 3, pip3, git, npx
2. **Installs OpenClaw** — `npm install -g openclaw@latest`
3. **Runs OpenClaw onboard** — AI provider, gateway, channels, daemon service
4. **Creates mcp-servers/** — directory for all cloned backends
5. **Clones pyATS MCP** — `git clone` + `pip3 install -r requirements.txt`
6. **Clones Markmap MCP** — `git clone` + `npm install` + `npm run build`
7. **Clones Arista CVP MCP** — `git clone noredistribution/mcp-cvp-fun` + `uv` runtime deps for CloudVision Portal REST API (4 tools: device inventory, events, connectivity monitor, tag management). Requires CVP service account token.
8. **Clones GAIT MCP** — `git clone` + `pip3 install gait-ai fastmcp`
9. **Clones NetBox MCP** — `git clone` + `pip3 install` dependencies
10. **Clones Nautobot MCP** — `git clone` + `pip3 install -e .` for Nautobot IPAM source of truth (5 tools: IP addresses, prefixes, VRF/tenant/site filtering, search, connection test). Python 3.13+ required; falls back to core deps on older Python. Alternative to NetBox.
11. **Clones Infrahub MCP** — `git clone` + `pip3 install -e .` for OpsMill Infrahub schema-driven source of truth (10 tools: nodes, GraphQL queries, versioned branches). Requires Infrahub instance with API token.
12. **Installs Itential MCP** — `pip3 install itential-mcp` (falls back to `git clone` + `pip3 install -e .`) for Itential Automation Platform network orchestration (65+ tools: config mgmt, compliance, workflows, golden config, lifecycle). Requires IAP instance with credentials.
13. **Clones ServiceNow MCP** — `git clone` + `pip3 install` dependencies
14. **Clones ACI MCP** — `git clone` + `pip3 install` dependencies
15. **Clones ISE MCP** — `git clone` + `pip3 install` dependencies
16. **Clones Wikipedia MCP** — `git clone` + `pip3 install` dependencies
17. **Clones NVD CVE MCP** — `git clone` + `pip3 install -e .`
18. **Clones Subnet Calculator MCP** — `git clone` (enhanced with IPv6 support)
19. **Clones F5 BIG-IP MCP** — `git clone` + `pip3 install` dependencies
20. **Clones Catalyst Center MCP** — `git clone` + `pip3 install` dependencies
21. **Caches Microsoft Graph MCP** — `npm cache add` for Graph API (OneDrive, SharePoint, Visio, Teams)
22. **Caches npx packages** — `npm cache add` for Draw.io and RFC servers
23. **Pulls GitHub MCP** — `docker pull ghcr.io/github/github-mcp-server` (requires Docker)
24. **Installs Packet Buddy MCP** — verifies/installs tshark, creates pcap upload directory
25. **Installs CML MCP** — `pip3 install cml-mcp` (requires Python 3.12+, CML 2.9+)
26. **Installs NSO MCP** — `pip3 install cisco-nso-mcp-server` (requires Python 3.12+, NSO with RESTCONF)
27. **Installs FMC MCP** — `git clone` + `pip3 install -r requirements.txt` for Cisco Secure Firewall policy search (HTTP transport, port 8000)
28. **Installs Meraki Magic MCP** — `git clone` + `pip install -r requirements.txt` for Cisco Meraki Dashboard API (~804 endpoints: orgs, networks, wireless, switching, security, cameras, diagnostics). Python 3.13+ recommended; falls back to core deps on older Python.
29. **Installs ThousandEyes Community MCP** — `git clone` + `pip install -r requirements.txt` for ThousandEyes monitoring (9 read-only tools: tests, agents, path vis, dashboards). Python 3.12+ required.
30. **Configures ThousandEyes Official MCP** — Remote HTTP endpoint hosted by Cisco at `https://api.thousandeyes.com/mcp` (~20 tools: alerts, outages, BGP, instant tests, endpoint agents). Pre-caches `mcp-remote` via npm. No local install required.
31. **Installs RADKit MCP** — `git clone` + `pip install -e .` for Cisco RADKit cloud-relayed remote device access (5 tools: device inventory, attributes, CLI exec, SNMP GET, structured exec). Python 3.10+ required. Certificate-based auth via RADKit service.
32. **Installs AWS Cloud MCP Servers** — Installs `uv` (Astral), validates 6 AWS MCP packages via `uvx` (Network, CloudWatch, IAM, CloudTrail, Cost Explorer, Diagram)
33. **Configures GCP Cloud MCP Servers** — Checks for `gcloud` CLI and credentials; 4 remote HTTP servers hosted by Google (Compute Engine, Cloud Monitoring, Cloud Logging, Resource Manager)
34. **Installs JunOS MCP** — `git clone` + `pip3 install -r requirements.txt` for Juniper JunOS device automation via PyEZ/NETCONF (10 tools: CLI execution, config management, Jinja2 templates, device facts, batch operations). Python 3.10+ required.
35. **Installs UML MCP** — `git clone` + `pip3 install -e .` for 27+ diagram types via Kroki multi-engine rendering (2 tools: generate_uml, generate_diagram_url). Python 3.10+ required. nwdiag (network), rackdiag (rack), packetdiag (protocol headers), sequence, state, class, C4, Mermaid, D2, Graphviz, ERD, BPMN.
36. **Installs ContainerLab MCP** — `git clone` + `pip3 install -r requirements.txt` for containerized network lab lifecycle management via ContainerLab API (6 tools: authenticate, list, deploy, inspect, exec, destroy). Supports SR Linux, cEOS, FRR, Cisco IOS-XR/XE/NX-OS, and more.
37. **Installs SD-WAN MCP** — `git clone` + `pip3 install` deps (fastmcp, requests, python-dotenv) for Cisco SD-WAN vManage read-only monitoring (12 tools: fabric devices, WAN Edge inventory, templates, policies, alarms, BFD, OMP routes, control connections, running config).
38. **Installs Grafana MCP** — Validates `uvx` availability for running `mcp-grafana` (Go binary, 75+ tools: dashboards, Prometheus PromQL, Loki LogQL, alerting, incidents, OnCall, annotations, panel rendering). Requires Grafana 9.0+ with service account token.
39. **Installs Prometheus MCP** — `pip3 install prometheus-mcp-server` for direct Prometheus monitoring (6 tools: instant/range PromQL queries, metric discovery with pagination, metric metadata, scrape target health, system health check). Supports basic auth, bearer tokens, and multi-tenant org IDs.
40. **Configures Kubeshark MCP** — Checks for `kubectl`; Kubeshark MCP is a remote HTTP endpoint running inside a Kubernetes cluster (6 tools: traffic capture, pcap export, snapshots, KFL filtering, L4 flow stats, TLS decryption). Requires Kubeshark deployed via Helm with `mcp.enabled=true`.
41. **Installs Protocol MCP** — `pip3 install -r requirements.txt` (scapy, networkx, mcp, fastmcp) for live BGP/OSPF/GRE control-plane participation (10 tools: peer with routers, inject/withdraw routes, query RIB/LSDB, adjust metrics). Protocol speakers from WontYouBeMyNeighbour.
42. **Protocol Peering Wizard** — Optional interactive configuration: router ID, local AS, BGP peer IP/AS, OSPF areas, GRE tunnels, lab mode. Writes protocol environment variables to `~/.openclaw/.env`. Optionally creates GRE tunnel (requires sudo).
43. **Deploys skills + workspace files** — Copies 82 skills and 6 MD files to `~/.openclaw/workspace/`
44. **Verifies installation** — Checks all MCP server scripts + core scripts exist
45. **Prints summary** — Lists all 37 MCP servers by category and all 82 skills by domain

---

## Testbed Configuration

Edit `testbed/testbed.yaml` to define your network devices:

```yaml
devices:
  R1:
    alias: "Core Router"
    type: router
    os: iosxe
    platform: CSR1kv
    credentials:
      default:
        username: admin
        password: "%ENV{NETCLAW_PASSWORD}"
    connections:
      cli:
        protocol: ssh
        ip: your-device-hostname-or-ip
        port: 22
```

The `%ENV{NETCLAW_PASSWORD}` syntax pulls credentials from environment variables so they stay out of version control.

---

## Prerequisites

- Node.js >= 18 (>= 22 recommended for OpenClaw)
- Python 3.x with pip3
- git
- Network devices accessible via SSH (for pyATS)
- Anthropic API key

Optional (for full feature set):
- NetBox instance with API token (or Nautobot instance with API token — alternative source of truth)
- ServiceNow instance with credentials
- Cisco APIC with credentials (for ACI skills)
- Cisco ISE with ERS API enabled (for ISE skills)
- NVD API key (free from https://nvd.nist.gov/developers/request-an-api-key)
- F5 BIG-IP management access with iControl REST enabled
- Cisco Catalyst Center (DNA Center) with API credentials
- Docker (for GitHub MCP server)
- tshark / Wireshark (for Packet Buddy pcap analysis — `apt install tshark`)
- GitHub PAT with repo scope (for GitHub MCP — https://github.com/settings/tokens)
- Cisco CML 2.9+ with API access and Python 3.12+ (for CML lab management)
- Cisco NSO with RESTCONF API enabled and Python 3.12+ (for NSO orchestration)
- Cisco Secure Firewall Management Center (FMC) with API access (for firewall policy search)
- Cisco Meraki Dashboard with API key and Organization ID (for Meraki wireless, switching, security, camera, and diagnostics skills — Python 3.13+ recommended)
- Cisco ThousandEyes account with API v7 OAuth bearer token and Python 3.12+ (for network monitoring, path visualization, BGP analysis, and outage investigation skills)
- Cisco RADKit service instance with onboarded devices and certificate-based identity, Python 3.10+ (for cloud-relayed remote device CLI/SNMP access)
- Juniper devices with NETCONF enabled and Python 3.10+ with PyEZ (for JunOS device automation — CLI, config, templates, facts, batch ops)
- Arista CloudVision Portal with service account token, Python 3.12+ and `uv` (for CVP device inventory, events, connectivity monitoring, tag management)
- AWS account with IAM credentials (`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`) for AWS cloud skills
- graphviz (`apt install graphviz` or `brew install graphviz`) for AWS architecture diagrams
- OpsMill Infrahub instance + API token (optional — schema-driven source of truth alternative)
- Itential Automation Platform instance + credentials (optional — network orchestration, compliance, golden config)
- Google Cloud project with service account or `gcloud` CLI (for GCP Compute, Monitoring, Logging skills)
- Microsoft 365 tenant with Azure AD app registration (for Graph/Visio/Teams skills)
- ContainerLab API server with PAM-authenticated Linux user (for containerized network lab management)
- Cisco SD-WAN vManage instance with API access (for SD-WAN fabric monitoring — read-only)
- Grafana 9.0+ with service account token (Editor role or granular RBAC) and `uvx` (for Grafana observability — dashboards, Prometheus, Loki, alerting, incidents, OnCall)
- Prometheus server with HTTP API access (for direct PromQL monitoring — instant/range queries, metric discovery, scrape target health)
- Kubernetes cluster with Kubeshark deployed via Helm and `kubectl` (for K8s L4/L7 traffic analysis — capture, pcap export, flow stats, TLS decryption)
- Docker for FRR lab testbed (optional — 3-router FRR topology for testing BGP/OSPF protocol participation)
- Root/sudo access for GRE tunnel creation (optional — required for BGP/OSPF peering over GRE tunnels)
- Kroki local instance (optional — public kroki.io used by default; local instance recommended for sensitive topology data)
- Slack workspace with NetClaw bot installed (for Slack skills)

---

## Example Conversations

Ask NetClaw anything you'd ask a senior network engineer:

```
"Run a health check on all devices"
--> pyats-health-check + pyats-parallel-ops: fleet-wide assessment, severity-sorted report

"Reconcile NetBox against the live network"
--> netbox-reconcile: drift detection, ServiceNow incidents for CRITICAL findings

"Is R1 vulnerable to any known CVEs?"
--> pyats-network (show version) + nvd-cve (search by IOS-XE version + CVSS scoring)

"Add a Loopback99 interface with IP 99.99.99.99/32"
--> servicenow-change-workflow (CR) + pyats-config-mgmt (baseline/apply/verify) + GAIT

"BGP peer 10.1.1.2 is down, help me fix it"
--> pyats-troubleshoot: parallel state from both peers, 9-item BGP checklist

"Audit the ACI fabric health"
--> aci-fabric-audit: nodes, policies, faults, endpoint learning

"Investigate endpoint 00:11:22:33:44:55"
--> ise-incident-response: auth history, posture, profile --> human decision point

"Check the F5 load balancer health"
--> f5-health-check: virtual server stats, pool member status, active connections

"What clients are connected to Site-A?"
--> catc-client-ops: client list filtered by site, SSID, band, health scores

"Calculate a /22 for the 10.50.0.0 network"
--> subnet-calculator: VLSM breakdown, usable hosts, wildcard mask, CIDR notation

"Generate a Visio topology diagram and upload it to SharePoint"
--> pyats-topology (CDP/LLDP discovery) + msgraph-visio (generate .vsdx) + msgraph-files (upload to SharePoint)

"Post the health report to Teams"
--> pyats-health-check + msgraph-teams (send HTML-formatted report to #netclaw-reports)

"Show me the OSPF topology as a mind map"
--> pyats-routing (OSPF neighbors/database) + markmap-viz (generate mind map)

"What does RFC 4271 say about BGP hold timers?"
--> rfc-lookup: fetch RFC 4271, extract relevant section

[upload capture.pcap to Slack] "What's in this capture?"
--> packet-analysis: summary, protocol hierarchy, conversations, expert info, AI findings

"Analyze the DNS traffic in that pcap"
--> packet-analysis: pcap_dns_queries, pcap_filter (dns), plain-English analysis

"Create a GitHub issue for the BGP flapping on R3"
--> github-ops: create issue with device details, symptoms, logs, recommended fix

"Commit R1's running config to the network-configs repo"
--> github-ops: create branch, commit config file, open PR with change summary

"Show me R1's config from NSO"
--> nso-device-ops: get_device_config("R1"), formatted configuration output

"Are all devices in sync with NSO?"
--> nso-device-ops: check_device_sync for each device, sync_from_device for any out-of-sync

"What services are deployed on NSO?"
--> nso-service-mgmt: get_service_types, get_services for each type, inventory report

"What platform is PE1 running?"
--> nso-device-ops: get_device_platform("PE1") — model, serial, OS version, hardware

"Build me a 4-router BGP lab with 2 ASes"
--> cml-lab-lifecycle + cml-topology-builder + cml-node-operations: create lab, add 4 IOSv nodes, wire topology, apply BGP configs, start lab

"Capture BGP traffic between R1 and R2 and analyze it"
--> cml-packet-capture: start capture with filter "tcp port 179", download pcap, Packet Buddy analysis

"Show me all running CML labs"
--> cml-lab-lifecycle: get_labs, list running labs with node counts and resource usage

"Export the OSPF lab topology and commit it to GitHub"
--> cml-lab-lifecycle: export_lab as YAML + github-ops: commit to repo

"What's the CML server capacity?"
--> cml-admin: get_system_info (CPU, RAM, disk), get_licensing (node count), resource planning report

"What firewall rules exist for 10.1.1.0/24?"
--> fmc-firewall-ops: list_fmc_profiles, search_access_rules with network indicator, formatted rule table

"Can 10.1.1.50 reach 10.2.1.100 on port 443 through the firewall?"
--> fmc-firewall-ops: find_rules_for_target (FTD device), find_rules_by_ip_or_fqdn (source + dest), port/action analysis

"Audit SGT policies across all FMCs"
--> fmc-firewall-ops: list_fmc_profiles, search_access_rules with SGT identity indicator per FMC, consistency report

"Show me all our Meraki devices"
--> meraki-network-ops: getOrganizations, getOrganizationInventory, device status summary

"How's the WiFi at the branch office?"
--> meraki-wireless-ops: getWirelessSSIDs, getWirelessConnectionStats, getWirelessChannelUtilization, signal quality report

"What's connected to port 12 on the lobby switch?"
--> meraki-switch-ops: getDeviceSwitchPorts (port 12 config), getDeviceSwitchPortStatuses (live state), getDeviceClients

"Show me the firewall rules on the HQ MX appliance"
--> meraki-security-appliance: getNetworkSecurityFirewallRules, rule analysis for overly permissive entries

"Is the VPN tunnel to the warehouse up?"
--> meraki-security-appliance: getNetworkVpnStatus, getNetworkSecurityVpnSiteToSite, tunnel state analysis

"Run a cable test on ports 1-4 of switch MS-Floor2"
--> meraki-monitoring: createDeviceLiveToolsCableTest, getDeviceLiveToolsCableTestResults (OK/open/short/length)

"Who changed the SSID config last week?"
--> meraki-monitoring: getOrganizationConfigurationChanges filtered by time/network, admin identity and change details

"What IPs are assigned in the 10.1.0.0/16 prefix in Nautobot?"
--> nautobot-sot: get_ip_addresses(prefix="10.1.0.0/16"), utilization summary with status and role breakdown

"Show me all deprecated IPs in the production VRF from Nautobot"
--> nautobot-sot: get_ip_addresses(status="deprecated", vrf="PROD-VRF"), stale allocation report

"Search Nautobot for anything related to core-rtr-01"
--> nautobot-sot: search_ip_addresses(query="core-rtr-01"), matching IPs with device assignment details

"What schema kinds are available in Infrahub?"
--> infrahub-sot: get_schema_mapping, list all available kinds with descriptions and relationships

"Show me all devices in Infrahub"
--> infrahub-sot: get_nodes(kind="InfraDevice"), device inventory with platform, role, site, and status

"Create a branch for VLAN changes"
--> infrahub-sot: branch_create("vlan-update"), query_graphql on branch to stage changes, branch_diff to review, GAIT audit

"Check the health of our Itential platform"
--> itential-automation: get_health, status of adapters, applications, system components, GAIT audit

"Run a compliance check on all core routers"
--> itential-automation: get_compliance_plans, run_compliance_plan targeting core routers, describe_compliance_report with pass/fail details, GAIT audit

"Deploy the golden config to the new branch switch"
--> itential-automation: get_golden_config_trees, render_template for target device, backup_device_configuration, apply_device_configuration, get_device_configuration to verify, GAIT audit

"What devices are available on the RADKit service?"
--> radkit-remote-access: get_device_inventory_names, get_device_attributes for each, inventory report

"Run show commands on the remote branch router via RADKit"
--> radkit-remote-access: exec_cli_commands_in_device("branch-rtr-01", ["show ip route", "show ip ospf neighbor"], timeout=60)

"Check uptime on all RADKit devices via SNMP"
--> radkit-remote-access: get_device_inventory_names, snmp_get(sysUpTime OID) per device, uptime summary table

"Why is traffic to example.com slow from London?"
--> te-network-monitoring: te_list_tests (find test), te_get_test_results (check latency)
--> te-path-analysis: te_get_path_vis (hop-by-hop), Get BGP Route Details (AS path check)

"Are there any network outages right now?"
--> te-path-analysis: Search Outages (official), List Events, Get Event Details, scope and timeline report

"Show me the path visualization for test 12345"
--> te-path-analysis: te_get_path_vis (community) for hop-by-hop data, Get Full Path Visualization (official) for all agents

"What BGP routes does ThousandEyes see for our prefix?"
--> te-path-analysis: Get BGP Test Results, Get BGP Route Details — AS paths, reachability from 300+ global monitors

"Run an instant test to 8.8.8.8 from our enterprise agents"
--> te-path-analysis: Instant Tests (official) — on-demand test from selected agents (consumes test units)

"Our VPN users in NYC are complaining about latency"
--> te-path-analysis: List Endpoint Agents, Get Endpoint Agent Metrics (WiFi, DNS, VPN), path visualization to gateway

"Show me all our AWS VPCs"
--> aws-network-ops: list_vpcs, get_vpc_network_details for each, formatted architecture summary

"Why can't my EC2 instance reach the database?"
--> aws-network-ops: find_ip_address (both IPs), get_eni_details, get_vpc_flow_logs (REJECT filter), route table analysis

"Check the Transit Gateway health"
--> aws-network-ops: list_transit_gateways, get_tgw_details, get_all_tgw_routes, detect_tgw_inspection + aws-cloud-monitoring: TGW metrics

"Are any CloudWatch alarms firing?"
--> aws-cloud-monitoring: list alarms in ALARM state, get metrics for affected resources, correlate with flow logs

"How much is our AWS network costing?"
--> aws-cost-ops: network service breakdown (NAT GW, TGW, VPN, ELB), monthly trend, forecast, optimization recommendations

"Audit our AWS IAM security"
--> aws-security-audit: users without MFA, stale access keys, overly permissive policies, CloudTrail suspicious events

"Draw our AWS network architecture"
--> aws-architecture-diagram: auto-discover VPCs/TGWs/subnets, generate PNG topology diagram

"List all our GCP VMs"
--> gcp-compute-ops: search_projects, list_instances per project, formatted inventory with status and IPs

"Are any GCP alerts firing?"
--> gcp-cloud-monitoring: list_alerts for active violations, get_alert_policy for details, list_timeseries for affected metrics

"Show me the GCP firewall logs for denied traffic"
--> gcp-cloud-logging: list_log_entries filtered for firewall DENIED, source/dest IP analysis

"Who deleted VMs in GCP this week?"
--> gcp-cloud-logging: list_log_entries for cloudaudit activity logs, filter compute.instances.delete

"Run a health check on all Juniper routers"
--> junos-network: get_router_list, execute_junos_command_batch (show chassis alarms, show bgp summary), analyze alarms/BGP state, GAIT audit

"Check the health of our Arista fabric"
--> arista-cvp: get_inventory (all devices), get_events (recent alerts), get_connectivity_monitor (probe status), analyze and correlate events with connectivity, GAIT audit

"Generate a network topology diagram"
--> uml-diagram: generate_uml(type="nwdiag") with network zones, IP addressing, device placement

"Document the BGP state machine"
--> uml-diagram: generate_uml(type="state") with BGP FSM states and transitions

"Show me the BGP peers and OSPF neighbors"
--> protocol-participation: protocol_summary — consolidated BGP peer state, RIB size, OSPF neighbors, GRE tunnel status

"Inject route 192.168.50.0/24 with local-pref 200"
--> servicenow-change-workflow (CR) + protocol-participation: bgp_get_rib (pre-check), bgp_inject_route(network, local_pref=200), bgp_get_rib (verify), GAIT audit

"Withdraw the blackhole route for 10.99.0.0/16"
--> servicenow-change-workflow (CR) + protocol-participation: bgp_get_rib(prefix) (verify exists), bgp_withdraw_route(network), bgp_get_rib(prefix) (verify removed), GAIT audit

"Deploy a 2-node SR Linux lab in ContainerLab"
--> clab-lab-management: listLabs (check conflicts), deployLab (topology JSON), inspectLab (verify, get management IPs), execCommand ("show version")

"What ContainerLab labs are running?"
--> clab-lab-management: listLabs, inspectLab per lab for node status and management IPs

"Show me all SD-WAN fabric devices"
--> sdwan-ops: get_devices — vManage, vSmart, vBond, vEdge status summary

"Are there any SD-WAN alarms?"
--> sdwan-ops: get_alarms — active alarms with severity, device, and description

"Check BFD tunnel health on WAN edge 10.10.10.100"
--> sdwan-ops: get_bfd_sessions(device_ip="10.10.10.100"), tunnel status and latency report

"What OMP routes is the branch edge advertising?"
--> sdwan-ops: get_omp_routes(device_ip="10.10.10.200"), received and advertised route summary

"Show me the network dashboards in Grafana"
--> grafana-observability: search_dashboards(title="network"), get_dashboard_summary per result, panel list with datasource info

"What interface traffic is Prometheus seeing on core-rtr-01?"
--> grafana-observability: query_prometheus(expr="rate(ifHCInOctets{device='core-rtr-01'}[5m]) * 8"), query_prometheus(expr="rate(ifHCOutOctets{device='core-rtr-01'}[5m]) * 8"), utilization summary in bps

"Are any Grafana alerts firing right now?"
--> grafana-observability: list_alert_rules — firing/pending rules with severity, affected metric, threshold, and contact point summary

"Search Loki logs for BGP flaps on the spine switches"
--> grafana-observability: query_loki_logs(query='{host=~"spine.*"} |~ "BGP|Established|Idle"', limit=100), pattern analysis and timeline

"Who is on call for network incidents?"
--> grafana-observability: get_current_oncall_users, list_oncall_schedules — current responders and rotation details

"What metrics does Prometheus have for the core routers?"
--> prometheus-monitoring: health_check, list_metrics(page=1), get_metric_metadata — available metrics with type and description

"Show me the interface traffic trend on core-rtr-01 for the last hour"
--> prometheus-monitoring: execute_range_query(query="rate(ifHCInOctets{device='core-rtr-01'}[5m])*8", start, end, step="60s") — bps trend with peak and average

"Are all SNMP scrape targets up in Prometheus?"
--> prometheus-monitoring: get_targets — scrape target status (up/down), last scrape time, labels, error messages

"Capture traffic to the api-gateway pod and show me the top talkers"
--> kubeshark-traffic: capture_traffic(filter="dst.pod.name == 'api-gateway'"), get_l4_flow_summary — top talkers, protocol breakdown, traffic volume

"Export a pcap of all HTTP 500 errors in the production namespace"
--> kubeshark-traffic: apply_filter(kfl_expression="dst.namespace == 'production' and response.status >= 500"), export_pcap — pcap for Wireshark analysis

"Show me all TCP flows with high latency in the cluster"
--> kubeshark-traffic: list_l4_flows, apply_filter(kfl_expression="response.latency > 500ms") — slow connections with RTT and byte stats

"Check Docker container health across all Linux hosts"
--> pyats-linux-system: pyats_list_devices (identify Linux hosts), pyats_run_linux_command("docker stats --no-stream") per host, analyze CPU/memory per container, GAIT audit

"Check OSPF and BGP health on all Juniper routers"
--> pyats-junos-routing: show ospf neighbor, show bgp summary per device, flag non-Full/non-Established, GAIT audit

"How many AnyConnect sessions are active on the ASA?"
--> pyats-asa-firewall: show vpn-sessiondb anyconnect, show vpn-sessiondb summary, show ip local pool, GAIT audit
```

See `examples/` for detailed workflow walkthroughs.

---

## Missions

| Mission | Status | Summary |
|---|---|---|
| MISSION01 | Complete | Core pyATS agent, 7 skills, Markmap, Draw.io, RFC, NVD CVE, SOUL v1 |
| MISSION02 | Complete | Full platform — 37 MCP servers, 82 skills (18 pyATS, 9 domain, 3 F5, 3 CatC, 3 M365, 1 GitHub, 1 packet analysis, 5 CML, 1 ContainerLab, 2 NSO, 1 Itential, 1 FMC, 1 SD-WAN, 1 Grafana, 1 Prometheus, 1 Kubeshark, 1 RADKit, 5 Meraki, 2 ThousandEyes, 5 AWS, 3 GCP, 1 JunOS, 1 Arista CVP, 1 UML, 1 protocol participation, 6 utility, 4 Slack), 6 workspace files, SOUL v2 |
