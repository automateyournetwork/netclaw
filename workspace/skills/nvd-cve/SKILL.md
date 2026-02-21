---
name: nvd-cve
description: "Search the National Vulnerability Database for CVEs - find vulnerabilities by keyword or ID, get CVSS scores, weaknesses, affected configurations, and remediation references"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["NVD_MCP_SCRIPT", "MCP_CALL"] } } }
---

# NVD CVE Vulnerability Search

Query the NIST National Vulnerability Database (NVD) for CVE vulnerabilities using the mcp-nvd server. Requires an NVD API key (`NVD_API_KEY` environment variable).

## Available Tools

### 1. `get_cve` — Look Up a Specific CVE by ID

```bash
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" get_cve '{"cve_id":"CVE-2023-20198"}'
```

**Parameters:**
- `cve_id` (required): The CVE identifier, e.g., `CVE-2023-20198`
- `concise` (optional, default `false`): Set `true` for brief output (ID, description, CVSS score only)

**Returns:** Full CVE details including:
- CVSS v3.1 and v2.0 scores, severity, vector string
- Exploitability and impact scores
- CWE weakness identifiers
- References with tags (Vendor Advisory, Patch, Exploit, etc.)
- Affected configurations (CPE entries)

### 2. `search_cve` — Search CVEs by Keyword

```bash
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" search_cve '{"keyword":"Cisco IOS XE 17.9"}'
```

**Parameters:**
- `keyword` (required): Search term, e.g., `"Cisco IOS XE"`, `"NX-OS 10.2"`, `"OpenSSL 3.0"`
- `exact_match` (optional, default `false`): Require exact keyword match
- `concise` (optional, default `false`): Brief output per CVE
- `results` (optional, default `10`): Number of results to return (max 2000)

**Returns:** List of matching CVEs with full details, plus total count.

## When to Use

- **Post-health-check vulnerability scan**: After `show version` reveals the IOS-XE/NX-OS version, search NVD for known CVEs
- **Security audit enrichment**: Cross-reference running config features (HTTP server, SNMP, SSH) against CVEs
- **Incident response**: Look up specific CVE IDs mentioned in advisories
- **Compliance reporting**: Document known vulnerabilities and remediation status
- **Upgrade planning**: Compare CVE exposure between current and target versions

## Vulnerability Audit Workflow

### Step 1: Extract Software Version

From a device health check, extract the software version (e.g., `IOS-XE 17.9.4a`).

### Step 2: Search NVD for Version-Specific CVEs

```bash
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" search_cve '{"keyword":"Cisco IOS XE 17.9.4","results":20}'
```

### Step 3: Get Details for Critical/High CVEs

For each CVE with CVSS >= 7.0, pull full details:

```bash
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" get_cve '{"cve_id":"CVE-2023-20198"}'
```

### Step 4: Exposure Correlation

Cross-reference CVE requirements against the device running config:

| CVE | Requires | Running Config | Exposed? |
|-----|----------|---------------|----------|
| CVE-2023-20198 | HTTP/HTTPS server enabled | `ip http server` present | **YES** |
| CVE-2023-20273 | Web UI accessible | `ip http secure-server` + no ACL | **YES** |
| CVE-2024-XXXXX | OSPF enabled | `router ospf 1` present | **YES** |

### Step 5: Produce Vulnerability Report

```
Vulnerability Audit — YYYY-MM-DD
Device: R1 | IOS-XE 17.9.4a

CRITICAL (CVSS >= 9.0):
  CVE-2023-20198 (CVSS 10.0) — IOS-XE Web UI privilege escalation
    Exposure: CONFIRMED — ip http server enabled
    Remediation: Upgrade to 17.9.4a+ or disable ip http server

HIGH (CVSS >= 7.0):
  CVE-2023-20273 (CVSS 7.2) — Web UI command injection
    Exposure: CONFIRMED — ip http secure-server, no ACL
    Remediation: Apply access-class to HTTP server or upgrade

MEDIUM (CVSS >= 4.0):
  [none found]

Summary: 2 CRITICAL (2 exposed), 0 HIGH, 0 MEDIUM
```

### Step 6: Search by Feature Keywords

When auditing specific features, search for feature-specific CVEs:

```bash
# SNMP vulnerabilities
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" search_cve '{"keyword":"Cisco SNMP remote code execution","results":10}'

# BGP vulnerabilities
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" search_cve '{"keyword":"Cisco BGP denial of service","results":10}'

# SSH vulnerabilities
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" search_cve '{"keyword":"Cisco IOS SSH vulnerability","results":10}'
```

## CVSS Severity Mapping

| CVSS Score | Severity | Action Timeline |
|-----------|----------|-----------------|
| 9.0 - 10.0 | CRITICAL | Immediate remediation required |
| 7.0 - 8.9 | HIGH | Remediate within 1 change window |
| 4.0 - 6.9 | MEDIUM | Remediate in next maintenance window |
| 0.1 - 3.9 | LOW | Document and track |

## Fleet-Wide Vulnerability Scan

Run version discovery across all devices, then batch-search NVD for each unique version:

```bash
# Step 1: Get version from each device
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show version"}'

# Step 2: Search NVD for each unique version found
NVD_API_KEY=$NVD_API_KEY python3 $MCP_CALL "python3 -u $NVD_MCP_SCRIPT" search_cve '{"keyword":"Cisco IOS XE 17.9.4","results":20,"concise":true}'
```

Produce a fleet vulnerability matrix:

```
┌──────────┬───────────────────┬──────────┬──────┬──────┬────────┐
│ Device   │ Software Version  │ CRITICAL │ HIGH │ MED  │ Action │
├──────────┼───────────────────┼──────────┼──────┼──────┼────────┤
│ R1       │ IOS-XE 17.9.4a    │ 2        │ 3    │ 5    │ URGENT │
│ R2       │ IOS-XE 17.12.1    │ 0        │ 1    │ 2    │ PLAN   │
│ SW1      │ IOS-XE 16.12.4    │ 5        │ 8    │ 12   │ URGENT │
└──────────┴───────────────────┴──────────┴──────┴──────┴────────┘
```

## GAIT Audit Trail

Record vulnerability scans in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"NVD vulnerability scan on R1 (IOS-XE 17.9.4a): 2 CRITICAL (CVE-2023-20198, CVE-2023-20273), 3 HIGH, 5 MEDIUM. Both CRITICAL CVEs confirmed exposed via running config analysis.","artifacts":[]}}'
```
