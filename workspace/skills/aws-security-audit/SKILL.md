---
name: aws-security-audit
description: AWS security auditing — IAM users/roles/policies, CloudTrail API events, security posture analysis
version: 1.0.0
tags: [aws, iam, cloudtrail, security, audit, compliance]
---

# AWS Security Audit

Audit AWS security posture via IAM and CloudTrail MCP servers — inspect users, roles, policies, and trace API activity for incident investigation and compliance.

## MCP Servers

- **IAM MCP**: `uvx awslabs.iam-mcp-server@latest --readonly` (stdio transport)
- **CloudTrail MCP**: `uvx awslabs.cloudtrail-mcp-server@latest` (stdio transport)
- **Requires**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)

## Key Capabilities

### IAM (Identity & Access Management)

- **Users**: List IAM users, access keys, MFA status, last activity
- **Roles**: List roles, trust policies, attached permissions
- **Policies**: Inspect policy documents, identify overly permissive policies
- **Groups**: List groups and their memberships
- **Read-only mode**: `--readonly` flag prevents any IAM modifications

### CloudTrail (API Audit Trail)

- **Event history**: Search recent API calls by user, service, or resource
- **Lookup events**: Filter by event name, resource type, username
- **Time-based queries**: Narrow to specific time windows around incidents
- **Multi-region**: Trail events across all enabled regions

## Workflow: Network Security Audit

When a user asks "audit our AWS network security":

1. **IAM roles for network services**: Check roles used by VPC, TGW, Network Firewall
2. **Overly permissive policies**: Find policies with `ec2:*` or `*:*` actions
3. **Unused access keys**: Identify stale credentials that should be rotated
4. **MFA compliance**: Check which users lack MFA
5. **CloudTrail check**: Recent `AuthorizeSecurityGroupIngress`, `CreateNetworkAcl`, `ModifyVpcAttribute` events
6. **Report**: Security posture summary with remediation recommendations

## Workflow: Incident Investigation

When investigating a security event:

1. **CloudTrail lookup**: Search events by time window and suspected user/role
2. **Identify actions**: What API calls were made? `DeleteSecurityGroup`, `ModifySubnetAttribute`?
3. **Source IP**: Where did the API calls originate from?
4. **IAM context**: What permissions does the user/role have? Should they?
5. **Blast radius**: What resources were affected?
6. **Report**: Timeline of events with impact assessment

## Workflow: Compliance Check

When checking AWS security compliance:

1. **Root account**: Check for root access key usage in CloudTrail
2. **MFA enforcement**: List users without MFA enabled
3. **Access key rotation**: Find keys older than 90 days
4. **Unused credentials**: Identify users with no recent activity
5. **Policy review**: Check for policies granting `*` on sensitive services
6. **Report**: Compliance scorecard with findings

## Common CloudTrail Network Events

| Event Name | What It Means |
|------------|---------------|
| `AuthorizeSecurityGroupIngress` | Security group rule added (inbound) |
| `AuthorizeSecurityGroupEgress` | Security group rule added (outbound) |
| `RevokeSecurityGroupIngress` | Security group rule removed (inbound) |
| `CreateNetworkAclEntry` | NACL rule added |
| `CreateRoute` | Route table entry added |
| `ModifyVpcAttribute` | VPC setting changed |
| `CreateVpnConnection` | New VPN tunnel created |
| `AttachInternetGateway` | IGW attached to VPC |
| `CreateTransitGatewayRoute` | TGW route added |
| `UpdateFirewallRuleGroupRuleList` | Network Firewall rule changed |

## IAM Best Practices for Network Teams

| Check | Why It Matters |
|-------|---------------|
| No `ec2:*` policies | Prevent accidental network changes |
| Separate roles per service | Least privilege for VPC, TGW, Firewall |
| MFA on all humans | Protect against credential theft |
| No root access keys | Root should use MFA console only |
| Key rotation < 90 days | Limit exposure of compromised keys |
| CloudTrail enabled | Audit trail for all API changes |

## Important Rules

- **IAM MCP runs in read-only mode** — cannot create, modify, or delete IAM resources
- **CloudTrail has event history limits** — default 90-day lookback for management events
- **Region-specific for CloudTrail** — unless using organization trail
- **Record in GAIT** — log all security investigations for audit trail

## Environment Variables

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or `AWS_PROFILE`)
