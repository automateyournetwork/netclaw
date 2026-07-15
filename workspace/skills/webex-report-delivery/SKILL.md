---
name: webex-report-delivery
description: "Deliver formatted network reports, audit results, topology diagrams, and compliance documentation to WebEx spaces with Adaptive Cards and markdown formatting. Use when posting a health check report, sharing a security audit, delivering topology diagrams, or sending scheduled network reports to WebEx."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# WebEx Report Delivery

## WebEx API Capabilities Used

| API | Purpose |
|-----|---------|
| Messages -- Create | Post report messages to spaces |
| Messages -- Create (Adaptive Card) | Deliver rich formatted reports with tables and data |
| Messages -- Create (with files) | Attach full reports, diagrams, spreadsheets |
| Messages -- List | Find previous reports for comparison |
| Rooms -- List | Discover target spaces for report delivery |

## Report Types and Formatting

### 1. Health Check Report (Adaptive Card)

Post after running the pyats-health-check skill:

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "TextBlock",
      "text": "Device Health Report -- R1",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "TextBlock",
      "text": "_2024-02-21 14:00 UTC_",
      "isSubtle": true
    },
    {
      "type": "TextBlock",
      "text": "**Device:** C8000V | IOS-XE 17.9.4a | Uptime: 47d 12h"
    },
    {
      "type": "ColumnSet",
      "columns": [
        { "type": "Column", "width": "stretch", "items": [{"type":"TextBlock","text":"**Check**","weight":"Bolder"},{"type":"TextBlock","text":"CPU (5min avg)"},{"type":"TextBlock","text":"Memory"},{"type":"TextBlock","text":"Interfaces"},{"type":"TextBlock","text":"Hardware"},{"type":"TextBlock","text":"NTP"},{"type":"TextBlock","text":"Logs"},{"type":"TextBlock","text":"Connectivity"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Status**","weight":"Bolder"},{"type":"TextBlock","text":"12%","color":"Good"},{"type":"TextBlock","text":"78%","color":"Warning"},{"type":"TextBlock","text":"All up","color":"Good"},{"type":"TextBlock","text":"OK","color":"Good"},{"type":"TextBlock","text":"Synced","color":"Good"},{"type":"TextBlock","text":"3 events","color":"Warning"},{"type":"TextBlock","text":"100%","color":"Good"}]},
        { "type": "Column", "width": "stretch", "items": [{"type":"TextBlock","text":"**Details**","weight":"Bolder"},{"type":"TextBlock","text":"Normal"},{"type":"TextBlock","text":"2.0G / 2.6G -- elevated"},{"type":"TextBlock","text":"4/4 interfaces up/up"},{"type":"TextBlock","text":"All modules operational"},{"type":"TextBlock","text":"Offset 2ms to 10.0.0.1"},{"type":"TextBlock","text":"3 OSPF adjacency flaps"},{"type":"TextBlock","text":"RTT 23ms to 8.8.8.8"}]}
      ]
    },
    {
      "type": "TextBlock",
      "text": "**Overall: WARNING** -- 2 items need attention",
      "color": "Warning",
      "weight": "Bolder"
    },
    {
      "type": "TextBlock",
      "text": "_Full report in thread_",
      "isSubtle": true
    }
  ]
}
```

Thread the detailed per-section output as follow-up messages using `parentId`.

### 2. Security Audit Report (Markdown)

Post after running the pyats-security skill:

```
**Security Audit Report -- R1**
_2024-02-21 | IOS-XE 17.9.4a_

**Summary:** 2 CRITICAL | 2 HIGH | 3 MEDIUM | 2 LOW

---

**CRITICAL**
- **C-001:** SSHv1 enabled -- vulnerable to MITM attacks
  > _Remediation:_ `ip ssh version 2`
- **C-002:** No VTY access-class -- management plane exposed to any source
  > _Remediation:_ Apply `access-class MGMT-ACL in` on VTY lines

**HIGH**
- **H-001:** No OSPF authentication on Gi1 -- route injection risk
- **H-002:** SNMP community 'public' with no source ACL

**MEDIUM**
- M-001: No CoPP policy configured
- M-002: HTTP server enabled (ip http server)
- M-003: Console exec-timeout set to 0 0 (no timeout)

_Detailed findings with remediation commands in thread_
```

### 3. Topology Discovery Report (Markdown)

Post after running the pyats-topology skill:

```
**Topology Discovery -- 2024-02-21**

**Devices Discovered:** 5 | **Links Mapped:** 12

**Discovery Sources:**
- CDP: 8 links (Cisco-to-Cisco)
- LLDP: 3 links (multi-vendor)
- OSPF: 4 routing adjacencies
- BGP: 2 peering sessions
- ARP: 23 L3 neighbors

**Adjacency Table:**
```
R1:Gi1  <-> R2:Gi1     (10.1.1.0/30, OSPF Area 0)
R1:Gi2  <-> SW1:Gi0/1  (10.1.2.0/24, Access VLAN 10)
R2:Gi2  <-> SW2:Gi0/1  (10.2.1.0/24, Access VLAN 20)
R1:Gi3  <-> ISP:eth0   (203.0.113.0/30, eBGP AS 65000)
```

_Draw.io diagram and full topology model in thread_
```

### 4. NetBox Reconciliation Report (Adaptive Card)

Post after running the netbox-reconcile skill:

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "TextBlock",
      "text": "NetBox Reconciliation Report -- 2024-02-21",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "TextBlock",
      "text": "**Scope:** 5 devices | 47 interfaces | 12 cables"
    },
    {
      "type": "ColumnSet",
      "columns": [
        { "type": "Column", "width": "stretch", "items": [{"type":"TextBlock","text":"**Category**","weight":"Bolder"},{"type":"TextBlock","text":"DOCUMENTED"},{"type":"TextBlock","text":"UNDOCUMENTED"},{"type":"TextBlock","text":"MISSING"},{"type":"TextBlock","text":"MISMATCH"},{"type":"TextBlock","text":"IP DRIFT"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Count**","weight":"Bolder"},{"type":"TextBlock","text":"10","color":"Good"},{"type":"TextBlock","text":"1","color":"Warning"},{"type":"TextBlock","text":"1","color":"Attention"},{"type":"TextBlock","text":"0","color":"Good"},{"type":"TextBlock","text":"2","color":"Warning"}]}
      ]
    },
    {
      "type": "TextBlock",
      "text": "**Actions Required:**\n1. Add R1:Gi3 <-> ISP:eth0 cable to NetBox\n2. Investigate missing NB cable #47 (R2:Gi3 <-> SW3:Gi0/2)\n3. Update R2 Loopback0 IP in NetBox (10.2.2.2 -> 10.2.2.3)",
      "wrap": true
    }
  ]
}
```

### 5. Change Report (Markdown)

Post after running the pyats-config-mgmt skill:

```
**Change Report -- R1**
_2024-02-21 14:30 UTC | ServiceNow CR: CHG0012345_

**Change:** Add Loopback99 for OSPF router-id migration

**Config Applied:**
```
interface Loopback99
 ip address 99.99.99.99 255.255.255.255
 description OSPF-RID-Migration
 no shutdown
```

**Verification: PASSED**
- Routing table: 47 -> 48 routes (+1 connected 99.99.99.99/32)
- OSPF neighbors: 2 (FULL) -- no change
- Connectivity: 100% to 8.8.8.8 -- no change
- New log: %LINEPROTO-5-UPDOWN: Loopback99 up/up

**Rollback:** Not required
**CR Status:** Closed (successful)
```

### 6. Vulnerability Scan Report (Adaptive Card)

Post after running the nvd-cve skill:

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "TextBlock",
      "text": "Vulnerability Scan -- Fleet Summary",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "TextBlock",
      "text": "_2024-02-21 | NVD Database_",
      "isSubtle": true
    },
    {
      "type": "ColumnSet",
      "columns": [
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Device**","weight":"Bolder"},{"type":"TextBlock","text":"R1"},{"type":"TextBlock","text":"R2"},{"type":"TextBlock","text":"SW1"}]},
        { "type": "Column", "width": "stretch", "items": [{"type":"TextBlock","text":"**Software**","weight":"Bolder"},{"type":"TextBlock","text":"IOS-XE 17.9.4a"},{"type":"TextBlock","text":"IOS-XE 17.12.1"},{"type":"TextBlock","text":"IOS-XE 16.12.4"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**CRIT**","weight":"Bolder"},{"type":"TextBlock","text":"2","color":"Attention"},{"type":"TextBlock","text":"0","color":"Good"},{"type":"TextBlock","text":"5","color":"Attention"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**HIGH**","weight":"Bolder"},{"type":"TextBlock","text":"3","color":"Warning"},{"type":"TextBlock","text":"1","color":"Warning"},{"type":"TextBlock","text":"8","color":"Warning"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Action**","weight":"Bolder"},{"type":"TextBlock","text":"URGENT","color":"Attention"},{"type":"TextBlock","text":"PLAN","color":"Warning"},{"type":"TextBlock","text":"URGENT","color":"Attention"}]}
      ]
    },
    {
      "type": "TextBlock",
      "text": "**Top Exposures:**\n- CVE-2023-20198 (CVSS 10.0) -- Affects R1, SW1 -- HTTP server exposed\n- CVE-2023-20273 (CVSS 7.2) -- Affects R1 -- Web UI accessible",
      "wrap": true
    },
    {
      "type": "TextBlock",
      "text": "_Detailed CVE analysis per device in thread_",
      "isSubtle": true
    }
  ]
}
```

## Scheduled Report Delivery

NetClaw can deliver reports on a schedule when asked:

| Report | Suggested Cadence | Space |
|--------|------------------|-------|
| Fleet health check | Daily 06:00 UTC | NetClaw Reports |
| Security audit | Weekly (Monday) | NetClaw Reports |
| NetBox reconciliation | Weekly (Wednesday) | NetClaw Reports |
| Vulnerability scan | Monthly (1st) | NetClaw Reports |
| Topology validation | Monthly (15th) | NetClaw Reports |

## Formatting Guidelines

1. **Use Adaptive Cards for structured data** -- tables, FactSets, ColumnSets for alignment
2. **Use markdown for narrative content** -- security findings, topology descriptions, change summaries
3. **Thread long outputs** -- keep top-level messages concise, put details in threaded replies via `parentId`
4. **Attach files for full reports** -- text files for detailed output, images for diagrams
5. **Always include timestamps** -- UTC, ISO format
6. **Link to ServiceNow CRs** -- when changes are involved
7. **Reference GAIT sessions** -- for audit trail continuity
8. **Include fallback text** -- always set the `markdown` field alongside Adaptive Card attachments

## Comparison with Previous Reports

When delivering a new report, reference the previous one:

```
**Health Trend -- R1**
_Compared to last check (2024-02-20 14:00 UTC)_

| Metric | Previous | Current | Trend |
|--------|----------|---------|-------|
| CPU 5min | 10% | 12% | Stable |
| Memory | 71% | 78% | +7% |
| Interfaces | 4/4 up | 4/4 up | Stable |
| Ping RTT | 21ms | 23ms | Stable |

**WARNING:** Memory trending upward -- investigate if continues
```
