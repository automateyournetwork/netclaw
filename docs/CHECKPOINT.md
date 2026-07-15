# Check Point Security Integration

NetClaw integrates with Check Point's enterprise security platform through 15 official MCP servers, providing AI-powered automation for firewall policies, threat intelligence, gateway diagnostics, SASE management, and malware analysis.

## Overview

| Feature | MCP Servers | Use Case |
|---------|-------------|----------|
| **Policy Management** | management, policy-insights | Audit rules, suggest optimizations |
| **Threat Intelligence** | reputation-service | IP/URL/file reputation lookups |
| **Gateway Diagnostics** | quantum-gw-cli, gw-connection-analysis | Health, performance, connection debug |
| **Threat Prevention** | threat-prevention | IPS, IOC feeds, profiles |
| **SASE** | harmony-sase | Cloud-delivered security |
| **Malware Analysis** | threat-emulation | Sandbox file analysis |
| **HTTPS Inspection** | https-inspection | SSL/TLS decryption policies |
| **GAIA OS** | quantum-gaia | OS-level management |
| **Documentation** | documentation | Check Point docs search |
| **Spark Firewall** | spark-management | MSP distributed firewalls |
| **CPInfo Analysis** | cpinfo-analysis | Diagnostic file analysis |
| **Exposure Management** | argos-erm | Risk scoring, alerts, assets |
| **Logs** | management-logs | Connection and audit logs |

## Quick Start

### Enable Integration

**New NetClaw installation:**
```bash
./scripts/install.sh
# Answer "y" to "Enable Check Point Security Integration?"
```

**Existing NetClaw installation:**
```bash
./scripts/checkpoint-enable.sh
```

### Configure Credentials

Add credentials to `~/.openclaw/.env`:

```bash
# Minimum setup (Management Server only)
CHKP_MGMT_HOST=192.168.1.100
CHKP_MGMT_API_KEY=your-api-key-here
CHKP_TELEMETRY_DISABLED=true
```

### Test the Integration

```bash
openclaw
> /checkpoint show my firewall policies
> /checkpoint check reputation of IP 8.8.8.8
```

## Credential Configuration

### Management Server (On-Premises)

Required for: policy, logs, threat prevention, https inspection, gateway, policy insights

```bash
CHKP_MGMT_HOST=192.168.1.100          # Management server IP/hostname
CHKP_MGMT_PORT=443                     # Web API port (default: 443)
CHKP_MGMT_API_KEY=your-api-key         # API key authentication (preferred)

# Alternative: username/password authentication
# CHKP_MGMT_USERNAME=admin
# CHKP_MGMT_PASSWORD=your-password

# For Multi-Domain Server (MDS) deployments
CHKP_MGMT_DOMAIN=domain-name
```

**To get an API key:**
1. Log into SmartConsole
2. Go to Manage & Settings > Blades > Management API
3. Enable API access
4. Create an API key for your user

### Smart-1 Cloud

Alternative to on-premises management:

```bash
CHKP_S1C_API_KEY=your-smart1-cloud-key
CHKP_S1C_URL=https://your-tenant.maas.checkpoint.com
```

### Reputation Service

For IP/URL/file threat intelligence:

```bash
CHKP_REPUTATION_API_KEY=your-reputation-key
```

**To get a Reputation API key:** Contact TCAPI_SUPPORT@checkpoint.com

### Harmony SASE

For cloud-delivered security:

```bash
CHKP_SASE_API_KEY=your-sase-api-key
CHKP_SASE_MGMT_HOST=https://api.us1.sase.checkpoint.com/api
CHKP_SASE_ORIGIN=https://your-tenant.sase.checkpoint.com
```

### Threat Emulation

For malware sandbox analysis:

```bash
CHKP_TE_API_KEY=your-threat-emulation-key
```

### Spark Management (MSP)

For distributed firewall management:

```bash
CHKP_SPARK_API_KEY=your-spark-api-key
```

### Argos ERM

For exposure and risk management:

```bash
CHKP_ARGOS_API_KEY=your-argos-api-key
```

### Global Settings

```bash
CHKP_TELEMETRY_DISABLED=true           # Disable Check Point telemetry
CHKP_LOG_LEVEL=standard                # minimal|standard|verbose
```

## Usage Examples

### Policy Audit (User Story 1)

```
/checkpoint show me all firewall policies
/checkpoint audit my policies for overly permissive rules
/checkpoint show all rules allowing any-any
/checkpoint suggest policy optimizations
/checkpoint show NAT rules for the DMZ policy
```

### Threat Intelligence (User Story 2)

```
/checkpoint check reputation of IP 185.220.101.1
/checkpoint is this URL malicious: http://suspicious.example.com
/checkpoint check file reputation for SHA256 abc123...
```

### Gateway Diagnostics (User Story 3)

```
/checkpoint show gateway health status
/checkpoint what's causing high CPU on the gateway
/checkpoint show interface statistics for eth0
/checkpoint show ClusterXL status
/checkpoint show performance overview
```

### Connection Debugging

```
/checkpoint debug why connection from 10.1.1.1 to 8.8.8.8 is failing
/checkpoint analyze dropped packets on the gateway
```

### Threat Prevention (User Story 4)

```
/checkpoint show threat prevention profiles
/checkpoint what IPS protections are available for CVE-2024-1234
/checkpoint show active IOC feeds
```

### SASE Management (User Story 5)

```
/checkpoint show all SASE regions
/checkpoint list applications in SASE policy
/checkpoint show SASE network configurations
```

### Malware Analysis (User Story 6)

```
/checkpoint analyze file with hash abc123...
/checkpoint get verdict for SHA256 xyz789...
```

### Documentation

```
/checkpoint how do I configure HTTPS inspection
/checkpoint what is ClusterXL
```

### Cross-Platform Queries (User Story 7)

```
/checkpoint cross-reference firewall rules with my CML lab topology
/checkpoint which Check Point rules affect traffic to devices in SuzieQ inventory
```

## MCP Server Details

### chkp-management

**Tools:** show-access-rulebase, show-nat-rulebase, show-hosts, show-networks, show-groups, show-gateways-and-servers, show-packages, show-simple-gateways

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY or USERNAME/PASSWORD

### chkp-management-logs

**Tools:** query-logs, show-logs-stats

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

### chkp-threat-prevention

**Tools:** show-threat-profiles, show-ips-protections, show-threat-indicators, show-threat-ioc-feeds

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

### chkp-reputation-service

**Tools:** query-ip-reputation, query-url-reputation, query-file-reputation

**Credentials:** CHKP_REPUTATION_API_KEY

### chkp-quantum-gw-cli

**Tools:** fw-stat, cphaprob-stat, show-interface, top-connections, cpview

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

### chkp-gw-connection-analysis

**Tools:** debug-connection, analyze-drops

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

### chkp-threat-emulation

**Tools:** submit-file, query-report, get-verdict

**Credentials:** CHKP_TE_API_KEY

### chkp-harmony-sase

**Tools:** list-sase-regions, list-sase-applications, show-sase-config, list-sase-networks

**Credentials:** CHKP_SASE_API_KEY, CHKP_SASE_MGMT_HOST, CHKP_SASE_ORIGIN

### chkp-quantum-gaia

**Tools:** show-interfaces, show-routes, show-arp

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

### chkp-https-inspection

**Tools:** show-https-rules, show-https-exceptions

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

### chkp-documentation

**Tools:** search-docs, get-article

**Credentials:** None required

### chkp-spark-management

**Tools:** list-spark-appliances, show-spark-policy, show-spark-status

**Credentials:** CHKP_SPARK_API_KEY

### chkp-cpinfo-analysis

**Tools:** analyze-cpinfo, extract-metrics

**Credentials:** None required (file-based)

### chkp-argos-erm

**Tools:** list-alerts, list-assets, query-threats, show-risk-score

**Credentials:** CHKP_ARGOS_API_KEY

### chkp-policy-insights

**Tools:** get-policy-insights, suggest-optimizations

**Credentials:** CHKP_MGMT_HOST, CHKP_MGMT_API_KEY

## Troubleshooting

### "MCP not configured" Error

Verify credentials are set:
```bash
cat ~/.openclaw/.env | grep CHKP
```

### "Authentication failed" Error

1. Verify API key is correct
2. Check network connectivity:
   ```bash
   curl -k https://$CHKP_MGMT_HOST:443/web_api/login
   ```
3. Ensure API access is enabled in SmartConsole

### "Connection refused" Error

1. Check firewall allows connection to management server
2. Verify management server IP/hostname is correct
3. Check port (default 443)

### "No Check Point MCPs available"

Re-run the enablement script:
```bash
./scripts/checkpoint-enable.sh
```

## Security Considerations

### Data Exposure

When using Check Point MCPs, queried security data (policies, logs, threat intelligence) is processed by the AI model. Ensure this aligns with your organization's data handling policies.

### Credential Storage

Credentials are stored in `~/.openclaw/.env` with file permissions limited to the current user. For production deployments, consider using a secrets manager.

### Telemetry

Check Point MCPs may send telemetry data. Set `CHKP_TELEMETRY_DISABLED=true` to disable.

### Logging

Control query logging with `CHKP_LOG_LEVEL`:
- `minimal` - Errors only
- `standard` - Queries and MCPs invoked (default)
- `verbose` - Full request/response logging

## Architecture

```
NetClaw (OpenClaw Agent)
    |
    |-- /checkpoint skill
    |       |
    |       |-- Query Router (keyword-based)
    |       |
    |       +-- MCP Servers (15 total)
    |               |
    |               |-- chkp-management ──────► Check Point Management API
    |               |-- chkp-reputation ──────► Reputation Cloud Service
    |               |-- chkp-harmony-sase ────► SASE API
    |               |-- chkp-threat-emulation ► TE Cloud API
    |               |-- chkp-documentation ───► Check Point Docs
    |               +-- ... (10 more)
```

## Resources

- **Check Point MCP Portal:** https://mcp.checkpoint.com/
- **GitHub Repository:** https://github.com/CheckPointSW/mcp-servers
- **NetClaw Skill:** workspace/skills/checkpoint/SKILL.md
- **Environment Variables:** .env.example

## Support

For Check Point API issues, contact Check Point support or your TAM.

For NetClaw integration issues, open an issue at https://github.com/automateyournetwork/netclaw/issues
