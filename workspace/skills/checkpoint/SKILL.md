# Check Point Security Platform

A comprehensive skill for interacting with Check Point enterprise security infrastructure through 15 MCP servers.

## Activation

This skill activates when user queries involve:
- Check Point firewall policies, rules, or objects
- Security policy auditing or compliance
- Threat intelligence (IP/URL/file reputation)
- Gateway diagnostics and troubleshooting
- SASE management and cloud security
- Threat prevention profiles and IPS
- Malware analysis and file sandboxing
- Check Point documentation queries

**Explicit activation**: `/checkpoint` prefix

## MCP Servers

This skill composes across 15 Check Point MCP servers:

| Server | Purpose | Credentials |
|--------|---------|-------------|
| `chkp-management` | Policies, rules, objects, topology | MGMT server |
| `chkp-management-logs` | Connection and audit logs | MGMT server |
| `chkp-threat-prevention` | TP profiles, IPS, IOC feeds | MGMT server |
| `chkp-https-inspection` | HTTPS inspection policies | MGMT server |
| `chkp-harmony-sase` | SASE regions, applications | SASE API |
| `chkp-reputation-service` | IP/URL/file reputation | Reputation API |
| `chkp-quantum-gw-cli` | Gateway diagnostics | MGMT server |
| `chkp-gw-connection-analysis` | Connection debugging | MGMT server |
| `chkp-threat-emulation` | Malware analysis | TE API |
| `chkp-quantum-gaia` | GAIA OS management | MGMT server |
| `chkp-documentation` | Check Point docs search | None |
| `chkp-spark-management` | Spark firewall (MSP) | Spark API |
| `chkp-cpinfo-analysis` | CPInfo diagnostics | None |
| `chkp-argos-erm` | Exposure/risk management | Argos API |
| `chkp-policy-insights` | Policy optimization | MGMT server |

## Query Routing

### Policy & Object Queries (US1)
**Keywords**: policy, rule, firewall, access, NAT, object, host, network, group, audit, permissive, compliance
**MCP**: `chkp-management`, `chkp-policy-insights`

Examples:
- "show me all firewall policies"
- "audit my policies for overly permissive rules"
- "show all rules allowing any-any"
- "list host objects matching 10.1.*"
- "show NAT rules for the DMZ policy"
- "suggest policy optimizations"
- "show gateways and servers"

### Log Queries
**Keywords**: logs, audit, connection, history, traffic
**MCP**: `chkp-management-logs`

Examples:
- "show recent connection logs"
- "query audit logs for the last hour"
- "show log statistics"

### Threat Intelligence (US2)
**Keywords**: reputation, malicious, suspicious, threat, IP, URL, hash, file, indicator
**MCP**: `chkp-reputation-service`

Examples:
- "check reputation of IP 185.220.101.1"
- "is this URL malicious: http://example.com/suspicious"
- "check file reputation for SHA256 abc123..."
- "what's the risk score for IP 8.8.8.8"

### Gateway Diagnostics (US3)
**Keywords**: gateway, health, CPU, memory, interface, performance, status, cluster, HA
**MCP**: `chkp-quantum-gw-cli`

**Gateway Selection**: When multiple gateways are configured, the skill uses the first configured gateway by default. Users can specify a different gateway in their query (e.g., "show health for gateway fw-london").

Examples:
- "show gateway health status"
- "what's causing high CPU on the gateway"
- "show interface statistics for eth0"
- "show top connections"
- "show ClusterXL status"
- "show performance overview"

### Connection Debugging
**Keywords**: debug, connection, failing, drops, blocked, troubleshoot, traffic
**MCP**: `chkp-gw-connection-analysis`

Examples:
- "debug why connection from 10.1.1.1 to 8.8.8.8 is failing"
- "analyze dropped packets on the gateway"
- "why is traffic being blocked to port 443"

### Threat Prevention (US4)
**Keywords**: threat, IPS, protection, CVE, IOC, feed, profile, signature
**MCP**: `chkp-threat-prevention`

Examples:
- "show threat prevention profiles"
- "what IPS protections are available for CVE-2024-1234"
- "show active IOC feeds and their status"
- "show threat indicators"

### SASE Management (US5)
**Keywords**: SASE, harmony, cloud, region, application, distributed
**MCP**: `chkp-harmony-sase`

Examples:
- "show all SASE regions"
- "list applications in SASE policy"
- "show SASE network configurations"
- "show SASE configuration status"

### Malware Analysis (US6)
**Keywords**: analyze, file, malware, sandbox, emulation, verdict, suspicious
**MCP**: `chkp-threat-emulation`

Examples:
- "analyze file with hash abc123..."
- "submit file for malware analysis"
- "get verdict for SHA256 xyz789..."
- "show analysis report for submission ID 12345"

### HTTPS Inspection
**Keywords**: HTTPS, SSL, inspection, decryption, certificate, bypass
**MCP**: `chkp-https-inspection`

Examples:
- "show HTTPS inspection rules"
- "show HTTPS bypass exceptions"
- "how is SSL decryption configured"

### GAIA OS
**Keywords**: GAIA, route, ARP, interface, OS, routing, table
**MCP**: `chkp-quantum-gaia`

Examples:
- "show GAIA interfaces"
- "show routing table"
- "show ARP table"

### Documentation
**Keywords**: docs, documentation, how, guide, reference, what is, configure, setup
**MCP**: `chkp-documentation`

Examples:
- "how do I configure HTTPS inspection"
- "what is ClusterXL"
- "show documentation for SmartConsole"
- "how to set up VPN"

### Spark Firewall (MSP)
**Keywords**: Spark, MSP, appliance, distributed, SMB
**MCP**: `chkp-spark-management`

Examples:
- "list Spark appliances"
- "show Spark policy for appliance X"
- "show Spark appliance status"

### CPInfo Diagnostics
**Keywords**: CPInfo, diagnostic, support, health check, dump
**MCP**: `chkp-cpinfo-analysis`

Examples:
- "analyze CPInfo file from /path/to/cpinfo.tgz"
- "extract metrics from CPInfo"

### Exposure/Risk Management
**Keywords**: exposure, risk, vulnerability, alert, asset, ERM
**MCP**: `chkp-argos-erm`

Examples:
- "show security alerts"
- "list monitored assets"
- "query threats for my organization"
- "show organizational risk score"

## Cross-Platform Composition (US7)

This skill can compose with other NetClaw skills for advanced queries:

### Check Point + CML
- "cross-reference firewall rules with my CML lab topology"
- "which Check Point rules would affect traffic in my lab"

### Check Point + SuzieQ
- "which Check Point rules affect traffic to devices in SuzieQ inventory"
- "compare firewall policies with network paths from SuzieQ"

### Check Point + Batfish
- "validate Check Point policies against Batfish reachability analysis"
- "check for policy conflicts using Batfish"

## Logging Configuration

Query logging is controlled by the `CHKP_LOG_LEVEL` environment variable:

| Level | Behavior |
|-------|----------|
| `minimal` | Log errors only |
| `standard` | Log queries and MCPs invoked (default) |
| `verbose` | Log queries, MCPs, and response summaries |

## Error Handling

### MCP Not Configured
If a required MCP is not configured, the skill reports which credentials are missing and provides setup guidance.

### Authentication Failures
For auth failures, the skill suggests verifying:
1. API key or username/password is correct
2. Management server is reachable
3. User has API access permissions

### Partial Configuration
The skill works with partial configurations. If only Management Server credentials are set, policy and gateway queries work but SASE and Reputation queries will indicate those MCPs are unavailable.

## Credential Reference

All credentials are stored in `~/.openclaw/.env` with the `CHKP_` prefix:

```bash
# Management Server (on-prem)
CHKP_MGMT_HOST=192.168.1.100
CHKP_MGMT_PORT=443
CHKP_MGMT_API_KEY=your-api-key
# OR username/password:
# CHKP_MGMT_USERNAME=admin
# CHKP_MGMT_PASSWORD=your-password
CHKP_MGMT_DOMAIN=                    # For MDS only

# Smart-1 Cloud (alternative)
# CHKP_S1C_API_KEY=your-s1c-key
# CHKP_S1C_URL=https://tenant.maas.checkpoint.com

# Harmony SASE
CHKP_SASE_API_KEY=your-sase-key
CHKP_SASE_MGMT_HOST=https://api.us1.sase.checkpoint.com/api
CHKP_SASE_ORIGIN=https://tenant.sase.checkpoint.com

# Reputation Service
CHKP_REPUTATION_API_KEY=your-reputation-key

# Threat Emulation
CHKP_TE_API_KEY=your-te-key

# Spark (MSP)
CHKP_SPARK_API_KEY=your-spark-key

# Argos ERM
CHKP_ARGOS_API_KEY=your-argos-key

# Global
CHKP_TELEMETRY_DISABLED=true
CHKP_LOG_LEVEL=standard
```

## Quick Start

1. Enable Check Point integration:
   ```bash
   ./scripts/checkpoint-enable.sh
   ```

2. Configure minimum credentials in `~/.openclaw/.env`:
   ```bash
   CHKP_MGMT_HOST=192.168.1.100
   CHKP_MGMT_API_KEY=your-api-key
   CHKP_TELEMETRY_DISABLED=true
   ```

3. Test the skill:
   ```bash
   openclaw
   > /checkpoint show my firewall policies
   > /checkpoint check reputation of IP 8.8.8.8
   ```

## See Also

- [docs/CHECKPOINT.md](../../../docs/CHECKPOINT.md) - Detailed integration guide
- [.env.example](../../../.env.example) - All environment variable documentation
- https://mcp.checkpoint.com/ - Official Check Point MCP portal
