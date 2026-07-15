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

## Memory Skills

### memory-facts
Record and recall network facts with temporal validity:
- `memory_record_fact(entity, key, value, metadata)` — store fact about entity (auto-supersedes existing)
- `memory_get_facts(entity, key)` — retrieve current facts for entity
- `memory_invalidate(fact_id, reason)` — explicitly invalidate outdated fact
- `memory_timeline(entity, after, before, key)` — view historical facts including invalidated

Facts are normalized (lowercase entities) and timestamped. Superseded facts remain in timeline for audit.

### memory-semantic
Semantic search across past sessions:
- `memory_store_session(summary, entities, topics)` — store session summary with embeddings
- `memory_recall(query, top_k, min_score)` — natural language search for similar sessions

Uses ChromaDB + all-MiniLM-L6-v2 (384 dimensions). Graceful degradation if embeddings unavailable.

### memory-decisions
Decision log with full context for audit:
- `memory_record_decision(context, decision, rationale, entities, cr_number)` — log operational decision
- `memory_get_decisions(entity, after, before)` — query decisions by entity or time range

Include ServiceNow CR number (CHG format) when available. Links to GAIT for full audit trail.

### memory-graph
Entity relationship tracking:
- `memory_link_entities(subject, predicate, object)` — create relationship between entities
- `memory_query_graph(entity, direction, predicate, depth)` — traverse relationships

Standard predicates: `peers_with`, `depends_on`, `connects_to`, `managed_by`, `caused`, `fixed_by`, `learned_from`.

**Use memory to:**
1. Remember device states across sessions
2. Recall similar troubleshooting sessions
3. Audit why decisions were made
4. Track topology relationships

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
- `get_schema` — discover node types, attributes, relationships, and filters first
- `get_nodes` / `search_nodes` — typed/filtered/paged reads and fuzzy substring search
- `query_graphql` — read-only custom queries
- Branch-isolated writes — `node_upsert` / `node_delete` / `mutate_graphql` land on an auto-created `mcp/session-*` branch, never the default
- `propose_changes` — open a Proposed Change for human review (agent never merges)

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

## Claroty OT Security Skills

### claroty-asset-inventory
OT / IoT / IoMT asset discovery and Purdue Model classification via Claroty xDome (4 tools, 2 ITSM-gated):
- `list_devices(site_id?, purdue_level?, device_purpose?, name_contains?)` — paginated device inventory
- `get_device_details` — full record for one device
- `set_device_purdue_level(device_id, purdue_level, cr_number)` — assign Purdue layer (ITSM-gated)
- `set_device_custom_attribute(device_id, key, value, cr_number)` — set metadata (ITSM-gated)
- Cross-reference with `nautobot-sot` or `netbox-reconcile` to surface SoT drift.

### claroty-risk-triage
Unified alert + vulnerability triage in OT environments (8 tools, 4 ITSM-gated):
- `list_alerts(severity?, status?, site_id?, assignee?)` and `get_alert_with_devices(alert_id)` for blast radius
- `list_vulnerabilities(severity?, cvss_min?, cve_contains?)` and `get_vulnerable_devices(vulnerability_id)`
- `acknowledge_alert(alert_id, resolution, cr_number)` — set resolution state (ITSM-gated)
- `set_vulnerability_relevance(device_id, vuln_id, relevant, cr_number)` — suppress CVE on a device (ITSM-gated)
- `label_alerts(alert_ids, labels, cr_number)` and `assign_alerts(alert_ids, assignee, cr_number)` (ITSM-gated)
- Correlate with `nvd-cve` MCP for CVSS vector decomposition; hand off to `ise-incident-response` for endpoint quarantine.

### claroty-ot-topology
OT communication map and segmentation visualisation (3 read-only tools):
- `get_device_communication_map(device_id? | site_id?)` — device-to-device edges
- `list_organization_zones()` — segmentation zones with device counts
- `list_ot_activity_events(device_id?, start?, end?)` — activity timeline
- Hand off to `canvas-network-viz` for inline Canvas/A2UI render or `drawio-` for exportable diagrams.

---

## Check Point Security Skills

### checkpoint-security
Check Point enterprise security platform (15 MCP servers, 60+ tools):

**Policy Management (chkp-management + chkp-policy-insights):**
- `show-access-rulebase`, `show-nat-rulebase` — audit firewall rules
- `show-hosts`, `show-networks`, `show-groups` — object inventory
- `get-policy-insights`, `suggest-optimizations` — AI-powered policy analysis

**Threat Intelligence (chkp-reputation-service):**
- `query-ip-reputation` — check IP reputation (malicious, suspicious, benign)
- `query-url-reputation` — URL threat classification
- `query-file-reputation` — file hash reputation lookup

**Gateway Diagnostics (chkp-quantum-gw-cli + chkp-gw-connection-analysis):**
- `fw-stat`, `cphaprob-stat` — firewall and ClusterXL status
- `show-interface`, `cpview` — interface stats and performance
- `debug-connection`, `analyze-drops` — connection troubleshooting

**Threat Prevention (chkp-threat-prevention):**
- `show-threat-profiles` — threat prevention policy profiles
- `show-ips-protections` — IPS signature inventory
- `show-threat-ioc-feeds` — active IOC feeds

**SASE (chkp-harmony-sase):**
- `list-sase-regions`, `list-sase-networks` — SASE infrastructure
- `list-sase-applications` — application control

**Malware Analysis (chkp-threat-emulation):**
- `submit-file` — submit file for sandbox analysis
- `query-report`, `get-verdict` — retrieve analysis results

**Additional MCPs:**
- `chkp-https-inspection` — SSL/TLS decryption policies
- `chkp-quantum-gaia` — GAIA OS management
- `chkp-documentation` — Check Point docs search
- `chkp-spark-management` — MSP distributed firewalls
- `chkp-cpinfo-analysis` — diagnostic file analysis
- `chkp-argos-erm` — exposure and risk management
- `chkp-management-logs` — connection and audit logs

**Workflow:**
1. Start with `show-access-rulebase` to understand current policy
2. Use `query-ip-reputation` for threat intelligence lookups
3. Use `fw-stat` for gateway health verification
4. Cross-reference with other NetClaw sources (CML labs, SuzieQ state)

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY (or USERNAME/PASSWORD), plus service-specific keys for SASE, TE, Reputation, Spark, Argos.

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

---

## IP Fabric Network Assurance Skills

### ipfabric-assurance
IP Fabric network assurance and path analysis (10 tools):

**Health Assessment:**
- `ipf_network_health_assess` — Comprehensive network health overview (snapshot freshness, intent verification, device issues, routing stability)

**Path Lookups:**
- `ipf_pathlookup_unicast` — Trace unicast path between two IPs
- `ipf_pathlookup_host-to-gateway` — Trace host to default gateway
- `ipf_pathlookup_multicast` — Trace multicast distribution path

**Path Diagrams (PNG):**
- `ipf_png_pathlookup_unicast` — Unicast path as visual diagram
- `ipf_png_pathlookup_host-to-gateway` — Host-to-gateway path diagram
- `ipf_png_pathlookup_multicast` — Multicast path diagram

**API Discovery:**
- `ipf_api_endpoint_search` — Find API endpoints using natural language
- `ipf_api_endpoint_details` — Get endpoint parameters and response schema
- `api_invoke` — Execute arbitrary API calls with parameters

**Workflow:**
1. Start with `ipf_network_health_assess` for overall health
2. Use `ipf_pathlookup_unicast` for connectivity troubleshooting
3. Add `ipf_png_pathlookup_*` for visual diagrams
4. Use API discovery tools for custom queries

**Snapshot Handling:**
- Default to `$last` (most recent completed snapshot)
- Specify by name: "using snapshot 'Pre-Change'"
- Specify by UUID for precise targeting

**VRF-Aware Queries:**
- Add `vrf` parameter for VRF-specific path analysis
- Default queries use global routing table

**Diagram Delivery:**
- CLI: Saved to `~/.openclaw/workspace/diagrams/ipfabric/`
- Slack/Teams/WebEx: Attached as file to message

**Credentials:** `IPFABRIC_HOST`, `IPFABRIC_API_TOKEN`

Developed in collaboration with **Daren Fulwell** (Field CTO, IP Fabric) and **John Capobianco** (Creator, NetClaw).

---

## Additional Skills Index

The skills above are documented with full step-by-step operational procedures. The 181 skills below were added across later feature branches and are not yet expanded into full procedures in this file — each one's complete workflow, commands, and best practices live directly in its own `SKILL.md`, which remains the authoritative reference. This index exists so every skill NetClaw has is at least discoverable from this file; read the linked `SKILL.md` for the actual procedure, don't guess from the one-line summary below.

| Skill | Summary | Full Procedure |
|-------|---------|-----------------|
| `aap-automation` | Red Hat Ansible Automation Platform — inventory management, job template execution, project SCM sync, ad-hoc commands, host management, Galaxy content discov... | `workspace/skills/aap-automation/SKILL.md` |
| `aap-eda` | Event-Driven Ansible (EDA) — activation lifecycle, rulebook management, decision environments, event stream monitoring. Use when managing event-driven automa... | `workspace/skills/aap-eda/SKILL.md` |
| `aap-lint` | ansible-lint playbook and role validation — syntax checking, best practice enforcement, project-wide analysis, rule filtering. Use when validating Ansible pl... | `workspace/skills/aap-lint/SKILL.md` |
| `aci-change-deploy` | Safe ACI policy change deployment - ServiceNow CR lifecycle, pre/post-change fault baselines, APIC policy application, automatic rollback on fault delta, and... | `workspace/skills/aci-change-deploy/SKILL.md` |
| `aci-fabric-audit` | Comprehensive Cisco ACI fabric health audit - node status, tenant/VRF/BD/EPG policy review, contract analysis, fault triage, and endpoint learning verificati... | `workspace/skills/aci-fabric-audit/SKILL.md` |
| `arista-cvp` | Arista CloudVision Portal (CVP) automation via REST API — device inventory, events, connectivity monitoring, tag management (4 tools). Use when managing Aris... | `workspace/skills/arista-cvp/SKILL.md` |
| `aruba-cx-config` | View and manage Aruba CX switch configurations, perform ISSU upgrades, and firmware operations | `workspace/skills/aruba-cx-config/SKILL.md` |
| `aruba-cx-interfaces` | Monitor Aruba CX switch interface status, LLDP neighbors, and optical transceiver health | `workspace/skills/aruba-cx-interfaces/SKILL.md` |
| `aruba-cx-switching` | View and manage Aruba CX switch VLANs and MAC address tables for Layer 2 operations | `workspace/skills/aruba-cx-switching/SKILL.md` |
| `aruba-cx-system` | Discover Aruba CX switch system information, firmware versions, and VSF topology | `workspace/skills/aruba-cx-system/SKILL.md` |
| `atlassian-itsm` | IT Service Management workflows using Jira for issue tracking and Confluence for documentation | `workspace/skills/atlassian-itsm/SKILL.md` |
| `aws-architecture-diagram` | AWS architecture diagrams — generate visual network topology diagrams from live AWS infrastructure. Use when drawing AWS network diagrams, visualizing VPCs, ... | `workspace/skills/aws-architecture-diagram/SKILL.md` |
| `aws-cloud-monitoring` | AWS CloudWatch monitoring — metrics, alarms, log queries, VPC flow log analysis, network performance. Use when checking AWS alarms, analyzing VPC flow logs, ... | `workspace/skills/aws-cloud-monitoring/SKILL.md` |
| `aws-cost-ops` | AWS Cost Explorer — spending analysis, service breakdowns, forecasts, cost anomalies. Use when analyzing AWS spending, investigating cost spikes, reviewing n... | `workspace/skills/aws-cost-ops/SKILL.md` |
| `aws-network-ops` | AWS cloud networking — VPC, Transit Gateway, Cloud WAN, VPN, Network Firewall, ENI, flow logs. Use when auditing AWS VPCs, troubleshooting connectivity betwe... | `workspace/skills/aws-network-ops/SKILL.md` |
| `aws-security-audit` | AWS security auditing — IAM users/roles/policies, CloudTrail API events, security posture analysis. Use when auditing IAM permissions, investigating security... | `workspace/skills/aws-security-audit/SKILL.md` |
| `azure-network-ops` | Azure cloud networking -- VNets, NSGs, ExpressRoute, VPN Gateways, Azure Firewalls, Load Balancers, Application Gateways, Route Tables, Network Watcher, Priv... | `workspace/skills/azure-network-ops/SKILL.md` |
| `azure-security-audit` | Azure NSG compliance auditing and security posture assessment. CIS Azure Foundations Benchmark rules, effective security rule analysis, orphaned NSG detectio... | `workspace/skills/azure-security-audit/SKILL.md` |
| `batfish-config-analysis` | Batfish network configuration analysis -- pre-deployment validation, reachability testing, ACL/firewall tracing, differential analysis, compliance checking. ... | `workspace/skills/batfish-config-analysis/SKILL.md` |
| `blender-3d-viz` | Create 3D network topology visualizations in Blender from CDP/LLDP neighbor data | `workspace/skills/blender-3d-viz/SKILL.md` |
| `catc-client-ops` | Catalyst Center client operations and monitoring - list/filter wired and wireless clients, detailed client lookup by MAC, client count analytics, time-based ... | `workspace/skills/catc-client-ops/SKILL.md` |
| `catc-inventory` | Catalyst Center device inventory and site management - list/filter devices by hostname, IP, platform, family, role, reachability; view site hierarchy; get in... | `workspace/skills/catc-inventory/SKILL.md` |
| `catc-troubleshoot` | Catalyst Center troubleshooting workflows - device unreachable investigation, client connectivity issues, interface down analysis, site-wide outage triage, w... | `workspace/skills/catc-troubleshoot/SKILL.md` |
| `checkpoint` | A comprehensive skill for interacting with Check Point enterprise security infrastructure through 15 MCP servers. | `workspace/skills/checkpoint/SKILL.md` |
| `clab-lab-management` | ContainerLab network lab lifecycle management — authenticate, list, deploy, inspect, execute commands on, and destroy containerized network labs via the Cont... | `workspace/skills/clab-lab-management/SKILL.md` |
| `claroty-asset-inventory` | Discover and classify OT / IoT / IoMT assets via Claroty xDome. List devices by site, Purdue level, and device purpose; assign Purdue layers and custom attri... | `workspace/skills/claroty-asset-inventory/SKILL.md` |
| `claroty-ot-topology` | Render Claroty xDome OT / IoT communication maps and zone segmentation as inline Canvas/A2UI topology, draw.io diagrams, and timeline summaries. | `workspace/skills/claroty-ot-topology/SKILL.md` |
| `claroty-risk-triage` | Triage Claroty xDome alerts and vulnerabilities, compute blast radius, correlate with NVD CVE data, and drive ITSM-gated workflow actions (acknowledge, label... | `workspace/skills/claroty-risk-triage/SKILL.md` |
| `cloudflare-analytics` | Access Cloudflare traffic analytics, logs, and Radar global Internet insights. | `workspace/skills/cloudflare-analytics/SKILL.md` |
| `cloudflare-dns` | Manage Cloudflare DNS zones and records with analytics insights. | `workspace/skills/cloudflare-dns/SKILL.md` |
| `cloudflare-security` | Monitor Cloudflare WAF, firewall events, audit logs, and threat intelligence. | `workspace/skills/cloudflare-security/SKILL.md` |
| `cloudflare-workers` | Monitor Cloudflare Workers deployments, bindings, and build insights. | `workspace/skills/cloudflare-workers/SKILL.md` |
| `cloudflare-zerotrust` | Inspect Cloudflare Zero Trust access applications, policies, tunnels, and CASB findings. | `workspace/skills/cloudflare-zerotrust/SKILL.md` |
| `cml-admin` | CML administration — user/group management, system info, licensing, resource monitoring. Use when creating CML users, checking license status, monitoring CML... | `workspace/skills/cml-admin/SKILL.md` |
| `cml-lab-lifecycle` | Cisco CML lab lifecycle management — create, start, stop, wipe, delete, clone, import/export labs. Use when building a network lab, starting or stopping a CM... | `workspace/skills/cml-lab-lifecycle/SKILL.md` |
| `cml-node-operations` | CML node operations — start, stop, console access, CLI execution, config management, node details. Use when starting or stopping a CML node, running show com... | `workspace/skills/cml-node-operations/SKILL.md` |
| `cml-packet-capture` | CML packet capture — start, stop, download pcaps from CML lab links, integrate with Packet Buddy for analysis. Use when capturing packets in a CML lab, troub... | `workspace/skills/cml-packet-capture/SKILL.md` |
| `cml-topology-builder` | Build CML topologies — add nodes, create interfaces, wire links, set link conditioning, add annotations. Use when building a network topology in CML, adding ... | `workspace/skills/cml-topology-builder/SKILL.md` |
| `datadog-apm` | Analyze distributed traces and service performance in Datadog APM. | `workspace/skills/datadog-apm/SKILL.md` |
| `datadog-incidents` | Manage incidents in Datadog Incident Management. | `workspace/skills/datadog-incidents/SKILL.md` |
| `datadog-logs` | Search and analyze logs in Datadog Log Management. | `workspace/skills/datadog-logs/SKILL.md` |
| `datadog-metrics` | Query metrics and explore dashboards in Datadog. | `workspace/skills/datadog-metrics/SKILL.md` |
| `defenseclaw-ops` | Manage DefenseClaw enterprise security - scan components, manage tool permissions, view alerts, configure guardrails | `workspace/skills/defenseclaw-ops/SKILL.md` |
| `devnet-catalyst-search` | Search Cisco Catalyst Center API documentation for device management and policy automation | `workspace/skills/devnet-catalyst-search/SKILL.md` |
| `devnet-meraki-search` | Search Cisco Meraki API documentation and lookup specific operations | `workspace/skills/devnet-meraki-search/SKILL.md` |
| `drawio-diagram` | Generate draw.io network diagrams — native .drawio files with CLI export (PNG/SVG/PDF), plus browser-based Mermaid/XML/CSV via MCP server. Use when creating ... | `workspace/skills/drawio-diagram/SKILL.md` |
| `eve-lab-topology-build` | Build or rewire EVE-NG lab topology. Use when creating or deleting virtual networks, connecting node interfaces to networks, inspecting topology links, check... | `workspace/skills/eve-lab-topology-build/SKILL.md` |
| `eve-lab-topology-design` | Design EVE-NG lab topology and coordinate the design workflow. Use when the user asks for lab design, architecture advice, topology planning, design review, ... | `workspace/skills/eve-lab-topology-design/SKILL.md` |
| `eve-lab-topology-discovery` | Gather missing requirements for EVE-NG topology design. Use when the request is vague or incomplete, when you need discovery questions, defaults, trade-off f... | `workspace/skills/eve-lab-topology-discovery/SKILL.md` |
| `eve-lab-topology-validation` | Validate EVE-NG topology designs and enforce final delivery structure. Use when reviewing a design, checking build readiness, producing the final design outp... | `workspace/skills/eve-lab-topology-validation/SKILL.md` |
| `eve-ng-config-ops` | Manage EVE-NG startup configurations stored in lab files. Use when exporting configs natively into the lab, reading embedded startup configs, pushing startup... | `workspace/skills/eve-ng-config-ops/SKILL.md` |
| `eve-ng-console-ops` | Execute live CLI commands on running EVE-NG nodes over telnet console. Use when running show commands, making live config changes, verifying protocol state, ... | `workspace/skills/eve-ng-console-ops/SKILL.md` |
| `eve-ng-lab-management` | Manage EVE-NG labs and platform inventory. Use when listing labs, checking lab metadata, creating or deleting labs, importing or exporting lab archives, chec... | `workspace/skills/eve-ng-lab-management/SKILL.md` |
| `eve-ng-node-operations` | Manage EVE-NG node lifecycle. Use when listing nodes, checking runtime state, creating or deleting nodes, starting or stopping nodes or whole labs, verifying... | `workspace/skills/eve-ng-node-operations/SKILL.md` |
| `evpn-vxlan-fabric` | EVPN/VXLAN fabric audit and troubleshooting — VTEPs, VNIs, route types, multihoming, underlay/overlay validation. Use when troubleshooting VXLAN overlay reac... | `workspace/skills/evpn-vxlan-fabric/SKILL.md` |
| `f5-config-mgmt` | F5 BIG-IP configuration management - safe change workflow with baseline capture, planning, creation/update/deletion of virtual servers, pools, iRules, and pr... | `workspace/skills/f5-config-mgmt/SKILL.md` |
| `f5-health-check` | F5 BIG-IP health monitoring - virtual server status, pool member health, log analysis, performance statistics, and systematic health assessment. Use when che... | `workspace/skills/f5-health-check/SKILL.md` |
| `f5-troubleshoot` | F5 BIG-IP troubleshooting - virtual server failures, pool member health, connection issues, SSL/TLS problems, iRule errors, persistence issues, and performan... | `workspace/skills/f5-troubleshoot/SKILL.md` |
| `fmc-firewall-ops` | Cisco Secure Firewall FMC — access policy search, rule inspection, FTD device targeting, multi-FMC profile management. Use when searching firewall rules by I... | `workspace/skills/fmc-firewall-ops/SKILL.md` |
| `fortimanager-ops` | FortiManager operations — ADOM inventory, policy package review, object search, install preview, and compliance workflows. Use when auditing FortiGate firewa... | `workspace/skills/fortimanager-ops/SKILL.md` |
| `forward` | Forward snapshot assurance, path search, app-aware path search, NQE, checks, vulnerabilities, diffs, configuration, lifecycle, collection, and topology workf... | `workspace/skills/forward/SKILL.md` |
| `fwrule-analyzer` | Multi-vendor firewall rule analysis — overlap detection, shadowing, conflict identification, duplication checking across PAN-OS, ASA, FTD, IOS/IOS-XE, IOS-XR... | `workspace/skills/fwrule-analyzer/SKILL.md` |
| `gait-session-tracking` | GAIT session lifecycle management - branch creation, turn recording, audit logging for every NetClaw operation. Use when starting a new NetClaw session, reco... | `workspace/skills/gait-session-tracking/SKILL.md` |
| `gcp-cloud-logging` | Google Cloud Logging — log search, VPC flow logs, firewall logs, audit logs, log buckets and views. Use when searching GCP logs, investigating denied VPC flo... | `workspace/skills/gcp-cloud-logging/SKILL.md` |
| `gcp-cloud-monitoring` | Google Cloud Monitoring — time series metrics, alert policies, active alerts, metric discovery. Use when checking GCP network performance, investigating firi... | `workspace/skills/gcp-cloud-monitoring/SKILL.md` |
| `gcp-compute-ops` | Google Cloud Compute Engine — VM instances, disks, templates, instance groups, reservations, project discovery. Use when listing GCP VMs, troubleshooting a C... | `workspace/skills/gcp-compute-ops/SKILL.md` |
| `github-ops` | GitHub repository operations — issues, PRs, code search, and config-as-code workflows. Use when creating a GitHub issue for a network finding, opening a pull... | `workspace/skills/github-ops/SKILL.md` |
| `gitlab-devops` | GitLab DevOps operations — issues, merge requests, CI/CD pipelines, repository browsing, labels, milestones, releases, and wiki management. Use when querying... | `workspace/skills/gitlab-devops/SKILL.md` |
| `gnmi-telemetry` | gNMI streaming telemetry operations for multi-vendor network devices. Query device state via structured YANG model paths, subscribe to real-time telemetry st... | `workspace/skills/gnmi-telemetry/SKILL.md` |
| `gns3-link-management` | Manage GNS3 links - connect/disconnect node interfaces, isolate nodes | `workspace/skills/gns3-link-management/SKILL.md` |
| `gns3-node-operations` | Manage GNS3 nodes - add from templates, start/stop/suspend/reload, console access | `workspace/skills/gns3-node-operations/SKILL.md` |
| `gns3-packet-capture` | Capture network traffic on GNS3 links - start/stop captures, retrieve PCAP data | `workspace/skills/gns3-packet-capture/SKILL.md` |
| `gns3-project-lifecycle` | Manage GNS3 network lab projects - create, open, close, delete, clone, export/import | `workspace/skills/gns3-project-lifecycle/SKILL.md` |
| `gns3-snapshot-ops` | Manage GNS3 project snapshots - create, restore, delete for safe experimentation | `workspace/skills/gns3-snapshot-ops/SKILL.md` |
| `grafana-observability` | Grafana observability platform — dashboards, Prometheus PromQL, Loki LogQL, alerting, incidents, OnCall schedules, annotations, datasource queries, panel ren... | `workspace/skills/grafana-observability/SKILL.md` |
| `gtrace-ip-enrichment` | IP address enrichment — ASN ownership lookup, geolocation (city/region/country/coordinates), and reverse DNS resolution. Use when identifying who owns an IP ... | `workspace/skills/gtrace-ip-enrichment/SKILL.md` |
| `gtrace-path-analysis` | Network path tracing and monitoring — traceroute with MPLS/ECMP/NAT detection, continuous MTR monitoring, and distributed GlobalPing probes from 500+ worldwi... | `workspace/skills/gtrace-path-analysis/SKILL.md` |
| `humanrail-escalation` | Human-in-the-loop escalation via HumanRail — route low-confidence agent decisions, pre-destructive operation approvals, and ambiguous incident tickets to rea... | `workspace/skills/humanrail-escalation/SKILL.md` |
| `infoblox-ddi` | Infoblox DDI operations — DNS zones/records, DHCP scopes and leases, IPAM networks and address utilization. Use when checking DNS records, validating IPAM ad... | `workspace/skills/infoblox-ddi/SKILL.md` |
| `infrahub-sot` | OpsMill Infrahub — infrastructure source of truth with schema-driven nodes, GraphQL queries, and branch-isolated changes. Use when querying Infrahub for devi... | `workspace/skills/infrahub-sot/SKILL.md` |
| `ipfabric` | > Developed in collaboration with **Daren Fulwell** (Field CTO, IP Fabric) and **John Capobianco** (Creator, NetClaw), representing nearly a decade of profes... | `workspace/skills/ipfabric/SKILL.md` |
| `ipfix-receiver` | Receive and query IPFIX and NetFlow flow records from network devices via UDP. | `workspace/skills/ipfix-receiver/SKILL.md` |
| `ise-posture-audit` | Cisco ISE posture and policy audit - authorization rules, posture compliance, profiling gaps, TrustSec SGT matrix, active session health. Use when running a ... | `workspace/skills/ise-posture-audit/SKILL.md` |
| `itential-automation` | Itential Automation Platform (IAP) — network automation orchestration, device configuration management, compliance enforcement, workflow execution, golden co... | `workspace/skills/itential-automation/SKILL.md` |
| `jenkins-cicd` | Jenkins CI/CD pipeline management — monitor builds, trigger pipelines, analyze logs, and track SCM changes for network automation workflows. | `workspace/skills/jenkins-cicd/SKILL.md` |
| `junos-network` | Juniper JunOS device automation via PyEZ/NETCONF — CLI execution, configuration management, Jinja2 template rendering, device facts, batch operations, config... | `workspace/skills/junos-network/SKILL.md` |
| `kubeshark-traffic` | Kubeshark Kubernetes traffic analysis — L4/L7 deep packet inspection, TLS decryption, pcap export, flow analysis, service mapping (6 tools). Use when capturi... | `workspace/skills/kubeshark-traffic/SKILL.md` |
| `markmap-viz` | Create interactive mind map visualizations from markdown - network inventory, OSPF areas, BGP topology, security audit results. Use when visualizing network ... | `workspace/skills/markmap-viz/SKILL.md` |
| `memory` | The Memory skill enables NetClaw to remember information about your network across sessions. Instead of re-explaining your topology, device names, and past i... | `workspace/skills/memory/SKILL.md` |
| `mempalace` | MemPalace AI memory — persistent memory across sessions. Search past decisions, store architecture choices, track temporal network facts via knowledge graph,... | `workspace/skills/mempalace/SKILL.md` |
| `meraki-monitoring` | Cisco Meraki Monitoring & Diagnostics — live ping, cable test, LED blink, wake-on-LAN, camera analytics, config change tracking. Use when running ping tests ... | `workspace/skills/meraki-monitoring/SKILL.md` |
| `meraki-network-ops` | Cisco Meraki Dashboard — organization inventory, network management, device lifecycle, client discovery, action batches. Use when listing Meraki devices, man... | `workspace/skills/meraki-network-ops/SKILL.md` |
| `meraki-security-appliance` | Cisco Meraki Security Appliance (MX) — firewall rules, site-to-site VPN, content filtering, traffic shaping, security events. Use when auditing Meraki MX fir... | `workspace/skills/meraki-security-appliance/SKILL.md` |
| `meraki-switch-ops` | Cisco Meraki Switching — port configuration, VLANs, port status, ACLs, QoS rules, port cycling. Use when configuring Meraki switch ports, creating VLANs, che... | `workspace/skills/meraki-switch-ops/SKILL.md` |
| `meraki-wireless-ops` | Cisco Meraki Wireless — SSID management, RF profiles, channel utilization, signal quality, client connectivity events. Use when managing Meraki SSIDs, troubl... | `workspace/skills/meraki-wireless-ops/SKILL.md` |
| `msgraph-files` | Manage files on OneDrive and SharePoint via Microsoft Graph API - upload, download, list, search, and organize network documentation and artifacts. Use when ... | `workspace/skills/msgraph-files/SKILL.md` |
| `msgraph-teams` | Send notifications and reports to Microsoft Teams channels via Graph API - alert delivery, report posting, incident updates, and diagram sharing. Use when po... | `workspace/skills/msgraph-teams/SKILL.md` |
| `msgraph-visio` | Generate and manage Visio network diagrams on SharePoint via Microsoft Graph API - create topology diagrams from CDP/LLDP discovery, update existing diagrams... | `workspace/skills/msgraph-visio/SKILL.md` |
| `nmap-network-scan` | Host discovery and port scanning using nmap — ICMP/ARP host discovery, SYN/TCP/UDP port scanning with scope enforcement and audit logging. Use when discoveri... | `workspace/skills/nmap-network-scan/SKILL.md` |
| `nmap-scan-management` | Custom nmap scans with arbitrary flags, plus scan history retrieval and management. Use when running nmap with custom flags, reviewing past scan results, com... | `workspace/skills/nmap-scan-management/SKILL.md` |
| `nmap-service-detection` | Service fingerprinting, OS detection, NSE script execution, and vulnerability scanning using nmap MCP. Use when identifying services on open ports, fingerpri... | `workspace/skills/nmap-service-detection/SKILL.md` |
| `nso-device-ops` | Cisco NSO device operations — config retrieval, state inspection, sync, platform info, NED IDs, device groups. Use when retrieving device configs from NSO, c... | `workspace/skills/nso-device-ops/SKILL.md` |
| `nso-service-mgmt` | Cisco NSO service management — discover service types, list service instances, orchestrate network services. Use when listing NSO services, checking service ... | `workspace/skills/nso-service-mgmt/SKILL.md` |
| `packet-analysis` | Analyze network packet captures (.pcap/.pcapng) using Packet Buddy MCP. Use when opening a pcap file, inspecting packet captures, troubleshooting network tra... | `workspace/skills/packet-analysis/SKILL.md` |
| `pagerduty-incidents` | Manage and investigate incidents in PagerDuty. | `workspace/skills/pagerduty-incidents/SKILL.md` |
| `pagerduty-oncall` | Manage on-call schedules and escalation policies in PagerDuty. | `workspace/skills/pagerduty-oncall/SKILL.md` |
| `pagerduty-orchestration` | Manage event orchestration and routing rules in PagerDuty. | `workspace/skills/pagerduty-orchestration/SKILL.md` |
| `pagerduty-services` | Manage service catalog and service health in PagerDuty. | `workspace/skills/pagerduty-services/SKILL.md` |
| `paloalto-panorama` | Palo Alto Panorama operations — device groups, templates, security policy search, NAT review, commit status, and audit workflows. Use when searching Palo Alt... | `workspace/skills/paloalto-panorama/SKILL.md` |
| `prisma-sdwan-apps` | View Prisma SD-WAN application definitions for policy visibility | `workspace/skills/prisma-sdwan-apps/SKILL.md` |
| `prisma-sdwan-config` | Inspect Prisma SD-WAN interfaces, routing (BGP, static), policies, and security zones | `workspace/skills/prisma-sdwan-config/SKILL.md` |
| `prisma-sdwan-status` | Monitor Prisma SD-WAN element health, software versions, events, and alarms | `workspace/skills/prisma-sdwan-status/SKILL.md` |
| `prisma-sdwan-topology` | Discover Prisma SD-WAN sites, ION elements, machines, and network topology | `workspace/skills/prisma-sdwan-topology/SKILL.md` |
| `prometheus-monitoring` | Prometheus monitoring — PromQL instant/range queries, metric discovery, metadata, scrape target health, system health checks (6 tools). Use when querying Pro... | `workspace/skills/prometheus-monitoring/SKILL.md` |
| `protocol-participation` | Live BGP and OSPF control-plane participation — peer with real routers, inject/withdraw routes, query RIB/LSDB, adjust metrics, GRE tunnel status. Use when i... | `workspace/skills/protocol-participation/SKILL.md` |
| `pyats-asa-firewall` | Cisco ASA firewall operations via pyATS — VPN sessions, failover state, interfaces, routing, service policies, resource usage, AnyConnect monitoring. Use whe... | `workspace/skills/pyats-asa-firewall/SKILL.md` |
| `pyats-config-mgmt` | Network change management - pre-change baselines, configuration deployment, post-change verification, rollback procedures, and compliance validation. Use whe... | `workspace/skills/pyats-config-mgmt/SKILL.md` |
| `pyats-dynamic-test` | Generate and execute deterministic pyATS aetest validation scripts - interface state, OSPF neighbors, BGP paths, ping matrices, and custom compliance tests. ... | `workspace/skills/pyats-dynamic-test/SKILL.md` |
| `pyats-f5-ltm` | F5 BIG-IP LTM/GTM operations via pyATS iControl REST — virtual servers, pools, nodes, monitors, profiles, iRules, persistence, GTM wide IPs, DNS, data groups... | `workspace/skills/pyats-f5-ltm/SKILL.md` |
| `pyats-f5-platform` | F5 BIG-IP platform operations via pyATS iControl REST — system, networking, HA/CM, auth, analytics, security, APM, live-update, ADC certs, file management. U... | `workspace/skills/pyats-f5-platform/SKILL.md` |
| `pyats-health-check` | Comprehensive network device health monitoring - CPU, memory, interfaces, hardware, NTP, logging, environment, and uptime analysis. Use when running a device... | `workspace/skills/pyats-health-check/SKILL.md` |
| `pyats-junos-interfaces` | JunOS interface operations via pyATS — physical/logical interfaces, LACP, CoS, LLDP, ARP, BFD, IPv6 neighbors, traffic monitoring, optics diagnostics. Use wh... | `workspace/skills/pyats-junos-interfaces/SKILL.md` |
| `pyats-junos-routing` | JunOS routing operations via pyATS — OSPF/OSPFv3, BGP, route table, MPLS/LDP/RSVP, TED, PFE, ping, traceroute across Juniper devices. Use when checking Junip... | `workspace/skills/pyats-junos-routing/SKILL.md` |
| `pyats-junos-system` | JunOS system operations via pyATS — chassis health, hardware inventory, system info, NTP, SNMP, files/logs, firewall counters, DDoS protection, services acco... | `workspace/skills/pyats-junos-system/SKILL.md` |
| `pyats-linux-network` | Linux host network operations via pyATS — interface configuration, routing tables, network connections, and multi-table route inspection across fleet hosts. ... | `workspace/skills/pyats-linux-network/SKILL.md` |
| `pyats-linux-system` | Linux host system operations via pyATS — process monitoring, filesystem inspection, Docker container stats, package/tool verification across fleet hosts. Use... | `workspace/skills/pyats-linux-system/SKILL.md` |
| `pyats-linux-vmware` | VMware ESXi host operations via pyATS — VM inventory, snapshot management, hypervisor inspection across ESXi hosts in the testbed. Use when listing VMs on ES... | `workspace/skills/pyats-linux-vmware/SKILL.md` |
| `pyats-network` | Network device automation via pyATS - run show commands, ping, apply config, learn config/logging, list devices, run Linux commands, execute dynamic tests on... | `workspace/skills/pyats-network/SKILL.md` |
| `pyats-parallel-ops` | Fleet-wide parallel device operations - concurrent health checks, config audits, routing snapshots, severity-sorted reporting, and failure-isolated multi-dev... | `workspace/skills/pyats-parallel-ops/SKILL.md` |
| `pyats-routing` | CCIE-level routing protocol analysis - OSPF, BGP, EIGRP, IS-IS, static routes, RIB/FIB verification, redistribution audit, and convergence validation. Use wh... | `workspace/skills/pyats-routing/SKILL.md` |
| `pyats-security` | Network security audit - ACLs, AAA, control plane policing, management plane hardening, encryption, port security, and CIS benchmark checks. Use when auditin... | `workspace/skills/pyats-security/SKILL.md` |
| `pyats-topology` | Network topology discovery via CDP/LLDP neighbors, ARP tables, routing peers, and interface mapping to build complete network maps. Use when mapping the netw... | `workspace/skills/pyats-topology/SKILL.md` |
| `pyats-troubleshoot` | Systematic network troubleshooting - connectivity, routing, interface, protocol, and performance issues using structured OSI-layer and divide-and-conquer met... | `workspace/skills/pyats-troubleshoot/SKILL.md` |
| `radkit-remote-access` | Cisco RADKit — cloud-relayed remote device access, CLI execution, SNMP polling, device inventory discovery, attribute inspection. Use when accessing remote n... | `workspace/skills/radkit-remote-access/SKILL.md` |
| `rfc-lookup` | Search and retrieve IETF RFC documents - lookup by number, search by keyword, extract sections. Use when looking up an RFC, checking protocol specifications,... | `workspace/skills/rfc-lookup/SKILL.md` |
| `sdwan-ops` | Cisco SD-WAN vManage read-only operations — fabric devices, WAN Edge inventory, templates, policies, alarms, events, interface stats, BFD sessions, OMP route... | `workspace/skills/sdwan-ops/SKILL.md` |
| `servicenow-change-workflow` | Full ITSM-gated change lifecycle - CR creation, pre-change incident validation, approval gate, execution via pyats-config-mgmt, post-change verification, and... | `workspace/skills/servicenow-change-workflow/SKILL.md` |
| `slack-incident-workflow` | Manage network incident response workflows in Slack - incident channels, status updates, escalation, resolution tracking, and post-incident review coordinati... | `workspace/skills/slack-incident-workflow/SKILL.md` |
| `slack-network-alerts` | Format and deliver network alerts, health warnings, and critical notifications via Slack with rich formatting, reactions, and file attachments. Use when send... | `workspace/skills/slack-network-alerts/SKILL.md` |
| `slack-report-delivery` | Deliver formatted network reports, audit results, topology diagrams, and compliance documentation to Slack channels with rich Block Kit formatting. Use when ... | `workspace/skills/slack-report-delivery/SKILL.md` |
| `slack-user-context` | Leverage Slack user profiles, presence, DND status, and workspace context to personalize responses, route escalations, and coordinate team operations. Use wh... | `workspace/skills/slack-user-context/SKILL.md` |
| `slack-voice-interface` | Respond to Slack voice clips with both text and an MP3 voice reply using edge-tts. Voice IN is already handled by OpenClaw transcription. Use when a user sen... | `workspace/skills/slack-voice-interface/SKILL.md` |
| `snmptrap-receiver` | Receive and query SNMP traps from network devices via UDP. | `workspace/skills/snmptrap-receiver/SKILL.md` |
| `splunk-indexes` | Discover and inspect Splunk indexes and configuration. | `workspace/skills/splunk-indexes/SKILL.md` |
| `splunk-saved` | Manage and run saved searches in Splunk. | `workspace/skills/splunk-saved/SKILL.md` |
| `splunk-search` | Execute and validate SPL (Search Processing Language) queries. | `workspace/skills/splunk-search/SKILL.md` |
| `subnet-calculator` | IPv4 and IPv6 subnet calculator - CIDR breakdown, usable hosts, previous/next subnets, address classification, VLSM planning, and dual-stack analysis. Use wh... | `workspace/skills/subnet-calculator/SKILL.md` |
| `suzieq-observability` | SuzieQ network observability — query current and historical network state, run validation assertions, get summary statistics, trace forwarding paths, and dis... | `workspace/skills/suzieq-observability/SKILL.md` |
| `syslog-receiver` | Receive and query syslog messages from network devices via UDP. | `workspace/skills/syslog-receiver/SKILL.md` |
| `te-network-monitoring` | Cisco ThousandEyes — test management, agent inventory, test results, dashboards, path visualization, user/account management. Use when checking ThousandEyes ... | `workspace/skills/te-network-monitoring/SKILL.md` |
| `te-path-analysis` | Cisco ThousandEyes — path visualization, BGP route analysis, outage investigation, instant tests, endpoint agent diagnostics. Use when tracing network paths ... | `workspace/skills/te-path-analysis/SKILL.md` |
| `telemetry-ops` | Comprehensive network telemetry and event collection across multiple protocols. | `workspace/skills/telemetry-ops/SKILL.md` |
| `terraform-operations` | Execute local Terraform operations with ServiceNow change control. | `workspace/skills/terraform-operations/SKILL.md` |
| `terraform-registry` | Discover providers and modules from the Terraform Registry. | `workspace/skills/terraform-registry/SKILL.md` |
| `terraform-workspaces` | Manage HCP Terraform (Terraform Cloud/Enterprise) workspaces. | `workspace/skills/terraform-workspaces/SKILL.md` |
| `threejs-network-viz` | Renders network topologies as interactive, fully-labeled 3D scenes directly in a web browser, using Three.js. Unlike NetClaw's UE5 (`ue5-network-viz`) and Bl... | `workspace/skills/threejs-network-viz/SKILL.md` |
| `token-tracker` | Track and display token consumption and cost for every NetClaw interaction. | `workspace/skills/token-tracker/SKILL.md` |
| `twilio-daily-briefing` | Provide optional daily phone briefings at a scheduled time with overnight event summaries. | `workspace/skills/twilio-daily-briefing/SKILL.md` |
| `twilio-emergency-call` | Automatically call John when critical network events occur (P1 incidents, core device failures). Emergency calls bypass quiet hours and are auto-approved wit... | `workspace/skills/twilio-emergency-call/SKILL.md` |
| `twilio-inbound-voice` | Enable John to call NetClaw's Twilio number and have a bidirectional voice conversation for status queries and network commands. | `workspace/skills/twilio-inbound-voice/SKILL.md` |
| `twilio-outbound-call` | Enable John to request on-demand phone calls for network status updates and schedule periodic update calls during ongoing incidents. | `workspace/skills/twilio-outbound-call/SKILL.md` |
| `twitter-check` | This skill provides a quick way for John to invoke the Twitter mention check and auto-respond workflow directly from Claude Code. | `workspace/skills/twitter-check/SKILL.md` |
| `twitter-heartbeat` | The twitter-heartbeat skill enables NetClaw to: | `workspace/skills/twitter-heartbeat/SKILL.md` |
| `twitter-respond` | Enables bidirectional Twitter interaction by monitoring @mentions of @John_Capobianco and generating CCIE-level technical replies. All replies require human ... | `workspace/skills/twitter-respond/SKILL.md` |
| `twitter-share` | The twitter-share skill enables users to ask NetClaw to tweet specific content. All tweets go through content guardrails and require explicit human approval ... | `workspace/skills/twitter-share/SKILL.md` |
| `ue5-network-viz` | The UE5 Network Visualization skill enables 3D network topology visualization in Unreal Engine 5.8 using the built-in MCP server. Network engineers can reque... | `workspace/skills/ue5-network-viz/SKILL.md` |
| `uml-diagram` | UML and diagram generation via Kroki — class, sequence, activity, state, component, deployment, network, ER, C4, Mermaid, D2, Graphviz, BPMN, 27+ types. Use ... | `workspace/skills/uml-diagram/SKILL.md` |
| `vault-mounts` | Discover and manage HashiCorp Vault secret engine mounts. | `workspace/skills/vault-mounts/SKILL.md` |
| `vault-pki` | Manage HashiCorp Vault PKI certificate infrastructure. | `workspace/skills/vault-pki/SKILL.md` |
| `vault-secrets` | Manage HashiCorp Vault KV secrets with strict value protection. | `workspace/skills/vault-secrets/SKILL.md` |
| `webex-incident-workflow` | Manage network incident response workflows in Cisco WebEx - incident spaces, status updates, escalation, resolution tracking, and post-incident review coordi... | `workspace/skills/webex-incident-workflow/SKILL.md` |
| `webex-network-alerts` | Format and deliver network alerts, health warnings, and critical notifications via Cisco WebEx with Adaptive Cards, markdown formatting, and file attachments... | `workspace/skills/webex-network-alerts/SKILL.md` |
| `webex-report-delivery` | Deliver formatted network reports, audit results, topology diagrams, and compliance documentation to WebEx spaces with Adaptive Cards and markdown formatting... | `workspace/skills/webex-report-delivery/SKILL.md` |
| `webex-user-context` | Leverage WebEx user profiles, presence status, and workspace context to personalize responses, route escalations, and coordinate team operations. Use when ch... | `workspace/skills/webex-user-context/SKILL.md` |
| `webex-voice-interface` | Respond to WebEx voice clips with both text and an MP3 voice reply using edge-tts. Voice IN is already handled by OpenClaw transcription. Use when a user sen... | `workspace/skills/webex-voice-interface/SKILL.md` |
| `wikipedia-research` | Research networking protocols, standards history, and technology context via Wikipedia - OSPF, BGP, MPLS, 802.1X, VXLAN, and more. Use when looking up protoc... | `workspace/skills/wikipedia-research/SKILL.md` |
| `zscaler-identity` | Manage users, groups, departments, and identity provider configurations. | `workspace/skills/zscaler-identity/SKILL.md` |
| `zscaler-insights` | Access analytics, threat intelligence, and security event data. | `workspace/skills/zscaler-insights/SKILL.md` |
| `zscaler-zdx` | Monitor digital experience scores, user performance, and application health. | `workspace/skills/zscaler-zdx/SKILL.md` |
| `zscaler-zia` | Manage Zscaler Internet Access firewall rules, URL filtering, DLP, and security policies. | `workspace/skills/zscaler-zia/SKILL.md` |
| `zscaler-zpa` | Manage Zscaler Private Access applications, segments, policies, and connectors. | `workspace/skills/zscaler-zpa/SKILL.md` |
