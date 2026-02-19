# Example: Full Autonomous Audit

## Prompt

```
Run a complete audit on R1 — health, security, routing, topology, vulnerabilities — and give me the full report
```

## What NetClaw Does

This is the most comprehensive workflow. NetClaw chains all skills together autonomously:

### Phase 1: Health Check (pyats-health-check)

```
→ show version           → Identity, uptime, software version
→ show processes cpu     → CPU utilization and top processes
→ show processes memory  → Memory utilization
→ show ip interface brief → Interface status overview
→ show interfaces        → Error counters and rates
→ show inventory         → Hardware modules
→ show ntp associations  → Time synchronization
→ pyats_show_logging     → System log analysis
→ ping 8.8.8.8           → Connectivity baseline
```

**Output:** Health report card with severity ratings per check.

### Phase 2: Security Audit (pyats-security)

```
→ pyats_show_running_config → Full config scan
→ show aaa servers          → AAA configuration
→ show ip access-lists      → ACL analysis with hit counts
→ show policy-map control-plane → CoPP status
→ show crypto key mypubkey rsa  → SSH key strength
→ show snmp                 → SNMP configuration
```

**Checks 40+ security controls:**
- Management plane: SSH version, VTY ACLs, timeouts, banners, HTTP disabled
- AAA: TACACS+/RADIUS, local fallback, accounting
- Access control: ACL completeness, hit counts, implicit deny logging
- CoPP: Rate limiting on control plane
- Routing auth: OSPF MD5, BGP MD5/GTSM, EIGRP key-chain
- Infrastructure: uRPF, CDP restriction, ICMP controls, proxy-ARP
- Credentials: Type 8/9 hashes, no cleartext, SNMP community strength

**Output:** CIS benchmark-style report with CRITICAL/HIGH/MEDIUM/LOW findings.

### Phase 3: Routing Analysis (pyats-routing)

```
→ show ip route           → Full routing table
→ show ip route summary   → Route counts by protocol
→ show ip ospf            → OSPF process overview
→ show ip ospf neighbor   → OSPF adjacencies
→ show ip ospf database   → LSDB summary
→ show ip bgp summary     → BGP peer status
→ show ip protocols       → Redistribution points
→ show route-map          → Route filtering policies
→ show ip prefix-list     → Prefix lists
```

**Analysis:**
- All adjacencies healthy (FULL/Established)
- Route counts match expectations
- No redistribution without filtering
- No suboptimal paths detected
- No routing loops

**Output:** Protocol status summary with anomaly flags.

### Phase 4: Topology Discovery (pyats-topology)

```
→ show cdp neighbors detail  → Cisco neighbor mapping
→ show lldp neighbors detail → Multi-vendor neighbors
→ show arp                   → L3 neighbor table
→ show ip ospf neighbor      → Routing adjacencies
→ show vrf                   → VRF topology
→ show standby brief         → FHRP groups
```

**Output:** Unified topology model with device inventory, link map, and subnet assignments.

### Phase 5: Vulnerability Scan (nvd-cve + pyats-network)

```
→ show version               → Extract IOS-XE version
→ nvd-cve search_cves        → Search NVD by version string
→ nvd-cve get_cve_details    → Get CVSS scores for each hit
→ pyats_show_running_config   → Check exposure (HTTP server, etc.)
```

**Output:** CVE list classified by severity with exposure assessment.

### Phase 6: Visualization

If topology data warrants it:

```
→ drawio-diagram  → Network topology diagram
→ markmap-viz     → OSPF area mind map
```

### Phase 7: Final Report

NetClaw assembles everything into a single report:

```
═══════════════════════════════════════════════════
  NetClaw Full Audit Report
  Device: R1 (devnetsandboxiosxec8k.cisco.com)
  Date: 2025-02-19
═══════════════════════════════════════════════════

1. HEALTH STATUS: HEALTHY
   CPU: 8% | Memory: 42% | Interfaces: 3/3 up | NTP: synced
   Uptime: 45d 12h | No critical log events

2. SECURITY POSTURE: 2 Critical, 1 High, 3 Medium
   [C-001] HTTP server enabled — web UI CVEs exploitable
   [C-002] No VTY access-class — management exposed
   [H-001] SNMP community 'public' with no ACL
   [M-001] No CoPP policy
   [M-002] No login banner
   [M-003] Console timeout set to 0 (never)

3. ROUTING: HEALTHY
   OSPF: 2 neighbors (FULL), Area 0
   BGP: 1 peer (Established, 5 prefixes)
   Routes: 47 total (12 connected, 8 OSPF, 5 BGP, 22 static)

4. TOPOLOGY: 3 devices discovered
   R1 ↔ R2 (Gi1, OSPF Area 0)
   R1 ↔ SW1 (Gi2, VLAN 10)
   R1 ↔ ISP (BGP AS 65002)

5. VULNERABILITIES: 2 Critical, 1 High
   CVE-2023-20198 (10.0) — EXPLOITABLE (HTTP server enabled)
   CVE-2023-20273 (9.8) — EXPLOITABLE (HTTP server enabled)
   CVE-2024-20353 (8.6) — EXPLOITABLE (HTTP server enabled)

═══════════════════════════════════════════════════
  PRIORITY ACTIONS
═══════════════════════════════════════════════════

  1. [IMMEDIATE] Disable HTTP server: 'no ip http server'
     Mitigates: CVE-2023-20198, CVE-2023-20273, CVE-2024-20353
  2. [IMMEDIATE] Add VTY access-class restricting management access
  3. [THIS WEEK] Replace SNMP community 'public', add ACL
  4. [THIS WEEK] Configure CoPP to protect control plane
  5. [THIS MONTH] Plan IOS-XE upgrade to latest maintenance release
  6. [THIS MONTH] Add login banner for legal compliance
```

## Skills Used

- **pyats-health-check** (Phase 1)
- **pyats-security** (Phase 2)
- **pyats-routing** (Phase 3)
- **pyats-topology** (Phase 4)
- **pyats-network** (underlying MCP calls for all phases)
- **nvd-cve** (Phase 5)
- **drawio-diagram** (Phase 6)
- **markmap-viz** (Phase 6)
- **rfc-lookup** (referenced if config recommendations needed)
