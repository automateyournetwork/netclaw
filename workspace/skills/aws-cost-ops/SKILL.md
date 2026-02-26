---
name: aws-cost-ops
description: AWS Cost Explorer — spending analysis, service breakdowns, forecasts, cost anomalies
version: 1.0.0
tags: [aws, cost-explorer, billing, finops, cost-optimization]
---

# AWS Cost Operations

Analyze AWS spending via the Cost Explorer MCP server — break down costs by service, track trends, identify anomalies, and forecast future spend.

## MCP Server

- **Command**: `uvx awslabs.cost-explorer-mcp-server@latest` (stdio transport)
- **Requires**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
- **Note**: Cost Explorer API charges $0.01 per request — be mindful of query volume

## Key Capabilities

- **Cost breakdown**: Spending by service, account, region, or tag
- **Time series**: Daily, monthly, or custom date range cost trends
- **Forecasts**: Predicted spend based on historical patterns
- **Anomaly detection**: Unusual spending spikes
- **Filtering**: Narrow by service (EC2, VPC, TGW, NAT GW, VPN, etc.)

## Workflow: Network Cost Analysis

When a user asks "how much is our AWS network costing?":

1. **Total network spend**: Cost breakdown for VPC, Transit Gateway, NAT Gateway, VPN, ELB, Direct Connect
2. **Trend**: Monthly trend for network services over last 6 months
3. **Top services**: Rank network services by spend (NAT GW data processing is often #1)
4. **Per-region**: Break down network costs by region
5. **Forecast**: Projected network spend for next month
6. **Report**: Network cost dashboard with optimization recommendations

## Workflow: Cost Anomaly Investigation

When investigating unexpected charges:

1. **Daily breakdown**: Get daily costs for the spike period
2. **Service drill-down**: Which service caused the spike?
3. **Region check**: Was the spike in a specific region?
4. **Correlate**: Cross-reference with CloudTrail for resource creation events
5. **Report**: Root cause and recommended action

## Workflow: Monthly Cost Review

For regular FinOps review:

1. **Month-over-month**: Compare current vs previous month spending
2. **Service breakdown**: Top 10 services by cost
3. **Network focus**: VPC, TGW, NAT GW, VPN, ELB, Direct Connect costs
4. **Growth rate**: Percentage change per service
5. **Forecast**: Next month projection
6. **Report**: Executive cost summary with trends

## Common AWS Network Cost Drivers

| Service | Cost Component | Typical Driver |
|---------|---------------|----------------|
| NAT Gateway | Data processing | $0.045/GB — largest network cost for most |
| NAT Gateway | Hourly charge | $0.045/hr per NAT GW |
| Transit Gateway | Data processing | $0.02/GB per attachment |
| Transit Gateway | Hourly charge | $0.05/hr per attachment |
| VPN | Hourly charge | $0.05/hr per VPN connection |
| VPN | Data transfer | $0.09/GB outbound |
| ELB (ALB) | Hourly + LCU | $0.0225/hr + LCU charges |
| ELB (NLB) | Hourly + NLCU | $0.0225/hr + NLCU charges |
| Direct Connect | Port hours | $0.03-$0.30/hr depending on speed |
| Data Transfer | Cross-AZ | $0.01/GB each direction |
| Data Transfer | Cross-Region | $0.02/GB |
| Data Transfer | Internet out | $0.09/GB (first 10TB) |

## Cost Optimization Tips

| Finding | Recommendation |
|---------|---------------|
| High NAT GW data processing | Use VPC endpoints for S3/DynamoDB (free) |
| Multiple NAT GWs per AZ | Consolidate if traffic allows |
| Idle VPN connections | Delete unused VPN tunnels |
| Cross-AZ traffic | Co-locate resources in same AZ where possible |
| Oversized ELB | Right-size based on actual LCU/NLCU usage |
| Unused EIPs | Release unattached Elastic IPs ($0.005/hr) |

## Important Rules

- **Cost Explorer API charges $0.01 per request** — batch queries, avoid excessive polling
- **Data lag** — Cost data can be delayed up to 24 hours
- **Unblended vs amortized** — clarify which cost type the user wants
- **Record in GAIT** — log cost investigations for audit trail

## Environment Variables

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
