---
name: aws-cloud-monitoring
description: AWS CloudWatch monitoring — metrics, alarms, log queries, VPC flow log analysis, network performance
version: 1.0.0
tags: [aws, cloudwatch, monitoring, metrics, alarms, logs, flow-logs]
---

# AWS Cloud Monitoring

Monitor AWS cloud infrastructure via CloudWatch — query metrics, check alarms, search logs, analyze VPC flow logs, and investigate network performance issues.

## MCP Server

- **Command**: `uvx awslabs.cloudwatch-mcp-server@latest` (stdio transport)
- **Requires**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)

## Key Capabilities

- **Metrics**: Query CloudWatch metrics for any AWS service (EC2, ELB, TGW, NAT GW, VPN)
- **Alarms**: List and inspect CloudWatch alarms and their states
- **Logs**: Run CloudWatch Logs Insights queries across any log group
- **Flow Logs**: Analyze VPC and TGW flow logs for traffic patterns and dropped connections

## Workflow: Network Monitoring Dashboard

When a user asks "how is our AWS network performing?":

1. **Check alarms**: List CloudWatch alarms in ALARM state
2. **VPN metrics**: Tunnel state, bytes in/out for site-to-site VPNs
3. **NAT Gateway metrics**: Active connections, packets dropped, bytes processed
4. **Transit Gateway metrics**: Bytes in/out, packets dropped per attachment
5. **ELB metrics**: Healthy/unhealthy targets, latency, 5xx errors
6. **Report**: Network health dashboard with any issues flagged

## Workflow: Flow Log Analysis

When investigating traffic patterns or security events:

1. **Query VPC flow logs**: Filter by source IP, destination IP, port, action (ACCEPT/REJECT)
2. **Identify rejected traffic**: Find REJECT entries to see blocked connections
3. **Top talkers**: Aggregate by source/destination to find heaviest traffic flows
4. **Time correlation**: Narrow to specific time windows around incidents
5. **Report**: Traffic analysis with recommendations

## Common CloudWatch Network Metrics

| Service | Metric | What It Tells You |
|---------|--------|-------------------|
| VPN | `TunnelState` | 0=down, 1=up for each tunnel |
| VPN | `TunnelDataIn/Out` | Bytes through each VPN tunnel |
| NAT GW | `ActiveConnectionCount` | Active NAT connections |
| NAT GW | `PacketsDropCount` | Packets dropped (capacity issue) |
| NAT GW | `BytesProcessed` | Traffic volume through NAT |
| TGW | `BytesIn/BytesOut` | Traffic per TGW attachment |
| TGW | `PacketDropCountBlackhole` | Blackhole route drops |
| ELB | `HealthyHostCount` | Healthy targets behind ALB/NLB |
| ELB | `TargetResponseTime` | Backend latency |
| EC2 | `NetworkIn/NetworkOut` | Instance network throughput |
| EC2 | `NetworkPacketsIn/Out` | Instance packet rate |

## Flow Log Query Examples

```
# Top rejected connections in last hour
fields @timestamp, srcAddr, dstAddr, dstPort, action
| filter action = "REJECT"
| stats count() as rejections by srcAddr, dstAddr, dstPort
| sort rejections desc
| limit 20

# Traffic from specific source
fields @timestamp, srcAddr, dstAddr, dstPort, bytes, action
| filter srcAddr = "10.0.1.50"
| sort @timestamp desc

# Top talkers by bytes
fields srcAddr, dstAddr, bytes
| stats sum(bytes) as totalBytes by srcAddr, dstAddr
| sort totalBytes desc
| limit 10
```

## Important Rules

- **CloudWatch Logs Insights queries have a cost** — be mindful of time range and data volume
- **Region-specific** — metrics and logs are scoped to the configured region
- **Record in GAIT** — log monitoring investigations for audit trail

## Environment Variables

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
