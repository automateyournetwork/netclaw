---
name: webex-network-alerts
description: "Format and deliver network alerts, health warnings, and critical notifications via Cisco WebEx with Adaptive Cards, markdown formatting, and file attachments. Use when sending alerts to WebEx spaces, posting health check results, notifying the team about a device issue, or formatting network status updates for a WebEx space."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# WebEx Network Alerts

## WebEx API Capabilities Used

| API | Purpose |
|-----|---------|
| Messages — Create | Post alert messages to spaces |
| Messages — Create (with Adaptive Card) | Deliver rich formatted alerts with severity styling |
| Messages — Create (with files) | Attach diagrams, reports, and log excerpts |
| Webhooks | Receive notification when users interact with Adaptive Cards |
| Rooms — List | Discover target spaces for alert delivery |
| People — Get My Own Details | Verify bot identity and space membership |

## WebEx Authentication

NetClaw uses a WebEx Bot access token for all messaging operations:

- **Bot Token**: Long-lived token from `developer.webex.com` (does not expire)
- **Base URL**: `https://webexapis.com/v1/`
- **Header**: `Authorization: Bearer $WEBEX_BOT_TOKEN`

## Alert Severity Formatting

Use WebEx markdown and Adaptive Cards to visually distinguish severity levels. WebEx supports a subset of markdown in plain messages and full Adaptive Card schema (v1.3) for rich layouts.

### CRITICAL Alert Format (Adaptive Card)

Post as an Adaptive Card with a red container:

```json
{
  "contentType": "application/vnd.microsoft.card.adaptive",
  "content": {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.3",
    "body": [
      {
        "type": "Container",
        "style": "attention",
        "items": [
          {
            "type": "TextBlock",
            "text": "CRITICAL -- Device Unreachable",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Attention"
          }
        ]
      },
      {
        "type": "FactSet",
        "facts": [
          { "title": "Device:", "value": "R1 (10.1.1.1)" },
          { "title": "Detected:", "value": "2024-02-21 14:32 UTC" },
          { "title": "Impact:", "value": "47 downstream routes affected, 3 OSPF adjacencies lost" }
        ]
      },
      {
        "type": "TextBlock",
        "text": "**Symptoms:**\n- Ping 0% success (was 100%)\n- OSPF neighbor state: DOWN\n- BGP peer 10.1.1.2: IDLE",
        "wrap": true
      },
      {
        "type": "TextBlock",
        "text": "**Recommended Action:**\n1. Check physical connectivity / power\n2. Verify interface status on upstream device\n3. Check for reload reason if device recovers",
        "wrap": true
      }
    ]
  }
}
```

Always include a plain `markdown` field as fallback text alongside the card attachment for clients that don't render Adaptive Cards.

### HIGH Alert Format (Markdown)

```
**HIGH -- Interface Flapping**

**Device:** SW1 | **Interface:** Gi1/0/24
**Flap Count:** 12 in last 30 minutes
**Connected To:** R2:Gi0/0/1 (discovered via CDP)

**Action Required:** Investigate physical layer -- CRC errors detected (47 in 5 min)
```

### WARNING Alert Format (Markdown)

```
**WARNING -- Memory Pressure**

**Device:** R2 | **Memory:** 82% used (2.1G / 2.6G)
**Trend:** Increased from 71% over 24h
**Top Consumer:** BGP Router (843 MB)

_Monitor -- no immediate action required_
```

### INFORMATIONAL Alert Format (Markdown)

```
**INFO -- Configuration Change Detected**

**Device:** R1 | **User:** admin (10.0.0.50)
**Time:** 2024-02-21 09:15 UTC
**Change:** 3 lines modified in running-config

_Captured in GAIT session abc123_
```

## Alert Workflows

### Health Check Alert Flow

After running a health check (pyats-health-check skill), post results to the designated WebEx space:

1. Run the full health check procedure
2. Determine overall severity (CRITICAL > HIGH > WARNING > HEALTHY)
3. Format the alert using the appropriate severity template above
4. Post to the network operations space via WebEx Messages API
5. For CRITICAL alerts, use an Adaptive Card with `attention` style container
6. For CRITICAL, start a thread by replying to the original message with detailed diagnostics

### Threshold-Triggered Alerts

When any health check metric exceeds thresholds:

| Metric | WARNING | HIGH | CRITICAL |
|--------|---------|------|----------|
| CPU 5min avg | > 50% | > 75% | > 90% |
| Memory used | > 70% | > 85% | > 95% |
| Interface errors | > 0 CRC | > 100/min | Resets incrementing |
| Packet loss | > 0% | > 5% | > 20% |
| NTP offset | > 100ms | > 500ms | > 1s or unsync |
| BGP peer | Flapping | 1 peer down | Multiple peers down |
| OSPF adjacency | Flapping | 1 adj lost | Area partition |

### Multi-Device Fleet Alert Summary (Adaptive Card)

After a fleet-wide health check, post a single summary using an Adaptive Card with a ColumnSet:

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "TextBlock",
      "text": "Fleet Health Summary -- 2024-02-21 14:00 UTC",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "TextBlock",
      "text": "**Devices Checked:** 8 | 1 CRITICAL | 2 HIGH | 3 WARNING | 2 HEALTHY"
    },
    {
      "type": "ColumnSet",
      "columns": [
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Device**","weight":"Bolder"},{"type":"TextBlock","text":"R1"},{"type":"TextBlock","text":"R2"},{"type":"TextBlock","text":"SW1"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**CPU**","weight":"Bolder"},{"type":"TextBlock","text":"12%"},{"type":"TextBlock","text":"8%"},{"type":"TextBlock","text":"67%"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Mem**","weight":"Bolder"},{"type":"TextBlock","text":"78%"},{"type":"TextBlock","text":"45%"},{"type":"TextBlock","text":"52%"}]},
        { "type": "Column", "width": "auto", "items": [{"type":"TextBlock","text":"**Overall**","weight":"Bolder"},{"type":"TextBlock","text":"WARNING","color":"Warning"},{"type":"TextBlock","text":"CRITICAL","color":"Attention"},{"type":"TextBlock","text":"HIGH","color":"Warning"}]}
      ]
    },
    {
      "type": "TextBlock",
      "text": "_Details in thread_",
      "isSubtle": true
    }
  ]
}
```

### Security Alert Flow

After a security audit (pyats-security skill), post findings:

```
**Security Audit -- R1**

**Findings:** 2 CRITICAL | 2 HIGH | 3 MEDIUM | 1 LOW

**CRITICAL:**
- [C-001] SSHv1 enabled -- MITM vulnerability
- [C-002] No VTY access-class -- management plane exposed

**HIGH:**
- [H-001] No OSPF authentication on Gi1
- [H-002] SNMP community 'public' with no ACL

_Full report attached as file_
```

## WebEx Threading

WebEx supports message threading via the `parentId` field:

- **Always thread** follow-up investigation steps under the original alert
- Post the initial alert as a top-level message to the space
- Post diagnostics, show command outputs, and resolution steps as thread replies using `parentId`
- Post final resolution summary as both a thread reply and a new top-level message

## File Attachments

Attach supporting data as files via the Messages API (multipart POST):

- **Topology diagrams** -- Draw.io PNG/SVG after topology discovery
- **Health reports** -- Full text report as .txt attachment
- **Config diffs** -- Pre/post change diffs
- **Log excerpts** -- Relevant log sections for investigation
- **Markmap mind maps** -- Protocol hierarchy visualizations

WebEx supports attaching files up to 100 MB per message.

## Space Strategy

| Space | Purpose | Alert Types |
|-------|---------|-------------|
| NetClaw Alerts | Critical/High alerts only | Device down, security critical |
| NetClaw Reports | Scheduled reports | Health checks, audits, reconciliation |
| NetClaw Changes | Change notifications | Config changes, CR updates |
| NetClaw General | General interaction | Ad-hoc queries, help |
| Incidents | Active incident threads | P1/P2 incident response |

## WebEx vs Slack Feature Mapping

| Slack Feature | WebEx Equivalent |
|---------------|-----------------|
| Emoji reactions (:rotating_light:) | Adaptive Card `color` property + bold text severity labels |
| Block Kit formatting | Adaptive Cards v1.3 |
| Custom username/avatar | Bot identity (set in developer.webex.com) |
| File uploads | Messages API multipart/form-data with `files` parameter |
| Thread replies | `parentId` field on Messages API |
| Channel mentions (@here, @channel) | `<@personId>` mentions and group mentions |
| Pinned messages | N/A -- use a dedicated "Baselines" space |

## Integration with GAIT

Every alert should reference the GAIT session:

```
_Tracked in GAIT session `abc123` -- commit `def456`_
```
