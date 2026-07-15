---
name: azure-network-ops
description: "Azure cloud networking -- VNets, NSGs, ExpressRoute, VPN Gateways, Azure Firewalls, Load Balancers, Application Gateways, Route Tables, Network Watcher, Private Endpoints, DNS zones. Use when auditing Azure VNets, troubleshooting hybrid connectivity (ExpressRoute/VPN), checking NSG rules, inspecting firewall policies, or analyzing load balancer health."
version: 1.0.0
license: Apache-2.0
tags: [azure, vnet, nsg, expressroute, vpn, firewall, load-balancer, dns, private-link]
---

# Azure Network Operations

## MCP Server

- **Command**: `python mcp-servers/azure-network-mcp/azure_network_mcp_server.py` (stdio transport)
- **Requires**: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`
- **Read-only**: All operations are List/Get -- no create/modify/delete
- **Auth**: DefaultAzureCredential (service principal or Azure CLI fallback)

## Available Tools (19)

### Subscription (1)

| Tool | What It Does |
|------|-------------|
| `azure_list_subscriptions` | List all accessible Azure subscriptions |

### VNet Topology (3)

| Tool | What It Does |
|------|-------------|
| `azure_list_vnets` | List all VNets with address space, subnet/peering count |
| `azure_get_vnet_details` | Full VNet details: subnets (NSG, route table, delegations), peerings, DNS |
| `azure_get_vnet_peerings` | VNet peering status with traffic forwarding settings |

### NSG Security (3)

| Tool | What It Does |
|------|-------------|
| `azure_list_nsgs` | List all NSGs with association info and orphan detection |
| `azure_get_nsg_rules` | All rules (custom + default) sorted by priority |
| `azure_get_effective_security_rules` | Effective aggregated rules for a NIC |

### Compliance (1)

| Tool | What It Does |
|------|-------------|
| `azure_audit_nsg_compliance` | CIS Azure Foundations Benchmark audit (rules 6.1-6.4) |

### ExpressRoute (2)

| Tool | What It Does |
|------|-------------|
| `azure_get_expressroute_status` | Circuit status, peering config, provisioning state |
| `azure_get_expressroute_routes` | Learned route table for a peering |

### VPN Gateway (1)

| Tool | What It Does |
|------|-------------|
| `azure_get_vpn_gateway_status` | Gateway config, connections, BGP settings |

### Firewall (2)

| Tool | What It Does |
|------|-------------|
| `azure_list_firewalls` | List Azure Firewalls with SKU and policy association |
| `azure_get_firewall_policy` | Policy details: rule collections, threat intel, IDPS |

### Load Balancer (2)

| Tool | What It Does |
|------|-------------|
| `azure_list_load_balancers` | List LBs with frontend/backend/probe summary |
| `azure_get_lb_backend_health` | Backend pool health per member |

### Application Gateway / Front Door (1)

| Tool | What It Does |
|------|-------------|
| `azure_get_app_gateway_health` | App GW config, WAF, backend health; Front Door routing |

### Supporting Services (3)

| Tool | What It Does |
|------|-------------|
| `azure_get_route_tables` | Route tables, UDRs, effective routes for a NIC |
| `azure_get_network_watcher_status` | Network Watcher availability, connection monitors, flow logs |
| `azure_get_private_endpoints` | Private Endpoints with DNS zone associations |
| `azure_get_dns_zones` | DNS zones (public/private) and record sets |

## Workflow: VNet Topology Audit

When asked "show me our Azure network" or "audit Azure VNets":

1. `azure_list_subscriptions` -- discover available subscriptions
2. `azure_list_vnets` -- get all VNets in the target subscription
3. For each VNet: `azure_get_vnet_details` -- subnets, peerings, DNS, NSGs
4. `azure_get_vnet_peerings` -- check peering state (Connected/Disconnected)
5. Report: VNet count, subnet utilization, peering health, orphaned NSGs

## Workflow: Hybrid Connectivity Check

When asked "check ExpressRoute status" or "is the VPN tunnel up":

1. `azure_get_expressroute_status` -- circuit provisioning, peering state
2. `azure_get_expressroute_routes` -- verify learned routes from on-prem
3. `azure_get_vpn_gateway_status` -- VPN connection status, BGP peers
4. Report: circuit health, learned route count, tunnel status, bytes transferred

## Workflow: Security Posture Assessment

When asked "audit NSG rules" or "check security posture":

1. `azure_audit_nsg_compliance` -- run CIS benchmark against all NSGs
2. `azure_list_nsgs` -- identify orphaned NSGs
3. For flagged NSGs: `azure_get_nsg_rules` -- review offending rules
4. `azure_get_effective_security_rules` -- verify effective rules on critical NICs
5. Report: findings by severity, remediation steps, orphan count

## Important Rules

- **Read-only**: Never attempt to create, modify, or delete Azure resources
- **Subscription-scoped**: Always specify or use default subscription_id
- **GAIT logging**: All tool calls are audit-logged with timestamp, operation, and result
- **Multi-subscription**: Pass subscription_id to query across subscriptions
- **Rate limits**: Azure ARM allows ~1200 reads/5min per tenant; server auto-retries on 429

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_TENANT_ID` | Yes | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Yes | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Yes | Service principal secret |
| `AZURE_SUBSCRIPTION_ID` | Yes | Default subscription |
