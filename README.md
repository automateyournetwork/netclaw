<p align="center">
  <img src="netclaw.jpg" alt="NetClaw — A CCIE-level AI agent that claws through your network" width="600">
</p>

# NetClaw

A CCIE-level AI network engineering coworker. Built on [OpenClaw](https://github.com/openclaw/openclaw) with Anthropic Claude, 42 skills, and 19 MCP server backends for complete network automation with ITSM gating, source-of-truth reconciliation, immutable audit trails, packet capture analysis, GitHub config-as-code, Cisco CML lab simulation, Slack-native operations, and Microsoft 365 integration.

---

## Quick Install

```bash
git clone https://github.com/automateyournetwork/netclaw.git
cd netclaw
./scripts/install.sh          # installs everything, then launches the setup wizard
```

That's it. The installer clones 19 MCP servers, deploys 42 skills, then launches a two-phase setup:

**Phase 1: `openclaw onboard`** (OpenClaw's built-in wizard)
- Pick your AI provider (Anthropic, OpenAI, Bedrock, Vertex, 30+ options)
- Set up the gateway (local mode, auth, port)
- Connect channels (Slack, Discord, Telegram, WhatsApp, etc.)
- Install the daemon service

**Phase 2: `./scripts/setup.sh`** (NetClaw platform credentials)
- Network devices (testbed.yaml editor)
- Platform credentials (NetBox, ServiceNow, ACI, ISE, F5, Catalyst Center, NVD, Microsoft Graph, GitHub, CML)
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
- **Reconcile** NetBox source of truth against live device state — flag IP drift, undocumented links, missing interfaces
- **Manage** ACI fabric — health audits, policy analysis, safe tenant/VRF/BD/EPG changes with fault delta rollback
- **Investigate** endpoints via ISE — auth history, posture, profiling, human-authorized quarantine
- **Scan** for CVE vulnerabilities against the NVD database with CVSS severity correlation and exposure confirmation
- **Manage** F5 BIG-IP load balancers — virtual servers, pools, iRules, stats, and change management
- **Operate** Catalyst Center — device inventory, client monitoring, site management, and troubleshooting
- **Calculate** IPv4 and IPv6 subnets — VLSM planning, wildcard masks, allocation standards
- **Alert** via Slack — severity-formatted notifications, incident workflows, and user-aware routing
- **Diagram** your network with Draw.io topology maps (color-coded by reconciliation status)
- **Visualize** protocol hierarchies as interactive Markmap mind maps
- **Reference** IETF RFCs and Wikipedia for standards-compliant configuration
- **Store** reports, config backups, and diagrams on SharePoint via Microsoft Graph
- **Generate** Visio topology diagrams from CDP/LLDP discovery and upload to SharePoint
- **Notify** via Microsoft Teams — health alerts, change updates, and report delivery to Teams channels
- **Analyze** packet captures — upload a pcap to Slack and NetClaw runs deep tshark analysis: protocol hierarchy, conversations, endpoints, DNS/HTTP extraction, expert info, and filtered inspection
- **Track** network changes in GitHub — create issues from findings, commit config backups, open PRs for changes, link to ServiceNow CRs
- **Simulate** network topologies in Cisco CML — create labs, add nodes, wire links, start/stop labs, execute CLI commands, capture packets on lab links, and manage CML users — all from natural language via Slack
- **Audit** every action in an immutable Git-based trail (GAIT) — there is always an answer to "what did the AI do and why"

---

## Architecture

```
Human (Slack / WebChat) --> NetClaw (CCIE Agent on OpenClaw)
                                |
                                |-- DEVICE AUTOMATION:
                                |     MCP: pyATS           --> IOS-XE / NX-OS / IOS-XR devices
                                |     MCP: F5 BIG-IP       --> iControl REST (virtuals, pools, iRules)
                                |     MCP: Catalyst Center --> DNA-C API (devices, clients, sites)
                                |
                                |-- INFRASTRUCTURE:
                                |     MCP: Cisco ACI       --> APIC / ACI fabric
                                |     MCP: Cisco ISE       --> Identity, posture, TrustSec
                                |     MCP: NetBox          --> DCIM/IPAM source of truth (read-write)
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
                                |-- LAB & SIMULATION:
                                |     MCP: Cisco CML         --> Lab lifecycle, topology, nodes, captures
                                |
                                |-- UTILITIES:
                                |     MCP: Subnet Calc     --> IPv4 + IPv6 CIDR calculator
                                |     MCP: GAIT            --> Git-based AI audit trail
                                |     MCP: Wikipedia       --> Technology context
                                |     MCP: Markmap         --> Mind map visualizations
                                |     MCP: Draw.io         --> Network topology diagrams
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

## MCP Servers (19)

| # | MCP Server | Repository | Transport | Function |
|---|------------|------------|-----------|----------|
| 1 | pyATS | [automateyournetwork/pyATS_MCP](https://github.com/automateyournetwork/pyATS_MCP) | stdio (Python) | Device CLI, Genie parsers, config push, dynamic test execution |
| 2 | F5 BIG-IP | [czirakim/F5.MCP.server](https://github.com/czirakim/F5.MCP.server) | stdio (Python) | iControl REST API — virtuals, pools, iRules, profiles, stats |
| 3 | Catalyst Center | [richbibby/catalyst-center-mcp](https://github.com/richbibby/catalyst-center-mcp) | stdio (Python) | DNA-C API — devices, clients, sites, interfaces |
| 4 | Cisco ACI | [automateyournetwork/ACI_MCP](https://github.com/automateyournetwork/ACI_MCP) | stdio (Python) | APIC interaction, policy management, fabric health |
| 5 | Cisco ISE | [automateyournetwork/ISE_MCP](https://github.com/automateyournetwork/ISE_MCP) | stdio (Python) | Identity policy, posture, TrustSec, endpoint control |
| 6 | NetBox | [netboxlabs/netbox-mcp-server](https://github.com/netboxlabs/netbox-mcp-server) | stdio (Python) | Read-write DCIM/IPAM source of truth |
| 7 | ServiceNow | [echelon-ai-labs/servicenow-mcp](https://github.com/echelon-ai-labs/servicenow-mcp) | stdio (Python) | Incidents, change requests, CMDB |
| 8 | Microsoft Graph | [@anthropic-ai/microsoft-graph-mcp](https://www.npmjs.com/package/@anthropic-ai/microsoft-graph-mcp) | npx | OneDrive, SharePoint, Visio, Teams, Exchange via Graph API |
| 9 | GitHub | [github/github-mcp-server](https://github.com/github/github-mcp-server) | Docker (Go) | Issues, PRs, code search, Actions, config-as-code workflows |
| 10 | Packet Buddy | Built-in | stdio (Python) | pcap/pcapng deep analysis via tshark — upload pcaps to Slack |
| 11 | Cisco CML | [xorrkaz/cml-mcp](https://github.com/xorrkaz/cml-mcp) | stdio (Python) | Lab lifecycle, topology, nodes, links, captures, CLI exec, admin |
| 12 | NVD CVE | [marcoeg/mcp-nvd](https://github.com/marcoeg/mcp-nvd) | stdio (Python) | NIST NVD vulnerability database with CVSS scoring |
| 13 | Subnet Calculator | [automateyournetwork/GeminiCLI_SubnetCalculator_Extension](https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension) | stdio (Python) | IPv4 + IPv6 CIDR subnet calculator |
| 14 | GAIT | [automateyournetwork/gait_mcp](https://github.com/automateyournetwork/gait_mcp) | stdio (Python) | Git-based AI tracking and audit |
| 15 | Wikipedia | [automateyournetwork/Wikipedia_MCP](https://github.com/automateyournetwork/Wikipedia_MCP) | stdio (Python) | Standards and technology context |
| 16 | Markmap | [automateyournetwork/markmap_mcp](https://github.com/automateyournetwork/markmap_mcp) | stdio (Node) | Hierarchical mind map generation |
| 17 | Draw.io | [@drawio/mcp](https://github.com/jgraph/drawio-mcp) | npx | Network topology diagram generation |
| 18 | RFC Lookup | [@mjpitz/mcp-rfc](https://github.com/mjpitz/mcp-rfc) | npx | IETF RFC search and retrieval |

All MCP servers communicate via stdio (JSON-RPC 2.0) through `scripts/mcp-call.py`. GitHub MCP runs via Docker. CML MCP is pip-installed (`cml-mcp`). No persistent connections, no port management.

---

## Skills (42)

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

### Domain Skills (7)

| Skill | What It Does |
|-------|-------------|
| **netbox-reconcile** | Diffs NetBox intent vs device reality. Detects 7 discrepancy types: IP_DRIFT, MISSING_INTERFACE, UNDOCUMENTED_LINK, CABLE_MISMATCH, VLAN_MISMATCH, STATUS_MISMATCH, MTU_MISMATCH. Opens ServiceNow incidents for CRITICAL findings. Generates Markmap drift summary. GAIT audit. |
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

### Reference & Utility Skills (6)

| Skill | Tool Backend | Purpose |
|-------|-------------|---------|
| **nvd-cve** | [marcoeg/mcp-nvd](https://github.com/marcoeg/mcp-nvd) (Python) | NVD vulnerability database — search by keyword, get CVE details with CVSS v3.1/v2.0 scores, exposure correlation |
| **subnet-calculator** | [SubnetCalculator MCP](https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension) | IPv4 + IPv6 subnet calculator — VLSM planning, wildcard masks, address classification, RFC 6164 /127 links |
| **wikipedia-research** | [Wikipedia_MCP](https://github.com/automateyournetwork/Wikipedia_MCP) | Protocol history, standards evolution, technology context. 6 tools: search, summary, content, references, categories, exists check. |
| **markmap-viz** | [markmap-mcp](https://github.com/automateyournetwork/markmap_mcp) (Node) | Interactive mind maps from markdown — OSPF area hierarchies, BGP peer trees, drift summaries |
| **drawio-diagram** | [@drawio/mcp](https://github.com/jgraph/drawio-mcp) (npx) | Network topology diagrams — Mermaid, XML, or CSV format. Color-coded by reconciliation status. |
| **rfc-lookup** | [@mjpitz/mcp-rfc](https://github.com/mjpitz/mcp-rfc) (npx) | IETF RFC search, retrieval, and section extraction — BGP (4271), OSPF (2328), NTP (5905) |

### Slack Integration Skills (4)

| Skill | Purpose |
|-------|---------|
| **slack-network-alerts** | Severity-formatted alert delivery (CRITICAL/HIGH/WARNING/INFO), reaction-based acknowledgment, fleet summary posts |
| **slack-report-delivery** | Rich Slack formatting for health checks, security audits, topology maps, reconciliation results, change reports |
| **slack-incident-workflow** | Full incident lifecycle in Slack: declaration, triage, automated investigation, status updates, resolution, post-incident review |
| **slack-user-context** | User-aware interactions: DND-respecting escalation, timezone-aware scheduling, role-based response depth, shift handoff summaries |

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

### Source of Truth Reconciliation
```
netbox-reconcile
--> NetBox intent pull (devices, interfaces, IPs, VLANs, cables)
--> pyATS actual state collection (pCall across fleet)
--> Diff engine: IP_DRIFT / MISSING / UNDOCUMENTED / CABLE_MISMATCH
--> ServiceNow incident per CRITICAL discrepancy
--> Markmap drift summary
--> GAIT commit
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
├── MISSION02.md                          # Completed — full platform, 42 skills, 19 MCP
├── workspace/
│   └── skills/                           # 42 skill definitions (source of truth)
│       ├── pyats-network/                # Core device automation (8 MCP tools)
│       ├── pyats-health-check/           # Health + NetBox cross-ref + pCall
│       ├── pyats-routing/                # OSPF, BGP, EIGRP, IS-IS analysis
│       ├── pyats-security/               # Security + ISE + NVD CVE + pCall
│       ├── pyats-topology/               # Discovery + NetBox reconciliation + pCall
│       ├── pyats-config-mgmt/            # Change control + ServiceNow + GAIT
│       ├── pyats-troubleshoot/           # Troubleshooting + pCall + NetBox + GAIT
│       ├── pyats-dynamic-test/           # pyATS aetest script generation
│       ├── pyats-parallel-ops/           # Fleet-wide pCall operations
│       ├── netbox-reconcile/             # Source of truth drift detection
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
│       ├── rfc-lookup/                   # IETF RFC search
│       ├── github-ops/                  # GitHub issues, PRs, config-as-code
│       ├── packet-analysis/             # pcap analysis via tshark + Slack upload
│       ├── cml-lab-lifecycle/          # CML lab create, start, stop, delete, clone
│       ├── cml-topology-builder/       # CML nodes, interfaces, links, annotations
│       ├── cml-node-operations/        # CML node start/stop, configs, CLI exec
│       ├── cml-packet-capture/         # CML link packet capture + Packet Buddy
│       ├── cml-admin/                  # CML users, groups, system, licensing
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
│   └── packet-buddy-mcp/                 # pcap analysis via tshark (built-in)
├── scripts/
│   ├── install.sh                        # Full bootstrap installer (24 steps)
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
7. **Clones GAIT MCP** — `git clone` + `pip3 install gait-ai fastmcp`
8. **Clones NetBox MCP** — `git clone` + `pip3 install` dependencies
9. **Clones ServiceNow MCP** — `git clone` + `pip3 install` dependencies
10. **Clones ACI MCP** — `git clone` + `pip3 install` dependencies
11. **Clones ISE MCP** — `git clone` + `pip3 install` dependencies
12. **Clones Wikipedia MCP** — `git clone` + `pip3 install` dependencies
13. **Clones NVD CVE MCP** — `git clone` + `pip3 install -e .`
14. **Clones Subnet Calculator MCP** — `git clone` (enhanced with IPv6 support)
15. **Clones F5 BIG-IP MCP** — `git clone` + `pip3 install` dependencies
16. **Clones Catalyst Center MCP** — `git clone` + `pip3 install` dependencies
17. **Caches Microsoft Graph MCP** — `npm cache add` for Graph API (OneDrive, SharePoint, Visio, Teams)
18. **Caches npx packages** — `npm cache add` for Draw.io and RFC servers
19. **Pulls GitHub MCP** — `docker pull ghcr.io/github/github-mcp-server` (requires Docker)
20. **Installs Packet Buddy MCP** — verifies/installs tshark, creates pcap upload directory
21. **Installs CML MCP** — `pip3 install cml-mcp` (requires Python 3.12+, CML 2.9+)
22. **Deploys skills + workspace files** — Copies 42 skills and 6 MD files to `~/.openclaw/workspace/`
23. **Verifies installation** — Checks all MCP server scripts + core scripts exist
24. **Prints summary** — Lists all 19 MCP servers by category and all 42 skills by domain

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
- NetBox instance with API token
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
- Microsoft 365 tenant with Azure AD app registration (for Graph/Visio/Teams skills)
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
```

See `examples/` for detailed workflow walkthroughs.

---

## Missions

| Mission | Status | Summary |
|---|---|---|
| MISSION01 | Complete | Core pyATS agent, 7 skills, Markmap, Draw.io, RFC, NVD CVE, SOUL v1 |
| MISSION02 | Complete | Full platform — 19 MCP servers, 42 skills (9 pyATS, 7 domain, 3 F5, 3 CatC, 3 M365, 1 GitHub, 1 packet analysis, 5 CML, 6 utility, 4 Slack), 6 workspace files, SOUL v2 |
