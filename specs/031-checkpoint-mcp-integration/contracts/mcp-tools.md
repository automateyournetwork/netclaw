# MCP Tools Contract: Check Point Integration

**Feature**: 031-checkpoint-mcp-integration
**Date**: 2026-06-14
**Source**: https://github.com/CheckPointSW/mcp-servers

## Overview

This document defines the tool inventory for all 15 Check Point MCP servers and their NetClaw configuration.

---

## 1. Quantum Management MCP

**Package**: `@chkp/quantum-management-mcp`
**Category**: Policy & Objects
**Credentials**: Management Server (mgmt) or Smart-1 Cloud (s1c)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `show-access-rulebase` | List access control rules | `policy-package`, `filter` |
| `show-nat-rulebase` | List NAT rules | `policy-package` |
| `show-hosts` | List host objects | `filter`, `limit` |
| `show-networks` | List network objects | `filter`, `limit` |
| `show-groups` | List group objects | `filter` |
| `show-gateways-and-servers` | List gateways and servers | `filter` |
| `show-packages` | List policy packages | - |
| `show-simple-gateways` | List simple gateway objects | - |

### NetClaw Configuration

```json
{
  "chkp-management": {
    "command": "npx",
    "args": ["@chkp/quantum-management-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 2. Management Logs MCP

**Package**: `@chkp/management-logs-mcp`
**Category**: Logs & Audit
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `query-logs` | Search connection and audit logs | `filter`, `time-frame`, `limit` |
| `show-logs-stats` | Get log statistics | `time-frame` |

### NetClaw Configuration

```json
{
  "chkp-management-logs": {
    "command": "npx",
    "args": ["@chkp/management-logs-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 3. Threat Prevention MCP

**Package**: `@chkp/threat-prevention-mcp`
**Category**: Threat Prevention
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `show-threat-profiles` | List threat prevention profiles | `filter` |
| `show-ips-protections` | List IPS protections | `filter`, `severity` |
| `show-threat-indicators` | List threat indicators | `filter` |
| `show-threat-ioc-feeds` | List IOC feed configurations | - |

### NetClaw Configuration

```json
{
  "chkp-threat-prevention": {
    "command": "npx",
    "args": ["@chkp/threat-prevention-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 4. HTTPS Inspection MCP

**Package**: `@chkp/https-inspection-mcp`
**Category**: HTTPS Inspection
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `show-https-rules` | List HTTPS inspection rules | `policy-package` |
| `show-https-exceptions` | List HTTPS bypass exceptions | - |

### NetClaw Configuration

```json
{
  "chkp-https-inspection": {
    "command": "npx",
    "args": ["@chkp/https-inspection-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 5. Harmony SASE MCP

**Package**: `@chkp/harmony-sase-mcp`
**Category**: SASE
**Credentials**: SASE (sase)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list-sase-regions` | List SASE regions | - |
| `list-sase-applications` | List defined applications | `filter` |
| `show-sase-config` | Show SASE configuration | - |
| `list-sase-networks` | List network configurations | - |

### NetClaw Configuration

```json
{
  "chkp-harmony-sase": {
    "command": "npx",
    "args": ["@chkp/harmony-sase-mcp"],
    "env": {
      "API_KEY": "${CHKP_SASE_API_KEY}",
      "MANAGEMENT_HOST": "${CHKP_SASE_MGMT_HOST}",
      "ORIGIN": "${CHKP_SASE_ORIGIN}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 6. Reputation Service MCP

**Package**: `@chkp/reputation-service-mcp`
**Category**: Threat Intelligence
**Credentials**: Reputation (reputation)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `query-ip-reputation` | Check IP reputation | `ip` |
| `query-url-reputation` | Check URL reputation | `url` |
| `query-file-reputation` | Check file hash reputation | `hash`, `hash-type` |

### NetClaw Configuration

```json
{
  "chkp-reputation-service": {
    "command": "npx",
    "args": ["@chkp/reputation-service-mcp"],
    "env": {
      "API_KEY": "${CHKP_REPUTATION_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 7. Quantum Gateway CLI MCP

**Package**: `@chkp/quantum-gw-cli-mcp`
**Category**: Gateway Diagnostics
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `fw-stat` | Firewall statistics | `gateway` |
| `cphaprob-stat` | ClusterXL status | `gateway` |
| `show-interface` | Interface statistics | `gateway`, `interface` |
| `top-connections` | Top connections | `gateway`, `limit` |
| `cpview` | Performance overview | `gateway` |

### NetClaw Configuration

```json
{
  "chkp-quantum-gw-cli": {
    "command": "npx",
    "args": ["@chkp/quantum-gw-cli-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 8. Gateway Connection Analysis MCP

**Package**: `@chkp/quantum-gw-connection-analysis-mcp`
**Category**: Connection Debug
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `debug-connection` | Debug specific connection | `src`, `dst`, `service`, `gateway` |
| `analyze-drops` | Analyze dropped packets | `gateway`, `time-frame` |

### NetClaw Configuration

```json
{
  "chkp-gw-connection-analysis": {
    "command": "npx",
    "args": ["@chkp/quantum-gw-connection-analysis-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 9. Threat Emulation MCP

**Package**: `@chkp/threat-emulation-mcp`
**Category**: Malware Analysis
**Credentials**: Threat Emulation (te)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `submit-file` | Submit file for analysis | `file-path` or `file-content` |
| `query-report` | Get analysis report | `report-id` |
| `get-verdict` | Get file verdict | `hash`, `hash-type` |

### NetClaw Configuration

```json
{
  "chkp-threat-emulation": {
    "command": "npx",
    "args": ["@chkp/threat-emulation-mcp"],
    "env": {
      "API_KEY": "${CHKP_TE_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 10. Quantum GAIA MCP

**Package**: `@chkp/quantum-gaia-mcp`
**Category**: GAIA OS
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `show-interfaces` | List GAIA interfaces | `gateway` |
| `show-routes` | Show routing table | `gateway` |
| `show-arp` | Show ARP table | `gateway` |

### NetClaw Configuration

```json
{
  "chkp-quantum-gaia": {
    "command": "npx",
    "args": ["@chkp/quantum-gaia-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 11. Documentation MCP

**Package**: `@chkp/documentation-mcp`
**Category**: Documentation
**Credentials**: None required

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search-docs` | Search documentation | `query` |
| `get-article` | Get specific article | `article-id` |

### NetClaw Configuration

```json
{
  "chkp-documentation": {
    "command": "npx",
    "args": ["@chkp/documentation-mcp"],
    "env": {
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 12. Spark Management MCP

**Package**: `@chkp/spark-management-mcp`
**Category**: Spark Firewall
**Credentials**: Spark (spark)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list-spark-appliances` | List Spark appliances | - |
| `show-spark-policy` | Show Spark policy | `appliance-id` |
| `show-spark-status` | Show appliance status | `appliance-id` |

### NetClaw Configuration

```json
{
  "chkp-spark-management": {
    "command": "npx",
    "args": ["@chkp/spark-management-mcp"],
    "env": {
      "API_KEY": "${CHKP_SPARK_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 13. CPInfo Analysis MCP

**Package**: `@chkp/cpinfo-analysis-mcp`
**Category**: CPInfo Diagnostics
**Credentials**: None required

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `analyze-cpinfo` | Analyze CPInfo file | `file-path` |
| `extract-metrics` | Extract specific metrics | `file-path`, `metric-type` |

### NetClaw Configuration

```json
{
  "chkp-cpinfo-analysis": {
    "command": "npx",
    "args": ["@chkp/cpinfo-analysis-mcp"],
    "env": {
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 14. Argos ERM MCP

**Package**: `@chkp/argos-erm-mcp`
**Category**: Exposure Management
**Credentials**: Argos (argos)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list-alerts` | List security alerts | `filter`, `severity` |
| `list-assets` | List monitored assets | `filter` |
| `query-threats` | Query threat intelligence | `query` |
| `show-risk-score` | Show organizational risk | - |

### NetClaw Configuration

```json
{
  "chkp-argos-erm": {
    "command": "npx",
    "args": ["@chkp/argos-erm-mcp"],
    "env": {
      "API_KEY": "${CHKP_ARGOS_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## 15. Policy Insights MCP

**Package**: `@chkp/policy-insights-mcp`
**Category**: Policy Optimization
**Credentials**: Management Server (mgmt)

### Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get-policy-insights` | Get policy optimization insights | `policy-package` |
| `suggest-optimizations` | Get optimization suggestions | `policy-package` |

### NetClaw Configuration

```json
{
  "chkp-policy-insights": {
    "command": "npx",
    "args": ["@chkp/policy-insights-mcp"],
    "env": {
      "MANAGEMENT_HOST": "${CHKP_MGMT_HOST}",
      "PORT": "${CHKP_MGMT_PORT:-443}",
      "API_KEY": "${CHKP_MGMT_API_KEY}",
      "TELEMETRY_DISABLED": "${CHKP_TELEMETRY_DISABLED:-true}"
    }
  }
}
```

---

## Summary: All 15 MCP Configurations

```json
{
  "mcpServers": {
    "chkp-management": { /* ... */ },
    "chkp-management-logs": { /* ... */ },
    "chkp-threat-prevention": { /* ... */ },
    "chkp-https-inspection": { /* ... */ },
    "chkp-harmony-sase": { /* ... */ },
    "chkp-reputation-service": { /* ... */ },
    "chkp-quantum-gw-cli": { /* ... */ },
    "chkp-gw-connection-analysis": { /* ... */ },
    "chkp-threat-emulation": { /* ... */ },
    "chkp-quantum-gaia": { /* ... */ },
    "chkp-documentation": { /* ... */ },
    "chkp-spark-management": { /* ... */ },
    "chkp-cpinfo-analysis": { /* ... */ },
    "chkp-argos-erm": { /* ... */ },
    "chkp-policy-insights": { /* ... */ }
  }
}
```
