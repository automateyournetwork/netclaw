---
name: fwrule-analyzer
description: "Multi-vendor firewall rule analysis — overlap detection, shadowing, conflict identification, duplication checking across PAN-OS, ASA, FTD, IOS/IOS-XE, IOS-XR, Check Point, SRX, Junos, Nokia SR OS, and Fortinet FortiOS/FortiGate. Use when validating firewall rule changes, auditing rulesets for conflicts, or normalizing vendor configs to a common schema."
version: 1.1.0
license: Apache-2.0
tags: [firewall, rule-analysis, overlap, shadowing, conflict, multi-vendor, security, fortios, fortigate]
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# Firewall Rule Analyzer

## MCP Server

- **Repository**: [AutomateIP/fwrule-mcp](https://github.com/AutomateIP/fwrule-mcp)
- **Transport**: stdio (Python via `uv run fwrule-mcp`)
- **Install**: `git clone` + `uv sync` (or `pip install -e .`)
- **Requires**: No environment variables — standalone analysis engine
- **Dependencies**: `fastmcp>=2.0`, `pydantic>=2.0`, Python 3.11+

## Available Tools (3)

| Tool | What It Does |
|------|-------------|
| `analyze_firewall_rule_overlap` | Compare a candidate rule against an existing ruleset using 6-dimensional set intersection (zones, addresses, ports, protocols, actions, applications). Detects overlaps, shadowing, conflicts, and duplicates. Supports two input modes: vendor-native config via built-in parsers, or pre-normalized JSON. |
| `parse_policy` | Convert vendor-native firewall configurations into a standardized JSON schema. Enables inspection of parser output — rule counts, object resolution, address expansion — before running overlap analysis. |
| `list_supported_vendors` | Enumerate all supported firewall vendors, their aliases, configuration formats, and explain how to use normalized JSON input to bypass vendor-specific parsers. |

## Supported Vendors (10)

| Vendor | Config Format | Versions | Identifiers |
|--------|---------------|----------|-------------|
| Palo Alto PAN-OS | XML export | 9.x–11.x | `panos`, `paloalto`, `panorama` |
| Cisco ASA | show running-config | 9.x+ | `asa`, `cisco-asa` |
| Cisco FTD | FMC JSON | 6.x–7.x | `ftd`, `firepower`, `fmc` |
| Cisco IOS/IOS-XE | show running-config | 12.x–17.x | `ios`, `iosxe`, `cisco-ios` |
| Cisco IOS-XR | show running-config | 6.x+ | `iosxr`, `ios-xr`, `xr` |
| Check Point | JSON rulebase | R80.x–R82.x | `checkpoint`, `cp`, `check-point` |
| Juniper SRX | display set | 19.x+ | `juniper`, `srx` |
| Juniper Junos | display set | 18.x+ | `junos`, `mx`, `ptx`, `qfx` |
| Nokia SR OS | MD-CLI format | 20.x+ | `sros`, `nokia`, `sr-os` |
| **Fortinet FortiOS** | **Full backup config** | **5.x–7.x** | **`fortios`, `fortigate`, `fortinet`, `forti`, `fgt`, `fmg`** |

> ⚠️ FortiOS parser contributed by SIA/NetClaw (Airowire Networks). PR open at [AutomateIP/fwrule-mcp#1](https://github.com/AutomateIP/fwrule-mcp/pull/1). Install from the fork until merged upstream: `pip install git+https://github.com/akshaysiddaram/fwrule-mcp.git`

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **Overlap** | Candidate rule matches traffic already handled by existing rules |
| **Shadowing** | Candidate rule is fully covered by a higher-priority existing rule — it will never match |
| **Conflict** | Rules match the same traffic but have different actions (allow vs deny) |
| **Duplication** | Candidate rule is functionally identical to an existing rule |
| **6-Dimensional Analysis** | Comparison across source/dest zones, source/dest addresses, services/ports, protocols, actions, and applications |
| **Normalized JSON** | Vendor-agnostic rule schema with standardized fields (id, position, enabled, action, zones, addresses, services, applications) |

## Two Input Modes

### Mode 1: Vendor-Native Config
Pass raw vendor configuration text and let the built-in parsers normalize it:
- `vendor`: Vendor identifier (e.g., `panos`, `asa`, `ftd`, `ios`, `checkpoint`, `srx`, `junos`, `nokia`, `fortios`)
- `ruleset_payload`: Complete firewall config in vendor format
- `candidate_rule_payload`: Single rule in vendor format
- `os_version`: Optional version hint for parser selection
- `context_objects`: Supplemental object definitions as JSON

### Mode 2: Pre-Normalized JSON
Bypass parsers when structured data is already available:
- `existing_rules`: JSON array of normalized rule objects
- `candidate_rule`: Single normalized JSON rule object

## Workflow: Pre-Change Rule Validation

When adding a new firewall rule to a policy:

1. **Parse existing policy**: `parse_policy` with vendor config — normalize to JSON, verify rule count and object resolution
2. **Analyze candidate**: `analyze_firewall_rule_overlap` — check the proposed rule against the existing ruleset
3. **Review findings**: Examine overlap type (shadow, conflict, duplicate, partial overlap), severity, and affected dimensions
4. **Decision**: Approve, modify, or reject the candidate rule based on findings
5. **Report**: Formatted analysis with vendor, policy, candidate rule, and overlap results

## Workflow: Cross-Vendor Policy Audit

When auditing firewall rules across multiple platforms:

1. **Enumerate vendors**: `list_supported_vendors` — confirm supported platforms
2. **Parse each policy**: `parse_policy` for each vendor config — normalize all rules
3. **Cross-analyze**: For each rule in vendor A, use `analyze_firewall_rule_overlap` against vendor B's normalized rules
4. **Identify**: Cross-platform conflicts, redundant rules, shadowed entries
5. **Report**: Multi-vendor rule consistency analysis

## Workflow: Ruleset Hygiene Audit

When cleaning up an existing firewall policy:

1. **Parse policy**: `parse_policy` — normalize the full ruleset
2. **For each rule**: `analyze_firewall_rule_overlap` — check the rule against all others in the same policy
3. **Flag**: Shadowed rules (dead rules that never match), duplicates, and internal conflicts
4. **Report**: Cleanup recommendations with rule positions and overlap details

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `fmc-firewall-ops` | FMC policy search + fwrule overlap analysis on retrieved rules |
| `paloalto-panorama` | Panorama policy export + fwrule cross-policy analysis |
| `pyats-security` | Device ACL retrieval via pyATS + fwrule overlap detection |
| `pyats-asa-firewall` | ASA config retrieval + fwrule ASA parser for rule normalization |
| `fortimanager-ops` | FortiManager policy export + fwrule FortiOS parser for cross-VDOM analysis |
| `servicenow-change-workflow` | ServiceNow CR gating + fwrule validation before rule deployment |
| `github-ops` | Commit firewall rule change analysis results to Git |
| `gait-session-tracking` | Audit trail for all firewall rule analysis operations |

## Important Rules

- **Read-only analysis** — all 3 tools are pure analysis; no firewall modifications
- **No credentials required** — works entirely on config text/JSON input, no API connections to firewalls
- **Vendor parsers are best-effort** — use Mode 2 (normalized JSON) when parsers produce unexpected results
- **Record in GAIT** — log all firewall rule analysis for compliance audit trail
