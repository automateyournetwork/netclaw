---
name: azure-security-audit
description: "Azure NSG compliance auditing and security posture assessment. CIS Azure Foundations Benchmark rules, effective security rule analysis, orphaned NSG detection. Use when auditing Azure NSGs for CIS compliance, checking for overly permissive rules, or reviewing effective security on NICs."
version: 1.0.0
license: Apache-2.0
tags: [azure, nsg, security, compliance, cis-benchmark, audit]
---

# Azure Security Audit

## MCP Server

- **Server**: azure-network-mcp (shared with azure-network-ops)
- **Command**: `python mcp-servers/azure-network-mcp/azure_network_mcp_server.py` (stdio transport)
- **Requires**: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`
- **Read-only**: All operations are observation-only

## Relevant Tools

### Primary Audit Tools

| Tool | What It Does |
|------|-------------|
| `azure_audit_nsg_compliance` | Run CIS Azure Foundations Benchmark against all or specific NSGs |
| `azure_list_nsgs` | List all NSGs with orphan detection (no subnet/NIC associations) |
| `azure_get_nsg_rules` | Full rule list sorted by priority for a specific NSG |
| `azure_get_effective_security_rules` | Effective aggregated rules on a NIC (all NSGs combined) |

### Supporting Context Tools

| Tool | What It Does |
|------|-------------|
| `azure_get_network_watcher_status` | Flow log configuration and retention checks |
| `azure_get_vnet_details` | Subnet-to-NSG associations for VNet topology context |
| `azure_list_firewalls` | Azure Firewall policies for layered security context |

## CIS Azure Foundations Benchmark Rules

The compliance audit checks these rules from the CIS Azure Foundations Benchmark:

| Rule | Severity | What It Checks |
|------|----------|----------------|
| 6.1 | Critical | RDP (port 3389) not open to 0.0.0.0/0 from internet |
| 6.2 | Critical | SSH (port 22) not open to 0.0.0.0/0 from internet |
| 6.3 | High | No unrestricted UDP (all ports) from internet |
| 6.4 | Medium | NSG flow logs enabled with >= 90 day retention |

## Workflow: Full NSG Compliance Audit

When asked "audit NSG compliance" or "check Azure security posture":

1. **Discover**: `azure_list_nsgs` -- get all NSGs, note orphaned ones
2. **Audit**: `azure_audit_nsg_compliance` -- run CIS checks against all NSGs
3. **Deep dive**: For each Critical/High finding:
   - `azure_get_nsg_rules` -- review the full rule set for context
   - Identify which subnets/NICs are affected via associations
4. **Effective rules**: For critical NICs:
   - `azure_get_effective_security_rules` -- verify aggregated effective rules
5. **Flow logs**: `azure_get_network_watcher_status` -- check flow log coverage
6. **Report**: Summarize by severity, list affected resources, provide remediation steps

## Workflow: Incident Response -- Suspicious Access

When investigating a potential security incident:

1. `azure_get_effective_security_rules` for the target NIC -- what traffic is allowed?
2. `azure_get_nsg_rules` for each associated NSG -- which specific rules permit traffic?
3. `azure_audit_nsg_compliance` on the specific NSG -- any known compliance gaps?
4. `azure_get_network_watcher_status` -- check if flow logs captured the traffic
5. Cross-reference with azure-network-ops VNet tools for full topology context

## Integration with azure-network-ops

This skill uses tools from the same azure-network-mcp server as azure-network-ops. The skills are complementary:

- **azure-network-ops**: Broad network topology, connectivity, and health monitoring
- **azure-security-audit**: Focused NSG compliance, security rule analysis, and posture assessment

Use both together for a complete Azure networking and security picture.

## Important Rules

- **Read-only**: Never modify NSG rules, flow logs, or any Azure resources
- **Severity prioritization**: Always report Critical findings first, then High, Medium, Low
- **Remediation guidance**: Include specific remediation steps for every finding
- **GAIT logging**: All audit operations are logged for compliance trail
- **Subscription scope**: Audit can cover all NSGs or filter by specific NSG/resource group
