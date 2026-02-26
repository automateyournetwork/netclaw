---
name: aws-network-ops
description: AWS cloud networking — VPC, Transit Gateway, Cloud WAN, VPN, Network Firewall, ENI, flow logs
version: 1.0.0
tags: [aws, vpc, transit-gateway, cloud-wan, vpn, network-firewall, flow-logs]
---

# AWS Network Operations

You have access to AWS cloud networking via the AWS Network MCP server. This is a **read-only** server with 27 tools for inspecting VPCs, Transit Gateways, Cloud WAN, VPN connections, Network Firewalls, and flow logs.

## MCP Server

- **Command**: `uvx awslabs.aws-network-mcp-server@latest` (stdio transport)
- **Requires**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
- **Read-only**: All operations are Describe/Get/List — no create/modify/delete

## Available Tools (27)

### General (3)

| Tool | What It Does |
|------|-------------|
| `get_path_trace_methodology` | Guidance for tracing network paths across AWS resources |
| `find_ip_address` | Find which VPC/subnet/ENI an IP address belongs to |
| `get_eni_details` | Get Elastic Network Interface details — security groups, subnet, routes |

### VPC (3)

| Tool | What It Does |
|------|-------------|
| `list_vpcs` | List all VPCs in the account/region |
| `get_vpc_network_details` | Full VPC details — subnets, route tables, IGW, NAT GW, endpoints, NACLs |
| `get_vpc_flow_logs` | Query VPC flow logs for traffic analysis |

### Transit Gateway (7)

| Tool | What It Does |
|------|-------------|
| `list_transit_gateways` | List all Transit Gateways |
| `get_tgw_details` | Transit Gateway details — attachments, route tables, associations |
| `get_tgw_routes` | Get routes from a specific TGW route table |
| `get_all_tgw_routes` | Get routes from all TGW route tables |
| `get_tgw_flow_logs` | Query Transit Gateway flow logs |
| `list_tgw_peerings` | List TGW peering connections |
| `detect_tgw_inspection` | Detect if traffic inspection is configured on a TGW |

### Cloud WAN (10)

| Tool | What It Does |
|------|-------------|
| `list_core_networks` | List all Cloud WAN core networks |
| `get_cloudwan_details` | Core network details — segments, policies, attachments |
| `get_cloudwan_routes` | Get routes from a Cloud WAN segment |
| `get_all_cloudwan_routes` | Get routes from all Cloud WAN segments |
| `get_cloudwan_attachment_details` | Details for a specific Cloud WAN attachment |
| `detect_cloudwan_inspection` | Detect inspection configuration on Cloud WAN |
| `list_cloudwan_peerings` | List Cloud WAN peering connections |
| `get_cloudwan_peering_details` | Details for a specific Cloud WAN peering |
| `get_cloudwan_logs` | Query Cloud WAN logs |
| `simulate_cloud_wan_route_change` | Simulate a route change and predict impact |

### VPN (1)

| Tool | What It Does |
|------|-------------|
| `list_vpn_connections` | List all site-to-site VPN connections with tunnel status |

### Network Firewall (3)

| Tool | What It Does |
|------|-------------|
| `list_network_firewalls` | List all AWS Network Firewalls |
| `get_firewall_rules` | Get firewall rule groups and policies |
| `get_network_firewall_flow_logs` | Query Network Firewall flow logs |

## Workflow: VPC Network Audit

When a user asks "show me our AWS network" or "audit the VPCs":

1. **List VPCs**: `list_vpcs` to see all VPCs in the region
2. **For each VPC**: `get_vpc_network_details` — subnets, route tables, gateways, NACLs
3. **Check TGW**: `list_transit_gateways` to see cross-VPC connectivity
4. **Check VPN**: `list_vpn_connections` for hybrid connectivity
5. **Check firewalls**: `list_network_firewalls` for security posture
6. **Report**: Formatted summary of the cloud network architecture

## Workflow: Troubleshoot Connectivity

When a user asks "why can't EC2 instance X reach Y?":

1. **Find the IPs**: `find_ip_address` for both source and destination
2. **Get ENI details**: `get_eni_details` to check security groups, subnet, routes
3. **Check route tables**: `get_vpc_network_details` to see routing
4. **Check flow logs**: `get_vpc_flow_logs` to see if traffic is being dropped
5. **Check firewalls**: `get_firewall_rules` if traffic crosses a Network Firewall
6. **Check TGW**: `get_tgw_routes` if traffic crosses Transit Gateway
7. **Report**: Root cause analysis with fix recommendation

## Workflow: Transit Gateway Health

When checking multi-VPC connectivity:

1. **List TGWs**: `list_transit_gateways`
2. **Get details**: `get_tgw_details` for attachments and route tables
3. **Check routes**: `get_all_tgw_routes` for route table completeness
4. **Check peerings**: `list_tgw_peerings` for cross-region/cross-account
5. **Check inspection**: `detect_tgw_inspection` for security posture
6. **Flow logs**: `get_tgw_flow_logs` for traffic analysis

## Workflow: VPN Tunnel Monitoring

When checking hybrid connectivity:

1. **List VPNs**: `list_vpn_connections`
2. **Check tunnel status**: Up/Down for each tunnel (redundancy check)
3. **Check routes**: TGW or VGW routes for the VPN prefixes
4. **Flow logs**: VPC flow logs for traffic across VPN
5. **Report**: VPN health summary with any down tunnels flagged

## Important Rules

- **Read-only** — this MCP cannot create, modify, or delete any AWS resources
- **Region-specific** — results are scoped to the configured AWS_REGION
- **IAM permissions required** — EC2 Describe, Network Manager, Network Firewall Describe, CloudWatch Logs
- **Record in GAIT** — log all AWS network investigations for audit trail

## Environment Variables

- `AWS_ACCESS_KEY_ID` — AWS access key
- `AWS_SECRET_ACCESS_KEY` — AWS secret key
- `AWS_REGION` — AWS region (e.g., us-east-1)
- Or `AWS_PROFILE` — Named AWS CLI profile
