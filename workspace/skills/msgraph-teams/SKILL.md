---
name: msgraph-teams
description: "Send notifications and reports to Microsoft Teams channels via Graph API - alert delivery, report posting, incident updates, and diagram sharing. Use when posting health alerts to Teams, sending security notifications, sharing change completion updates, or delivering reports to a Teams channel"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"], "env": ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"] } } }
---

# Microsoft Graph — Teams Notifications

## How to Call the Tools

The Microsoft Graph MCP server is invoked via npx with Azure AD credentials:

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" <tool-name> '<arguments-json>'
```

## Available Operations

### 1. List Teams

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_list_teams '{}'
```

### 2. List Channels in a Team

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_list_channels '{"teamId":"<team-id>"}'
```

### 3. Send a Message to a Channel

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_send_channel_message '{"teamId":"<team-id>","channelId":"<channel-id>","message":"<html-content>"}'
```

### 4. Reply to a Thread

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_reply_to_message '{"teamId":"<team-id>","channelId":"<channel-id>","messageId":"<msg-id>","message":"<html-content>"}'
```

### 5. List Recent Messages

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_list_channel_messages '{"teamId":"<team-id>","channelId":"<channel-id>"}'
```

## Message Formats

### Health Check Alert

```html
<h3>Health Check Report — 2026-02-22</h3>
<table>
  <tr><th>Device</th><th>CPU</th><th>Memory</th><th>Status</th></tr>
  <tr><td>R1</td><td>23%</td><td>45%</td><td>HEALTHY</td></tr>
  <tr><td>SW1</td><td>82%</td><td>67%</td><td>WARNING</td></tr>
</table>
<p><strong>1 WARNING</strong> — SW1 CPU at 82% (threshold: 80%)</p>
```

### Security Alert (Critical)

```html
<h3>CRITICAL — CVE Exposure Detected</h3>
<p><strong>Device:</strong> R1 (IOS-XE 17.9.4a)</p>
<p><strong>CVE-2023-20198</strong> (CVSS 10.0) — Web UI privilege escalation</p>
<p><strong>Exposure:</strong> CONFIRMED — ip http server enabled</p>
<p><strong>Action Required:</strong> Disable ip http server or upgrade immediately</p>
```

### Change Completion

```html
<h3>Change Complete — CHG0012345</h3>
<p><strong>Target:</strong> R1 — Add Loopback99 (99.99.99.99/32)</p>
<p><strong>Status:</strong> SUCCESS — verified, CR closed</p>
<p><strong>GAIT Branch:</strong> config-r1-loopback99-2026-02-22</p>
```

### Topology Diagram Share

```html
<h3>Updated Network Topology</h3>
<p>Campus physical topology regenerated from CDP/LLDP discovery.</p>
<p><strong>Devices:</strong> 4 | <strong>Links:</strong> 6 | <strong>Changes:</strong> +1 new link (R2-SW2)</p>
<p><a href="https://contoso.sharepoint.com/sites/neteng/Topology/campus-physical-2026-02-22.vsdx">Open in Visio</a></p>
```

## When to Use

- **Health alerts** — Post health check results with severity-coded summaries
- **Security notifications** — Alert on CVE exposure, failed security audits, or posture violations
- **Change updates** — Notify the team when changes are completed, failed, or rolled back
- **Incident updates** — Post investigation progress and resolution to incident channels
- **Report delivery** — Share audit reports, reconciliation results, and compliance summaries
- **Diagram sharing** — Post links to updated Visio topology diagrams on SharePoint

## Channel Mapping

Map Teams channels to NetClaw notification types:

```
### Teams Channel Map (configure in TOOLS.md)
- #netclaw-alerts     → P1/P2 critical alerts, CVE exposure
- #netclaw-reports    → Health reports, audit results, reconciliation
- #netclaw-changes    → Change request updates, completion notices
- #network-general    → P3/P4 notifications, topology updates
- #incidents          → Active incident investigation threads
```

## Integration with Other Skills

- **pyats-health-check** — Post health check summaries to Teams
- **pyats-security** — Alert on CVE exposure and failed security audits
- **netbox-reconcile** — Post drift detection results to Teams
- **servicenow-change-workflow** — Notify on CR creation, approval, completion
- **ise-incident-response** — Post investigation progress to incident channels
- **msgraph-visio** — Share Visio diagram links in Teams channels
- **msgraph-files** — Reference SharePoint file links in Teams messages
- **gait-session-tracking** — Record Teams notifications in audit trail

## Rules

1. **Never post credentials or secrets** to Teams channels
2. **Always include severity level** in alert messages
3. **Thread incident updates** — reply to the original message, don't create new top-level posts
4. **Respect channel purpose** — alerts go to alert channels, reports go to report channels
5. **Include actionable context** — every alert should say what happened and what to do next

## GAIT Audit Trail

Record Teams notifications in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Posted fleet health report to Teams #netclaw-reports channel. 4 devices assessed: 3 HEALTHY, 1 WARNING (SW1 CPU 82%). Included table with CPU, memory, and interface status per device.","artifacts":[]}}'
```
