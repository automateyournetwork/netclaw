# NetClaw Skill Procedures Reference

> Load this file when you need detailed operational procedures for any skill.
> This is a reference document - core workflows are in SOUL.md.
> Use: `read("~/.openclaw/workspace/SOUL-SKILLS.md")`

---

## Device Automation Skills

### pyats-network
Core device automation: show commands, configure, ping, logging, dynamic tests. Use `pyats_run_command` for single commands, `pyats_run_command_batch` for multiple. Genie parsers return structured JSON for 100+ IOS-XE commands.

### pyats-health-check
8-step health assessment:
1. Device reachability (ping)
2. Interface status vs NetBox expected state
3. CPU/memory utilization
4. Error counters (CRC, input errors, output drops)
5. Routing protocol adjacencies
6. Hardware inventory (fans, power supplies)
7. Software version vs NVD CVE scan
8. Severity scoring (CRITICAL/HIGH/MEDIUM/LOW)

Use pCall for fleet-wide health checks. Cross-reference NetBox for expected interface states.

### pyats-routing
OSPF, BGP, EIGRP, IS-IS deep analysis with full path selection. Parse routing tables, neighbor states, advertised/received prefixes. Use `pyats_get_routing_table`, `pyats_get_ospf_neighbors`, `pyats_get_bgp_summary`.

### pyats-security
9-step CIS audit:
1. Management plane hardening (SSH, VTY ACLs)
2. Control plane policing
3. AAA configuration
4. SNMP security (v3, ACLs)
5. Routing protocol authentication
6. First-hop security (DHCP snooping, DAI)
7. uRPF
8. Logging configuration
9. NVD CVE vulnerability scan

Verify ISE NAD registration. Correlate CVE exposure with running config.

### pyats-topology
CDP/LLDP/ARP discovery with NetBox cable reconciliation. Use `pyats_get_cdp_neighbors`, `pyats_get_lldp_neighbors`. Diff discovered neighbors against NetBox cable records. Flag undocumented links.

### pyats-config-mgmt
5-phase change workflow:
1. **Pre-change baseline** — capture running config
2. **Validation** — parse and verify syntax
3. **Apply** — push config via pyATS
4. **Post-change verification** — confirm changes applied
5. **Rollback** — revert if verification fails

Requires ServiceNow CR in `Implement` state. Record all phases in GAIT.

### pyats-troubleshoot
OSI-layer diagnosis methodology:
1. **Layer 1** — interface status, errors, CRC, collisions
2. **Layer 2** — MAC table, VLAN, STP state, ARP
3. **Layer 3** — IP config, routing table, next-hop reachability
4. **Layer 4** — ACLs, NAT, port connectivity
5. **Application** — DNS, protocol-specific checks

Use pCall for multi-hop parallel collection. Cross-reference NetBox for expected state.

### pyats-dynamic-test
Generate and execute deterministic pyATS aetest scripts from natural language requirements. Define testcases, setup/cleanup, pass/fail criteria. Execute and report results.

### pyats-parallel-ops
Fleet-wide parallel operations:
- **pCall grouping** — execute same command across multiple devices simultaneously
- **Failure isolation** — continue on failure, collect all results
- **Severity sorting** — triage results by severity level

Use for fleet health checks, config audits, and mass data collection.

---

## pyATS Linux Host Skills

### pyats-linux-system
Linux host system operations via `pyats_run_linux_command`:
- `ps -ef` — process listings
- `ps -ef | grep {pattern}` — targeted process search
- `docker stats --no-stream` — container resource usage
- `ls -l` — filesystem inspection
- `curl -V` — tool verification

All commands are read-only. No kill, rm, shutdown operations.

### pyats-linux-network
Linux host network operations via `pyats_run_linux_command`:
- `ifconfig` / `ifconfig {interface}` — interface state (IPs, MACs, errors, MTU)
- `ip route show table all` — full multi-table routing
- `route` / `route -n` — legacy routing
- `netstat -rn` — routing via netstat format

Cross-reference Linux host IPs against NetBox/Nautobot IPAM.

### pyats-linux-vmware
VMware ESXi host operations via `pyats_run_linux_command`:
- `vim-cmd vmsvc/getallvms` — VM inventory (ID, name, datastore, guest OS, hardware version)
- `vim-cmd vmsvc/snapshot.get {vmid}` — snapshot tree inspection

Flag stale snapshots (>72h) and deep chains (>3 levels). Compare VM inventory against NetBox virtualization records.

---

## pyATS JunOS Skills

### pyats-junos-system
JunOS chassis and system operations:
- `show chassis alarms` — **CHECK FIRST** on any JunOS health check
- `show chassis environment` — temp, fans, power
- `show chassis hardware` — serial numbers, inventory
- `show version` — firmware versions
- `show system uptime` / `show system storage` / `show system buffers`
- `show ntp associations` / `show snmp statistics`
- `show log messages` / `show system core-dumps`
- `show ddos-protection statistics`

System audit pattern: version → uptime → commit history → storage → core-dumps → NTP → NVD CVE scan.

### pyats-junos-interfaces
JunOS interface operations:
- `show interfaces terse` / `show interfaces descriptions` / `show interfaces statistics`
- `show interfaces {interface} extensive` — deep-dive
- `show interfaces diagnostics optics` — SFP diagnostics (rx power < -20 dBm = WARNING)
- `show lacp interfaces` / `show lacp statistics`
- `show lldp neighbors` / `show arp no-resolve`
- `show ipv6 neighbors`
- `show bfd session`

### pyats-junos-routing
JunOS routing protocol operations:
- **OSPF**: `show ospf neighbor`, `show ospf interface`, `show ospf database`, `show ospf overview`, `show ospf statistics`
- **OSPFv3**: Full IPv6 parity
- **BGP**: `show bgp summary`, `show bgp neighbor {peer}`, `show bgp group`
- **Route table**: `show route`, `show route protocol {proto}`, `show route advertising-protocol`, `show route receiving-protocol`
- **MPLS**: `show mpls lsp`, `show ldp overview`, `show ldp neighbor`, `show rsvp session`
- **Verification**: `ping {dest} count {n}`, `traceroute {dest} no-resolve`

Validation: OSPF neighbor state must be Full, BGP peer state must be Established.

---

## pyATS ASA Skills

### pyats-asa-firewall
Cisco ASA firewall operations:
- **Check failover first**: `show failover` is the first command on any ASA HA pair
- **VPN monitoring**: `show vpn-sessiondb summary` for capacity, `show vpn-sessiondb anyconnect sort inactivity` for idle sessions, `show ip local pool` for address exhaustion
- **ASP drops**: `show asp drop` reveals why traffic is blocked (flow-drop, acl-drop, inspect-drop, rpf-violated)
- **Multi-context**: `show context detail` for per-context resources, `show resource usage` for limits
- **Interface status**: `show interface ip brief`, `show interface detail`
- **Routing**: `show route`, `show arp`

Cross-reference ASA version with NVD CVE — ASA vulnerabilities are high-impact.

---

## pyATS F5 BIG-IP Skills

### pyats-f5-ltm
F5 BIG-IP LTM/GTM operations via iControl REST:
- **Virtual servers**: status, destination, profiles
- **Pools**: members, monitors, load balancing method
- **Nodes**: address, state, availability
- **Monitors**: 40+ types (HTTP/S, TCP, UDP, DNS, database, external)
- **Profiles**: 60+ types (SSL client/server, HTTP, TCP, FastL4, compression, caching)
- **Persistence**: cookie, source-addr, SSL, universal
- **iRules**: rule profiler
- **LTM policies**, data groups (internal/external)
- **GTM**: wide IPs (A/AAAA/CNAME/MX/NAPTR/SRV), pools, datacenters, servers, 30+ monitors

### pyats-f5-platform
F5 BIG-IP platform operations via iControl REST:
- **System**: version, hardware, CPU, memory, disk, performance stats, NTP, DNS, syslog, SNMP, certificates, licensing, provisioning
- **Networking**: interfaces, VLANs, self IPs, trunks, routes, route domains, BGP/BFD, tunnels (GRE/VXLAN/IPsec/Geneve), ARP, NDP, STP, packet filters
- **Cluster management**: devices, device-groups, sync-status, failover-status, traffic-groups, trust-domain
- **Authentication**: LDAP, RADIUS, TACACS+, users, roles, password policy, partitions
- **Analytics**: CPU, memory, HTTP, TCP, DNS, DoS, ASM/WAF, bot defense, SSL orchestrator
- **Security**: AFM firewall policies, management IP rules

**Check sync-status first**: `/mgmt/tm/cm/sync-status` — "Changes Pending" or "Disconnected" means stop and investigate.

Platform health pattern: version → hardware → CPU → memory → disk → NTP → license → provision → performance stats.

---

## F5 BIG-IP Skills

### f5-health-check
Virtual server stats, pool member health, log analysis:
1. Virtual server availability (up/down/unknown)
2. Pool member health (available/unavailable/disabled)
3. Connection counts and rates
4. Monitor status per member
5. Log analysis for errors
6. Severity assessment

### f5-config-mgmt
Safe F5 object lifecycle with ServiceNow CR gating and GAIT audit. Pre-change snapshot, apply changes, post-change verification, rollback on failure.

### f5-troubleshoot
Virtual server, pool, persistence, iRule, SSL, and performance troubleshooting:
1. Check virtual server status and statistics
2. Verify pool member health
3. Test persistence behavior
4. Analyze iRule execution
5. Verify SSL certificate chain
6. Review performance metrics

---

## Domain Skills

### netbox-reconcile
Diff NetBox intent vs device reality:
1. Query NetBox for expected state (IPs, interfaces, cables)
2. Query devices for actual state
3. Compare and generate drift report
4. Flag IP drift, missing interfaces, cable mismatches
5. Open ServiceNow incidents for CRITICAL discrepancies

### nautobot-sot
Nautobot IPAM source of truth:
- `test_connection` — verify Nautobot API reachability before starting
- IP address queries with status/role/VRF/tenant filtering
- Prefix lookups by site
- Full-text IP search
- Filter by VRF when overlapping address space is in use

Alternative to NetBox for orgs running Nautobot.

### infrahub-sot
Infrahub SoT operations:
- `get_schema_mapping` — discover node types, attributes, relationships first
- `get_node_filters` — learn supported filter syntax before queries
- Branch for changes — never mutate directly on main branch
- `get_related_nodes` — traverse relationships instead of multiple queries

### aci-fabric-audit
ACI fabric health, policy audit, fault analysis:
1. Fabric health score
2. Tenant/VRF/BD/EPG/Contract inventory
3. Fault analysis by severity
4. Endpoint learning verification
5. Policy compliance checks

### aci-change-deploy
Safe ACI policy changes with ServiceNow gating and fault delta rollback:
1. Pre-change fault snapshot
2. Apply policy changes
3. Post-change fault delta
4. Rollback if new faults detected

### ise-posture-audit
Authorization policy review, posture compliance, TrustSec SGT analysis:
1. Authorization policy audit
2. Posture assessment compliance
3. Profiling coverage
4. TrustSec SGT matrix analysis

### ise-incident-response
Endpoint investigation and human-authorized quarantine:
1. Endpoint lookup by MAC/IP
2. Authentication history
3. Authorization context
4. **NEVER auto-quarantine** — requires explicit human confirmation

### servicenow-change-workflow
Full ITSM lifecycle:
1. Check for open P1/P2 incidents on affected CIs
2. Create CR with description, risk, impact, rollback plan
3. Wait for approval (CR must be in `Implement` state)
4. Execute changes
5. Close CR on success; escalate on failure

### gait-session-tracking
Mandatory Git-based audit trail:
1. `gait_branch` — create session branch
2. `gait_record_turn` — record each action
3. `gait_log` — display full audit trail at session end

---

## Catalyst Center Skills

### catc-inventory
Device inventory, site hierarchy, interface details via Catalyst Center API.

### catc-client-ops
Client monitoring:
- Wired/wireless client discovery
- SSID/band/site filtering
- MAC lookup
- Count trending and analytics

### catc-troubleshoot
Device unreachable, client connectivity, interface down, site-wide triage. Use pyATS follow-up for CLI-level investigation.

---

## Microsoft 365 Skills

### msgraph-files
OneDrive/SharePoint file operations:
- Upload audit reports, configuration backups, documentation
- Download files for processing
- Search across SharePoint
- Organize network documentation and artifacts

### msgraph-visio
Visio diagram generation:
1. Collect CDP/LLDP discovery data
2. Generate Visio topology diagram
3. Upload to SharePoint
4. Create sharing link for team

### msgraph-teams
Teams channel notifications:
- Health alerts
- Security alerts
- Change updates
- Report delivery
- Diagram sharing

Follow same severity-based channel mapping as Slack.

---

## GitHub Skills

### github-ops
Config-as-code operations:
- Create issues from findings
- Commit config backups
- Open PRs with ServiceNow CR references
- Search code
- Trigger Actions workflows

---

## Packet Analysis Skills

### packet-analysis
Deep pcap/pcapng analysis via tshark:
- Protocol hierarchy
- Conversations
- Endpoints
- DNS analysis
- HTTP analysis
- Expert info
- Filtered inspection

---

## nmap Network Scanning Skills

### nmap-network-scan
Host discovery (ICMP/ARP) and port scanning (SYN/TCP/UDP):
- CIDR scope enforcement
- Audit logging
- 6 tools for different scan types

### nmap-service-detection
Service/version fingerprinting, OS detection, NSE script execution:
- Vulnerability scanning
- Full recon sweeps
- 5 tools

### nmap-scan-management
Custom nmap scans with arbitrary flags (scope-enforced):
- Scan history listing
- Result retrieval by ID
- Before/after comparison workflows
- 3 tools

---

## gtrace Path Analysis Skills

### gtrace-path-analysis
Advanced traceroute with MPLS/ECMP/NAT detection:
- `traceroute` — full path analysis first
- `mtr` — continuous monitoring for intermittent issues
- `globalping` — distributed probes from 500+ worldwide locations

Run traceroute first, then MTR for persistent issues, GlobalPing for perspective.

### gtrace-ip-enrichment
IP address enrichment:
- `asn_lookup` — organization, network range, RIR
- `geo_lookup` — city/region/country/coordinates
- `reverse_dns` — hostname resolution

Enrich traceroute hops to identify network owners and locations.

---

## Cisco CML Skills

### cml-lab-lifecycle
Create, start, stop, wipe, delete, clone, import/export CML labs from natural language.

### cml-topology-builder
Add nodes, create interfaces, wire links, set link conditioning, control link states.

### cml-node-operations
Start/stop nodes, set startup configs, execute CLI commands, retrieve console logs.

### cml-packet-capture
Capture packets on CML links with BPF filters, hand off to Packet Buddy for analysis.

### cml-admin
CML server administration: users, groups, system info, licensing, resource monitoring.

---

## ContainerLab Skills

### clab-lab-management
ContainerLab network lab lifecycle management:
- `listLabs` — list labs before deploying to avoid name conflicts
- Deploy new topologies (SR Linux, cEOS, FRR, IOS-XR, NX-OS, etc.)
- `inspectLab` with `details: true` after deployment
- `destroyLab` with `graceful: true` and `cleanup: true`

Lab-only operations — no ServiceNow CR gating required. Docker dependency.

---

## Cisco SD-WAN Skills

### sdwan-ops
Read-only vManage operations (12 tools):
- `get_devices` — fabric device inventory
- `get_wan_edge_inventory` — serial numbers, chassis IDs
- `get_device_templates`, `get_feature_templates` — template audit
- `get_centralized_policies` — policy definitions
- `get_alarms` — active alarms
- `get_omp_routes` — OMP routing (received/advertised)
- `get_bfd_sessions` — BFD session status
- `get_control_connections` — DTLS/TLS control connections

Check fabric health first. Cross-reference with pyATS for CLI state.

---

## Observability Skills

### grafana-observability
Grafana platform (75+ tools):
- Dashboard search/summary/property extraction/modification
- Prometheus PromQL queries (instant/range, metric discovery)
- Loki LogQL queries (log search, label discovery)
- Alerting rules (list/create/update/delete, contact points)
- Incident management (list/create/update, activity timeline)
- OnCall schedules (rotations, current on-call)
- Annotations, panel image rendering, deep link generation

Start with dashboard search. Use `get_dashboard_summary` over full JSON. Dashboard modifications require ServiceNow CR.

### prometheus-monitoring
Direct Prometheus access (6 tools):
- `health_check` — verify connectivity first
- `list_metrics` with pagination — discover available metrics
- `get_metric_metadata` — type, help text, unit
- `execute_query` — instant PromQL queries
- `execute_range_query` — time-series trends
- `get_targets` — scrape target health

Complementary to Grafana — direct PromQL access without dashboard overhead.

### kubeshark-traffic
Kubernetes L4/L7 traffic analysis (6 tools):
- `capture_traffic` with KFL filters — scope to specific pods/namespaces
- `list_l4_flows` — TCP/UDP connection details, RTT
- `get_l4_flow_summary` — top-talkers, protocol distribution
- `apply_filter` with KFL — filter by pod, status, latency, protocol
- `export_pcap` — export for tshark analysis
- `create_snapshot` — point-in-time capture for forensics

TLS decryption is automatic via eBPF. Sensitive data awareness — handle exports securely.

---

## Cisco NSO Skills

### nso-device-ops
NSO device operations: config from CDB, operational state, sync status, platform info, NED IDs, device groups.

### nso-service-mgmt
NSO service management: service types, deployed instances, health checks, impact analysis.

---

## Itential IAP Skills

### itential-automation
Itential Automation Platform (65+ tools):
- `get_health` — verify IAP status before running automations
- `backup_device_configuration` — always backup before config pushes
- `apply_device_configuration` — gate with ServiceNow CR
- `get_compliance_plans`, `run_compliance_plan` — pre- and post-change compliance
- `get_golden_config_trees`, `render_template` — golden config workflows
- `get_workflows`, `start_workflow`, `describe_job` — workflow orchestration
- `run_command_template` — bulk command execution
- `get_resources`, `describe_resource`, `run_action` — lifecycle management

Names are case-sensitive. Record all operations in GAIT.

---

## Juniper JunOS Skills

### junos-network
Juniper device automation via PyEZ/NETCONF (10 tools):
- `get_router_list` — verify target device exists first
- `get_junos_config` — baseline before changes
- `execute_junos_command`, `execute_junos_command_batch` — CLI execution
- `render_and_apply_j2_template` with `dry_run=true` — preview templates
- `load_and_commit_config` — gate with ServiceNow CR, include commit_comment

Respect blocklists (block.cmd, block.cfg) — no reboot, halt, zeroize.

---

## Arista CloudVision Skills

### arista-cvp
CloudVision Portal automation (4 tools):
- `get_inventory` — verify CVP connectivity and device streaming first
- `get_events` — check alerts before changes
- `get_connectivity_monitor` — jitter, latency, packet loss
- `create_tag` — gate with ServiceNow CR (modifies CVP state)

Cross-reference with NetBox/Nautobot. Scan EOS versions against NVD CVE. Community project (unofficial).

---

## Protocol Participation Skills

### protocol-participation
Live BGP and OSPF control-plane participation (10 tools):
- **Read operations (always safe)**: `bgp_get_peers`, `bgp_get_rib`, `ospf_get_neighbors`, `ospf_get_lsdb`, `gre_tunnel_status`, `protocol_summary`
- **Route mutations (require ServiceNow CR)**: `bgp_inject_route`, `bgp_withdraw_route`, `bgp_adjust_local_pref`, `ospf_adjust_cost`

Verify RIB before injecting. Only advertise to Established peers. Use `protocol_summary` for health checks. Lab mode (`NETCLAW_LAB_MODE=true`) relaxes CR requirement.

---

## Cisco FMC Skills

### fmc-firewall-ops
Cisco Secure Firewall policy search via FMC (4 read-only tools):
- `list_fmc_profiles` — discover FMC instances first
- `find_rules_by_ip_or_fqdn` — search within specific access policy
- `find_rules_for_target` — resolve FTD devices to assigned policies
- `search_access_rules` — FMC-wide search with network/identity indicators

---

## Firewall Rule Analysis Skills

### fwrule-analyzer
Multi-vendor firewall rule overlap, shadowing, conflict, and duplication analysis (3 tools):
- 9 vendors: PAN-OS, ASA, FTD, IOS/IOS-XE, IOS-XR, Check Point, SRX, Junos, Nokia SR OS
- 6-dimensional set intersection
- No credentials required — pure offline analysis engine

---

## Ansible Automation Platform Skills

### aap-automation
Red Hat Ansible Automation Platform (45 tools):
- Inventory management
- Job template execution and monitoring
- Project SCM sync
- Ad-hoc commands
- Host/group management
- Galaxy content discovery

### aap-eda
Event-Driven Ansible (12 tools):
- Activation lifecycle (enable/disable/restart)
- Rulebook management
- Decision environments
- Event stream monitoring

### aap-lint
ansible-lint validation (9 tools):
- Playbook/role linting with configurable profiles
- Syntax checking
- Best practice enforcement
- Project-wide analysis

---

## Enterprise Platform Skills

### infoblox-ddi
Infoblox DNS, DHCP, and IPAM operations: zones/records, lease/scope review, utilization checks, address conflict validation.

### paloalto-panorama
Panorama-managed firewall policy search: device groups, templates, NAT/security rules, object review, commit validation workflows.

### fortimanager-ops
FortiManager policy governance: ADOM inventory, package/rule review, revision history, install preview workflows.

---

## Cisco RADKit Skills

### radkit-remote-access
Cloud-relayed remote device access:
- `get_device_inventory_names` — discover available devices first
- `get_device_attributes` — inspect device type, platform, capabilities
- `exec_cli_commands_in_device` — CLI commands with timeout and max_lines
- `snmp_get` — lightweight metric polling

Set reasonable timeouts and line limits. RADKit is read-write capable if onboarded user has write access — gate config changes with ServiceNow CRs.

---

## Data Center Fabric Skills

### evpn-vxlan-fabric
Vendor-neutral EVPN/VXLAN fabric audit and troubleshooting:
- VTEP reachability
- VNI mapping
- EVPN route types
- Multihoming/ESI state
- Underlay/overlay correlation

---

## Cisco Meraki Skills

### meraki-network-ops
Meraki Dashboard operations (~804 API endpoints via dynamic MCP):
- Organization inventory
- Network management
- Device lifecycle
- Client discovery
- Uplink status
- Action batches for bulk operations

Built-in caching reduces API calls by 50-90%. `READ_ONLY_MODE=true` blocks all writes.

### meraki-wireless-ops
Meraki wireless management:
- SSID configuration
- RF profiles
- Channel utilization analysis
- Signal quality monitoring
- Client connectivity event investigation

### meraki-switch-ops
Meraki switch operations:
- Port configuration
- VLANs
- Port statuses
- ACLs, QoS rules
- Port cycling
- BPDU guard verification

### meraki-security-appliance
Meraki MX security appliance:
- L3/L7 firewall rules
- Site-to-site Auto VPN
- Content filtering
- Traffic shaping
- IDS/IPS security events

### meraki-monitoring
Meraki live diagnostics:
- Ping from device
- Cable test
- LED blink
- Wake-on-LAN
- Camera analytics
- Configuration change audit trail

All write operations require ServiceNow CRs.

---

## ThousandEyes Skills

### te-network-monitoring
ThousandEyes network monitoring:
- Community MCP server (9 tools, stdio): tests, agents, dashboards, results, alerts, events
- Official MCP server (~20 tools, remote HTTP): advanced analysis, instant tests, AI-powered views

### te-path-analysis
ThousandEyes deep path analysis:
- Hop-by-hop path visualization (latency, loss, MPLS labels, ISP identification)
- BGP route analysis (AS path validation, prefix reachability, route hijack detection)
- Outage investigation (scope, timeline, affected services)
- Instant tests (use judiciously — consumes test units)
- Endpoint VPN diagnostics (WiFi signal, DNS, VPN latency)

Both servers share `TE_TOKEN` environment variable.

---

## AWS Cloud Skills

### aws-network-ops
AWS cloud networking (27 read-only tools):
- VPCs, Transit Gateways, Cloud WAN
- VPN, Network Firewalls
- Flow logs

### aws-cloud-monitoring
CloudWatch metrics, alarms, Logs Insights queries, VPC/TGW flow log analysis.

### aws-security-audit
IAM users/roles/policies (read-only), CloudTrail API events, compliance checks.

### aws-cost-ops
Cost Explorer: spending by service, trends, forecasts, network cost optimization.

### aws-architecture-diagram
Generate visual architecture diagrams from live AWS infrastructure (graphviz).

---

## GCP Cloud Skills

### gcp-compute-ops
GCP Compute Engine (28 tools) + Resource Manager: VMs, disks, templates, instance groups, projects.

### gcp-cloud-monitoring
Cloud Monitoring (6 tools): time series metrics, alert policies, active alerts.

### gcp-cloud-logging
Cloud Logging (6 tools): log search, VPC flow logs, firewall logs, audit logs.

---

## Reference & Utility Skills

### nvd-cve
NVD vulnerability database: search by keyword, CVE details with CVSS v3.1/v2.0 scores.

### subnet-calculator
IPv4 + IPv6 CIDR calculator: VLSM, wildcard masks, RFC 6164 /127 links.

### wikipedia-research
Protocol history, standards evolution, technology context.

### markmap-viz
Interactive mind maps from markdown. Use for hierarchical data (OSPF areas, BGP peers, drift summaries).

### drawio-diagram
Network topology diagrams: native .drawio files with CLI export (PNG/SVG/PDF with embedded XML), plus browser-based Mermaid/XML/CSV via MCP server. Use for topology from CDP/LLDP discovery, color-coded by reconciliation status.

### uml-diagram
UML and diagram generation via Kroki (27+ types):
- `nwdiag` — network topology (IP addressing, VLANs, zones)
- `rackdiag` — data center rack layouts
- `packetdiag` — protocol header documentation
- `sequence` — change request flows, protocol exchanges
- `state` — protocol state machines (BGP FSM, OSPF states)
- `c4plantuml` / `structurizr` — architecture documentation
- `mermaid` / `d2` / `graphviz` — flowcharts, dependency graphs

Use `generate_diagram_url` for inline URLs, `generate_uml` with `output_dir` to save files. Security note: public Kroki server is default — use `KROKI_SERVER` env var for sensitive data.

### rfc-lookup
IETF RFC search, retrieval, section extraction.

---

## Slack Integration Skills

### slack-network-alerts
Severity-formatted alert delivery with reaction-based acknowledgment.

### slack-report-delivery
Rich Slack formatting for reports: health, security, topology, reconciliation.

### slack-incident-workflow
Full incident lifecycle: declaration, triage, investigation, resolution, PIR.

### slack-user-context
DND-respecting escalation, timezone-aware scheduling, role-based response depth.

---

## Cisco WebEx Integration Skills

### webex-network-alerts
Severity-formatted alert delivery to WebEx spaces:
- Adaptive Cards (severity-styled containers, FactSets, ColumnSets)
- Markdown formatting
- File attachments

### webex-report-delivery
Rich WebEx formatting for reports using Adaptive Cards for structured data and markdown for narrative content.

### webex-incident-workflow
Full incident lifecycle in WebEx:
- Interactive Adaptive Card buttons for IC claim
- Dedicated incident spaces via Rooms API
- Threaded investigation via `parentId`

### webex-user-context
Availability-aware escalation via People API, role-based response depth.

**WebEx formatting guidelines:**
- Adaptive Cards v1.3: `attention` for CRITICAL, `good` for RESOLVED
- Always include fallback text in markdown field
- Use `parentId` for threading
- File attachments via multipart/form-data (up to 100 MB)
- Mentions use `<@personId>` syntax

---

## Voice Interface Skills

### slack-voice-interface
Voice responses for Slack:
1. Process voice transcript (transcription handled by OpenClaw)
2. Generate text response using full skill set
3. Call `text_to_speech` to generate MP3
4. Upload MP3 to thread alongside text response

Default voice: en-US-GuyNeural. Keep voice responses under 100 words. Fallback to text-only if TTS fails.

### webex-voice-interface
Voice responses for WebEx: same workflow as Slack — transcribe, process, generate MP3 via edge-tts, upload to WebEx space as file attachment.

---

## Heartbeat Check-Ins

When performing periodic heartbeat health checks, send check-in messages to all configured channels:
- **Slack** — post to configured heartbeat channel
- **WebEx** — if `WEBEX_BOT_TOKEN` and `WEBEX_ALERTS_ROOM_ID` set, post to WebEx alerts space using Adaptive Cards for problem summaries
- **Teams** — if Microsoft Graph configured, post to designated Teams channel

Keep healthy check-ins to one sentence. Use rich formatting only for problem summaries.

---

## Cloudflare Skills

### cloudflare-dns
DNS and domain management via Cloudflare DNS Analytics MCP:
- `list_zones` — enumerate all zones in account
- `get_zone_details` — zone configuration, status, plan
- `list_dns_records` — A/AAAA/CNAME/MX/TXT records with filters
- `get_dns_analytics` — query volume, latency, error rates
- `get_dnssec_status` — DNSSEC configuration and key status

Query DNS analytics first for traffic patterns. Cross-reference with NetBox DNS records.

### cloudflare-zerotrust
Zero Trust network access via Cloudflare:
- `list_access_applications` — protected applications inventory
- `list_access_policies` — policy rules and conditions
- `get_gateway_logs` — DNS/HTTP gateway activity
- `list_tunnel_connections` — Cloudflare Tunnel status
- `get_device_posture` — endpoint compliance checks

Zero Trust audit: applications → policies → gateway logs → posture compliance.

### cloudflare-analytics
Traffic and performance analytics:
- `get_zone_analytics` — requests, bandwidth, threats blocked
- `get_firewall_events` — WAF triggers, rate limiting, bot detection
- `get_origin_analytics` — origin server response times
- `get_cache_analytics` — cache hit ratio, bandwidth saved

Start with zone analytics for overview, drill into firewall events for security.

### cloudflare-workers
Edge compute and serverless via Workers:
- `list_workers` — deployed Worker scripts
- `get_worker_logs` — Worker execution logs and errors
- `list_kv_namespaces` — KV storage namespaces
- `get_durable_objects` — stateful edge compute

Workers are read-only by default. Deployment requires ServiceNow CR.

### cloudflare-security
WAF, DDoS, and security posture:
- `list_firewall_rules` — custom firewall rules
- `get_waf_packages` — managed WAF rulesets
- `get_rate_limits` — rate limiting configuration
- `get_ddos_analytics` — DDoS attack mitigation stats
- `list_ip_access_rules` — IP allow/block lists

Security audit: WAF packages → firewall rules → rate limits → DDoS analytics.

---

## Zscaler Skills

### zscaler-zia
Zscaler Internet Access (ZIA) security:
- `list_url_categories` — URL filtering categories
- `get_security_policies` — web security policies
- `list_firewall_rules` — cloud firewall rules
- `get_ssl_inspection` — SSL inspection config
- `list_dlp_engines` — DLP engines and patterns

ZIA audit: security policies → firewall rules → SSL inspection → DLP.

### zscaler-zpa
Zscaler Private Access (ZPA) zero trust:
- `list_application_segments` — protected applications
- `list_server_groups` — app connector groups
- `list_access_policies` — access policies
- `list_posture_profiles` — device posture checks
- `list_connectors` — ZPA connector status

ZPA audit: connectors → server groups → application segments → access policies.

### zscaler-zdx
Zscaler Digital Experience (ZDX) monitoring:
- `list_devices` — enrolled endpoint devices
- `get_user_experience` — user experience scores
- `list_applications` — monitored applications
- `get_network_metrics` — network path analytics
- `list_alerts` — ZDX alerts and issues

ZDX troubleshooting: device health → network metrics → application performance.

### zscaler-identity
Zscaler identity and user management:
- `list_users` — user directory
- `list_groups` — user groups
- `list_departments` — department hierarchy
- `get_idp_config` — identity provider settings

Identity audit: IDP config → departments → groups → users.

### zscaler-insights
Zscaler analytics and reporting:
- `get_traffic_insights` — traffic analytics
- `get_threat_insights` — threat detection stats
- `get_bandwidth_report` — bandwidth utilization
- `list_audit_logs` — admin audit trail

Security review: threat insights → traffic analytics → audit logs.

---

## HashiCorp Vault Skills

### vault-secrets
Secrets engine management:
- `list_secrets` — enumerate secrets in a path
- `read_secret` — retrieve secret data
- `list_secret_engines` — available secrets engines
- `get_secret_metadata` — version history, deletion status

Secrets audit: list engines → list secrets → read metadata → verify policies.

### vault-pki
PKI certificates management:
- `list_certificates` — issued certificates
- `get_certificate` — certificate details
- `get_ca_chain` — CA certificate chain
- `list_roles` — PKI roles for cert issuance

Certificate audit: CA chain → roles → issued certificates → expiration.

### vault-mounts
Secrets engine and auth method mounts:
- `list_auth_methods` — authentication methods
- `list_secret_engines` — secrets engines
- `get_mount_config` — mount configuration
- `get_audit_devices` — audit logging devices

Vault health: auth methods → secret engines → audit devices.

---

## HashiCorp Terraform Skills

### terraform-registry
Terraform Registry module and provider discovery:
- `search_modules` — find public modules
- `get_module_versions` — version history
- `search_providers` — find providers
- `get_provider_docs` — provider documentation

Use registry search before writing modules from scratch.

### terraform-workspaces
Terraform Cloud workspace management:
- `list_workspaces` — organization workspaces
- `get_workspace_runs` — run history
- `get_workspace_state` — current state file
- `list_variables` — workspace variables

Workspace review: variables → recent runs → current state.

### terraform-operations
Terraform Cloud run operations:
- `create_run` — trigger plan/apply (requires ServiceNow CR)
- `get_run_status` — run status and logs
- `get_plan_output` — plan details
- `cancel_run` — cancel pending run

All write operations gate through ServiceNow CR workflow.

---

## Splunk Skills

### splunk-search
Splunk search and query:
- `run_search` — execute SPL queries
- `get_search_results` — retrieve search results
- `list_search_jobs` — active/completed searches
- `get_search_status` — job status

Search workflow: list indexes → run search → get results → export.

### splunk-indexes
Splunk index management:
- `list_indexes` — available indexes
- `get_index_details` — index configuration
- `get_index_stats` — event count, size
- `list_sourcetypes` — data sourcetypes

Index discovery before querying for efficient searches.

### splunk-saved
Splunk saved searches and alerts:
- `list_saved_searches` — saved search definitions
- `get_saved_search` — search details
- `run_saved_search` — execute saved search
- `list_alerts` — alert history

Compliance reporting: list saved searches → run on schedule → verify results.

---

## Datadog Skills

### datadog-logs
Log search and analysis:
- `search_logs` — query logs with filters
- `get_log_details` — specific log entry
- `list_log_indexes` — available indexes
- `get_pipeline_config` — log pipeline configuration

Log investigation: search by service/host → filter by time → get details.

### datadog-metrics
Metric queries and dashboards:
- `execute_query` — PromQL-style metric queries
- `list_metrics` — available metrics
- `get_metric_metadata` — metric type and unit
- `list_dashboards` — dashboard inventory
- `get_dashboard` — dashboard definition

Metric analysis: list metrics → execute query → visualize in dashboard.

### datadog-incidents
Incident management:
- `list_incidents` — active/resolved incidents
- `get_incident` — incident details
- `create_incident` — create incident (requires write)
- `update_incident` — update status (requires write)

Read-only by default. Write operations require explicit enable.

### datadog-apm
Application performance monitoring:
- `list_services` — APM service inventory
- `get_service_summary` — service health
- `list_traces` — distributed traces
- `get_trace` — trace details

APM workflow: service inventory → health check → trace analysis.

---

## PagerDuty Skills

### pagerduty-incidents
Incident management:
- `list_incidents` — active/resolved incidents
- `get_incident` — incident details
- `manage_incidents` — acknowledge/resolve
- `add_note_to_incident` — timeline updates
- `add_responders` — escalate to additional responders
- `get_related_incidents` — find related issues

Incident workflow: list triggered → get details → acknowledge → add notes → resolve.

### pagerduty-oncall
On-call schedule management:
- `list_oncalls` — current on-call
- `list_schedules` — schedule inventory
- `get_schedule` — schedule details
- `list_escalation_policies` — escalation chains
- `create_schedule_override` — temporary coverage

On-call check: list oncalls → verify escalation policy → create override if needed.

### pagerduty-services
Service catalog:
- `list_services` — service inventory
- `get_service` — service configuration
- `create_service` — new service (requires write)
- `update_service` — modify service (requires write)

Service review: list services → check escalation policy assignments.

### pagerduty-orchestration
Event orchestration:
- `list_event_orchestrations` — orchestration rules
- `get_event_orchestration` — rule details
- `get_event_orchestration_router` — routing rules
- `update_event_orchestration_router` — modify routing (requires write)

Event routing audit: list orchestrations → review router rules → verify destinations.

---

## Prisma SD-WAN Skills

### prisma-sdwan-topology
Prisma SD-WAN fabric topology:
- `list_sites` — site inventory
- `get_site` — site details and configuration
- `list_elements` — ION device inventory
- `get_element` — device details
- `list_interfaces` — interface inventory

Topology discovery: sites → elements → interfaces → WAN links.

### prisma-sdwan-status
Prisma SD-WAN health and status:
- `get_element_status` — device health
- `list_alarms` — active alarms
- `get_app_status` — application health
- `list_vpn_links` — VPN tunnel status
- `get_path_status` — path analytics

Health check: element status → alarms → VPN links → path status.

### prisma-sdwan-config
Prisma SD-WAN configuration:
- `list_policy_sets` — policy definitions
- `get_policy` — policy details
- `list_path_policies` — path selection rules
- `list_qos_policies` — QoS configuration

Config audit: policy sets → path policies → QoS policies.

### prisma-sdwan-apps
Prisma SD-WAN application visibility:
- `list_app_definitions` — application signatures
- `get_app_stats` — application usage
- `list_app_policies` — per-app policies

Application visibility: app definitions → usage stats → policy mapping.

---

## GNS3 Skills

### gns3-project-lifecycle
GNS3 project management:
- `list_projects` — lab inventory
- `create_project` — new lab project
- `open_project` — open existing project
- `close_project` — close project
- `delete_project` — remove project

Lab-only operations — no ServiceNow CR required.

### gns3-node-operations
GNS3 node management:
- `list_nodes` — nodes in project
- `create_node` — add node to topology
- `start_node` — power on node
- `stop_node` — power off node
- `get_node_console` — console access

Node lifecycle: create → configure → start → test → stop.

### gns3-link-management
GNS3 link and connectivity:
- `list_links` — links in project
- `create_link` — connect nodes
- `delete_link` — remove connection
- `get_link_filters` — link conditioning

Link management for topology building.

### gns3-packet-capture
GNS3 packet capture:
- `start_capture` — begin capture on link
- `stop_capture` — end capture
- `get_capture_file` — download pcap
- `list_captures` — active captures

Hand off pcap files to Packet Buddy for analysis.

### gns3-snapshot-ops
GNS3 snapshot management:
- `list_snapshots` — snapshot inventory
- `create_snapshot` — save lab state
- `restore_snapshot` — rollback to snapshot
- `delete_snapshot` — remove snapshot

Always snapshot before major topology changes.
