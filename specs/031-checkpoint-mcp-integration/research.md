# Research: Check Point MCP Integration

**Date**: 2026-06-14
**Feature**: 031-checkpoint-mcp-integration

## Research Tasks Completed

1. ✅ Check Point MCP Environment Variables
2. ✅ MCP Tool Inventory
3. ✅ Query Routing Patterns
4. ✅ Existing Install.sh Pattern

---

## 1. Environment Variables by MCP Server

### Credential Groups

Based on research, Check Point MCPs share credentials by product family:

| Group | MCPs Using | Variables |
|-------|-----------|-----------|
| **Management** | quantum-management, management-logs, threat-prevention, https-inspection, policy-insights | `MANAGEMENT_HOST`, `PORT`, `API_KEY` or `USERNAME`/`PASSWORD` |
| **Smart-1 Cloud** | quantum-management, gw-cli (alternate) | `API_KEY`, `S1C_URL` |
| **SASE** | harmony-sase | `API_KEY`, `MANAGEMENT_HOST`, `ORIGIN` |
| **Gateway** | quantum-gw-cli, quantum-gw-connection-analysis, quantum-gaia | Same as Management (accesses gateways via mgmt) |
| **Reputation** | reputation-service | `API_KEY` (dedicated key from TCAPI_SUPPORT@checkpoint.com) |
| **Threat Emulation** | threat-emulation | `API_KEY` (TE-specific key) |
| **Spark** | spark-management | `API_KEY` (Spark-specific) |
| **Argos ERM** | argos-erm | `API_KEY` (Argos-specific) |
| **None** | documentation, cpinfo-analysis | No credentials required |

### NetClaw Environment Variable Mapping

**Decision**: Use `CHKP_` prefix for all variables to namespace them clearly.

```bash
# Management Server (on-premises or Smart-1 Cloud)
CHKP_MGMT_HOST=           # IP/hostname of management server
CHKP_MGMT_PORT=443        # Optional, default 443
CHKP_MGMT_API_KEY=        # API key auth (preferred)
CHKP_MGMT_USERNAME=       # Alternative: username/password
CHKP_MGMT_PASSWORD=       # Alternative: username/password
CHKP_MGMT_DOMAIN=         # Optional: domain for MDS

# Smart-1 Cloud (alternative to on-prem)
CHKP_S1C_API_KEY=         # Smart-1 Cloud API key
CHKP_S1C_URL=             # Smart-1 Cloud Web-API URL

# SASE
CHKP_SASE_API_KEY=        # Harmony SASE API key
CHKP_SASE_MGMT_HOST=      # SASE management API endpoint
CHKP_SASE_ORIGIN=         # SASE origin domain

# Reputation Service
CHKP_REPUTATION_API_KEY=  # From TCAPI_SUPPORT@checkpoint.com

# Threat Emulation
CHKP_TE_API_KEY=          # Threat Emulation API key

# Spark (MSP)
CHKP_SPARK_API_KEY=       # Spark Management API key

# Argos ERM
CHKP_ARGOS_API_KEY=       # Argos ERM API key

# Global Settings
CHKP_TELEMETRY_DISABLED=true  # Disable Check Point telemetry
CHKP_LOG_LEVEL=standard       # minimal|standard|verbose (per clarification)
```

**Rationale**: Prefixing with `CHKP_` prevents collision with other integrations and makes Check Point variables easily identifiable in `.env` files.

**Alternatives Considered**:
- Using Check Point's native variable names (rejected: inconsistent across MCPs)
- Single credential set for all MCPs (rejected: different products require different API keys)

---

## 2. MCP Tool Inventory

### Tools by Server (from Check Point documentation)

| MCP Server | Primary Tools | Category |
|------------|--------------|----------|
| **quantum-management-mcp** | show-access-rulebase, show-nat-rulebase, show-hosts, show-networks, show-groups, show-gateways-and-servers | Policy & Objects |
| **management-logs-mcp** | query-logs, show-logs-stats | Logs & Audit |
| **threat-prevention-mcp** | show-threat-profiles, show-ips-protections, show-threat-indicators | Threat Prevention |
| **https-inspection-mcp** | show-https-rules, show-https-exceptions | HTTPS Inspection |
| **harmony-sase-mcp** | list-sase-regions, list-sase-applications, show-sase-config | SASE |
| **reputation-service-mcp** | query-ip-reputation, query-url-reputation, query-file-reputation | Threat Intelligence |
| **quantum-gw-cli-mcp** | fw-stat, cphaprob-stat, show-interface, top-connections | Gateway Diagnostics |
| **quantum-gw-connection-analysis-mcp** | debug-connection, analyze-drops | Connection Debug |
| **threat-emulation-mcp** | submit-file, query-report, get-verdict | Malware Analysis |
| **quantum-gaia-mcp** | show-interfaces, show-routes, show-arp | GAIA OS |
| **documentation-mcp** | search-docs, get-article | Documentation |
| **spark-management-mcp** | list-spark-appliances, show-spark-policy | Spark Firewall |
| **cpinfo-analysis-mcp** | analyze-cpinfo, extract-metrics | CPInfo Diagnostics |
| **argos-erm-mcp** | list-alerts, list-assets, query-threats | Exposure Management |
| **policy-insights-mcp** | get-policy-insights, suggest-optimizations | Policy Optimization |

**Decision**: Document complete tool inventory in contracts/mcp-tools.md during Phase 1.

---

## 3. Query Routing Patterns

### Natural Language → MCP Mapping

| Query Pattern | Primary MCP(s) | Keywords |
|---------------|---------------|----------|
| "show policies", "audit rules", "firewall rules" | quantum-management + policy-insights | policy, rule, firewall, audit, permissive |
| "check reputation", "is this IP malicious" | reputation-service | reputation, malicious, suspicious, IP, URL, hash |
| "gateway health", "CPU usage", "interface status" | quantum-gw-cli | gateway, health, CPU, memory, interface, performance |
| "connection failing", "debug traffic" | quantum-gw-connection-analysis | connection, debug, failing, drops, blocked |
| "threat prevention", "IPS", "IOC" | threat-prevention | threat, IPS, protection, CVE, IOC |
| "analyze file", "malware check" | threat-emulation | analyze, file, malware, sandbox, emulation |
| "SASE regions", "cloud security" | harmony-sase | SASE, harmony, cloud, region, application |
| "HTTPS inspection", "SSL decryption" | https-inspection | HTTPS, SSL, inspection, decryption, certificate |
| "GAIA", "OS config", "routing table" | quantum-gaia | GAIA, route, ARP, interface, OS |
| "documentation", "how to", "what is" | documentation | docs, documentation, how, guide, reference |
| "Spark firewall", "MSP appliance" | spark-management | Spark, MSP, appliance, distributed |
| "CPInfo", "diagnostic file" | cpinfo-analysis | CPInfo, diagnostic, support, health check |
| "exposure", "risk", "vulnerability" | argos-erm | exposure, risk, vulnerability, alert, asset |
| "connection logs", "audit trail" | management-logs | logs, audit, connection, history |

**Decision**: Implement keyword-based routing with fallback to documentation MCP for unknown queries.

**Rationale**: Keyword matching is simple, deterministic, and aligns with how users naturally describe Check Point operations.

---

## 4. Install.sh Integration Pattern

### Existing Pattern Analysis

Current install.sh structure:
- 55 total steps
- Uses `log_step`, `log_info`, `log_warn`, `log_error` functions
- Interactive prompts with `read -r -p`
- Modular with clone_or_pull for git repos
- Prerequisites check at step 1

### Integration Point

**Decision**: Add Check Point integration as steps 48-50 (before final configuration steps).

```bash
# ═══════════════════════════════════════════
# Step 48: Check Point Security Integration
# ═══════════════════════════════════════════

log_step "48/$TOTAL_STEPS Check Point Security Integration..."

read -r -p "Enable Check Point Security Integration? [y/N] " enable_checkpoint
if [[ "$enable_checkpoint" =~ ^[Yy]$ ]]; then
    # Prompt for credentials or skip
    # Add MCP configs to openclaw.json
    # Update .env with CHKP_* variables
fi
```

**Rationale**: Placing near the end allows all prerequisites (Node.js, npm) to be verified first.

**Alternatives Considered**:
- Separate install script only (rejected: new users miss the option)
- Early in install process (rejected: prerequisites not yet verified)

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Environment variable prefix | `CHKP_*` | Clear namespacing, avoids collisions |
| Credential grouping | By product family | Matches Check Point API architecture |
| Query routing | Keyword-based matching | Simple, deterministic, user-friendly |
| Install.sh integration | Steps 48-50 | After prerequisites, before final config |
| Default gateway targeting | First configured | Per clarification session |
| Logging level | Configurable via env var | Per clarification session |

---

## Open Items for Phase 1

1. Create full tool inventory with parameters (contracts/mcp-tools.md)
2. Define MCP configuration JSON schema (data-model.md)
3. Write quickstart guide with verification steps (quickstart.md)
