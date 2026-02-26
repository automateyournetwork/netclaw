---
name: aws-architecture-diagram
description: AWS architecture diagrams — generate visual network topology diagrams from live AWS infrastructure
version: 1.0.0
tags: [aws, diagram, architecture, visualization, topology]
---

# AWS Architecture Diagram

Generate visual architecture diagrams of AWS infrastructure using the AWS Diagram MCP server — automatically discover and render VPCs, subnets, Transit Gateways, load balancers, and network connections.

## MCP Server

- **Command**: `uvx awslabs.aws-diagram-mcp-server@latest` (stdio transport)
- **Requires**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
- **Dependency**: Requires `graphviz` installed on the system (`apt install graphviz` or `brew install graphviz`)

## Key Capabilities

- **Auto-discovery**: Scan AWS account and render infrastructure as a diagram
- **Network topology**: VPCs, subnets, route tables, IGW, NAT GW, TGW connections
- **Service mapping**: EC2, ELB, RDS, Lambda placed in their VPC/subnet context
- **Multiple formats**: PNG, SVG, PDF output
- **Filtered views**: Scope diagram to specific VPCs, services, or tags

## Workflow: Network Architecture Diagram

When a user asks "draw our AWS network" or "show me the architecture":

1. **Generate diagram**: Use diagram tool scoped to networking resources
2. **Include**: VPCs, subnets (public/private), IGW, NAT GW, TGW, VPN, peering connections
3. **Label**: CIDR blocks, subnet names, AZ placement
4. **Connections**: Show routing paths — TGW attachments, peering links, VPN tunnels
5. **Output**: PNG or SVG file for sharing in Slack or documentation
6. **Report**: Architecture summary alongside the diagram

## Workflow: VPC Detail Diagram

When focusing on a specific VPC:

1. **Scope to VPC**: Filter diagram to one VPC by ID or tag
2. **Show subnets**: Public, private, isolated — grouped by AZ
3. **Show route tables**: Main and custom route tables with key routes
4. **Show gateways**: IGW, NAT GW, VPC endpoints
5. **Show security**: NACLs, security group relationships
6. **Output**: Detailed VPC topology diagram

## Workflow: Multi-Account Network Diagram

When documenting cross-account architecture:

1. **Hub-spoke topology**: Show Transit Gateway as the hub
2. **VPC attachments**: Each spoke VPC with its CIDR and purpose
3. **Route propagation**: Show which routes propagate where
4. **VPN/DX**: On-premises connections via VPN or Direct Connect
5. **Inspection VPC**: Network Firewall placement if applicable
6. **Output**: Enterprise network topology diagram

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `aws-network-ops` | Discover VPCs/TGWs first, then diagram them |
| `aws-cloud-monitoring` | Add CloudWatch metrics annotations to diagram |
| `aws-cost-ops` | Annotate diagram with cost per resource |
| `markmap-viz` | Generate mindmap alternative for simpler overviews |

## Diagram Scoping Tips

| Scope | When To Use |
|-------|------------|
| Full account | Initial architecture review or documentation |
| Single VPC | Troubleshooting or VPC-specific audit |
| TGW + attachments | Multi-VPC connectivity review |
| Subnet-level | Security audit or routing investigation |
| Tagged resources | Application-specific or team-specific views |

## Important Rules

- **Graphviz required** — the MCP server generates Graphviz DOT files and renders them; `graphviz` must be installed
- **Large accounts may produce complex diagrams** — scope with filters for clarity
- **Region-specific** — diagram shows resources in the configured AWS_REGION only
- **Read-only** — only discovers and renders, never modifies resources
- **Record in GAIT** — log diagram generation for audit trail

## Environment Variables

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
