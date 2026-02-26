---
name: gcp-cloud-logging
description: Google Cloud Logging — log search, VPC flow logs, firewall logs, audit logs, log buckets and views
version: 1.0.0
tags: [gcp, cloud-logging, logs, flow-logs, audit, firewall-logs]
---

# GCP Cloud Logging

Search and analyze Google Cloud logs via the Cloud Logging MCP server — query log entries, discover available logs, inspect log buckets and views for VPC flow logs, firewall logs, audit logs, and application logs.

## MCP Server

- **Endpoint**: `https://logging.googleapis.com/mcp` (Streamable HTTP)
- **Auth**: OAuth 2.0 via Google IAM — service account key (`GOOGLE_APPLICATION_CREDENTIALS`) or `gcloud auth application-default login`
- **Requires**: `GCP_PROJECT_ID` environment variable

## Available Tools (6)

| Tool | What It Does |
|------|-------------|
| `list_log_entries` | Search and retrieve log entries — the primary tool for debugging, error hunting, and audit |
| `list_log_names` | Discover what logs exist in a project — find available log sources |
| `get_bucket` | Get details of a specific log bucket (storage container for logs) |
| `list_buckets` | List all log buckets in a project |
| `get_view` | Get a specific log view (fine-grained access filter on a bucket) |
| `list_views` | List log views in a bucket |

## Workflow: VPC Flow Log Analysis

When investigating GCP network traffic:

1. **Discover logs**: `list_log_names` — find `compute.googleapis.com/vpc_flows`
2. **Query flow logs**: `list_log_entries` filtered by:
   - Source/destination IP
   - Port and protocol
   - Action (ALLOWED/DENIED)
   - Time range
3. **Denied traffic**: Filter for `reporter="DEST"` and denied connections
4. **Top talkers**: Aggregate by source/destination IP and bytes
5. **Cross-reference**: Use `gcp-cloud-monitoring` for network metrics during the same period
6. **Report**: Traffic analysis with security findings

## Workflow: Firewall Log Investigation

When investigating GCP firewall rule activity:

1. **Discover logs**: `list_log_names` — find `compute.googleapis.com/firewall`
2. **Query firewall logs**: `list_log_entries` filtered by:
   - Rule name
   - Action (ALLOWED/DENIED)
   - Source/destination IP
   - Port
3. **Denied connections**: Find blocked traffic patterns
4. **Rule effectiveness**: Which rules are hitting most frequently?
5. **Report**: Firewall activity summary with recommendations

## Workflow: Audit Trail Investigation

When investigating GCP API activity (equivalent of AWS CloudTrail):

1. **Admin activity logs**: `list_log_entries` for `cloudaudit.googleapis.com/activity` — who created/modified/deleted resources?
2. **Data access logs**: `list_log_entries` for `cloudaudit.googleapis.com/data_access` — who read what?
3. **Filter by principal**: Narrow to specific user or service account
4. **Filter by method**: Narrow to specific API calls (e.g., `compute.instances.delete`)
5. **Time window**: Focus on the incident period
6. **Report**: Audit timeline with responsible principals and actions

## Workflow: Troubleshooting with Logs

When debugging a GCP issue:

1. **Application logs**: `list_log_entries` for the affected service
2. **Error filtering**: Filter by severity (ERROR, CRITICAL, EMERGENCY)
3. **Instance logs**: Filter by `resource.labels.instance_id` for specific VMs
4. **Correlate**: Match timestamps with `gcp-cloud-monitoring` alert violations
5. **Bucket check**: `list_buckets` to verify log retention settings
6. **Report**: Root cause analysis with log evidence

## Common GCP Log Sources

| Log Name | What It Contains |
|----------|-----------------|
| `compute.googleapis.com/vpc_flows` | VPC flow logs — source/dest IP, port, bytes, packets, action |
| `compute.googleapis.com/firewall` | Firewall rule hits — allowed/denied connections with rule name |
| `cloudaudit.googleapis.com/activity` | Admin activity audit — resource create/modify/delete events |
| `cloudaudit.googleapis.com/data_access` | Data access audit — read operations on resources |
| `cloudaudit.googleapis.com/system_event` | System events — Google-initiated actions (live migration, etc.) |
| `compute.googleapis.com/shielded_vm_integrity` | Shielded VM boot integrity verification |
| `dns.googleapis.com/dns_queries` | Cloud DNS query logs |
| `loadbalancing.googleapis.com/requests` | Load balancer access logs |
| `networksecurity.googleapis.com/firewall_threat` | Cloud IDS / Firewall threat detection |

## Log Query Filter Examples

```
# VPC flow logs — denied traffic to port 443
resource.type="gce_subnetwork"
logName="projects/PROJECT/logs/compute.googleapis.com%2Fvpc_flows"
jsonPayload.disposition="DENIED"
jsonPayload.connection.dest_port=443

# Firewall — denied SSH attempts
resource.type="gce_subnetwork"
logName="projects/PROJECT/logs/compute.googleapis.com%2Ffirewall"
jsonPayload.disposition="DENIED"
jsonPayload.connection.dest_port=22

# Audit — who deleted VMs in the last hour
logName="projects/PROJECT/logs/cloudaudit.googleapis.com%2Factivity"
protoPayload.methodName="compute.instances.delete"
timestamp>="2026-01-01T00:00:00Z"

# DNS queries from specific source
resource.type="dns_query"
jsonPayload.sourceIP="10.0.1.50"
```

## Important Rules

- **Remote MCP server** — hosted by Google, no local install needed
- **OAuth 2.0 authentication** — uses IAM for access control
- **Project-scoped** — logs are scoped to the configured GCP project
- **Log queries have cost implications** — Cloud Logging charges for data scanned beyond free tier (50 GB/month free)
- **Retention varies** — Admin activity logs: 400 days, Data access logs: 30 days (default), VPC flow logs: depends on bucket config
- **Record in GAIT** — log all investigations for audit trail

## Environment Variables

- `GCP_PROJECT_ID` — Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` — Path to service account key JSON file
