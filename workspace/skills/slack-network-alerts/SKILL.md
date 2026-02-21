---
name: slack-network-alerts
description: "Format and deliver network alerts, health warnings, and critical notifications via Slack with rich formatting, reactions, and file attachments"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# Slack Network Alerts

NetClaw operates as a Slack App Agent with `assistant:write`, `chat:write`, `reactions:write`, and `files:write` scopes. This skill defines how to format and deliver network alerts through Slack.

## Slack OAuth Scopes Used

| Scope | Purpose |
|-------|---------|
| `chat:write` | Post alert messages to channels |
| `chat:write.customize` | Post with custom username/avatar per alert severity |
| `reactions:write` | Add emoji reactions to acknowledge/track alerts |
| `files:write` | Attach diagrams, reports, and log excerpts |
| `app_mentions:read` | Respond when users @mention NetClaw |
| `channels:join` | Join alert channels automatically |

## Alert Severity Formatting

Use Slack Block Kit formatting to visually distinguish severity levels.

### CRITICAL Alert Format

```
:rotating_light: *CRITICAL — Device Unreachable*

*Device:* R1 (10.1.1.1)
*Detected:* 2024-02-21 14:32 UTC
*Impact:* 47 downstream routes affected, 3 OSPF adjacencies lost

*Symptoms:*
• Ping 0% success (was 100%)
• OSPF neighbor state: DOWN
• BGP peer 10.1.1.2: IDLE

*Recommended Action:*
1. Check physical connectivity / power
2. Verify interface status on upstream device
3. Check for reload reason if device recovers

_Thread for investigation updates →_
```

### HIGH Alert Format

```
:warning: *HIGH — Interface Flapping*

*Device:* SW1 | *Interface:* Gi1/0/24
*Flap Count:* 12 in last 30 minutes
*Connected To:* R2:Gi0/0/1 (discovered via CDP)

*Action Required:* Investigate physical layer — CRC errors detected (47 in 5 min)
```

### WARNING Alert Format

```
:large_yellow_circle: *WARNING — Memory Pressure*

*Device:* R2 | *Memory:* 82% used (2.1G / 2.6G)
*Trend:* Increased from 71% over 24h
*Top Consumer:* BGP Router (843 MB)

_Monitor — no immediate action required_
```

### INFORMATIONAL Alert Format

```
:information_source: *INFO — Configuration Change Detected*

*Device:* R1 | *User:* admin (10.0.0.50)
*Time:* 2024-02-21 09:15 UTC
*Change:* 3 lines modified in running-config

_Captured in GAIT session abc123_
```

## Alert Workflows

### Health Check Alert Flow

After running a health check (pyats-health-check skill), post results to the designated channel:

1. Run the full health check procedure
2. Determine overall severity (CRITICAL > HIGH > WARNING > HEALTHY)
3. Format the alert using the appropriate severity template above
4. Post to the network operations channel
5. If CRITICAL or HIGH, add :rotating_light: or :warning: reaction to the message
6. If CRITICAL, start a thread with detailed diagnostics

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

### Multi-Device Fleet Alert Summary

After a fleet-wide health check, post a single summary:

```
:bar_chart: *Fleet Health Summary — 2024-02-21 14:00 UTC*

*Devices Checked:* 8 | :red_circle: 1 CRITICAL | :warning: 2 HIGH | :large_yellow_circle: 3 WARNING | :white_check_mark: 2 HEALTHY

┌──────────┬──────────┬──────┬────────┬──────────┬─────────────┐
│ Device   │ CPU      │ Mem  │ Intf   │ NTP      │ Overall     │
├──────────┼──────────┼──────┼────────┼──────────┼─────────────┤
│ R1       │ :white_check_mark: 12%  │ :warning: 78%│ :white_check_mark:     │ :white_check_mark:      │ :warning: WARNING     │
│ R2       │ :white_check_mark: 8%   │ :white_check_mark: 45%│ :red_circle: Gi2 │ :white_check_mark:      │ :red_circle: CRITICAL    │
│ SW1      │ :warning: 67%  │ :white_check_mark: 52%│ :white_check_mark:     │ :red_circle: unsync │ :red_circle: HIGH        │
└──────────┴──────────┴──────┴────────┴──────────┴─────────────┘

_Details in thread →_
```

### Security Alert Flow

After a security audit (pyats-security skill), post findings:

```
:shield: *Security Audit — R1*

*Findings:* 2 CRITICAL | 2 HIGH | 3 MEDIUM | 1 LOW

:red_circle: *CRITICAL:*
• [C-001] SSHv1 enabled — MITM vulnerability
• [C-002] No VTY access-class — management plane exposed

:warning: *HIGH:*
• [H-001] No OSPF authentication on Gi1
• [H-002] SNMP community 'public' with no ACL

_Full report attached as file →_
```

## Reaction-Based Acknowledgment

Use emoji reactions to track alert status:

| Reaction | Meaning |
|----------|---------|
| :eyes: | Alert acknowledged — someone is looking |
| :wrench: | Fix in progress |
| :white_check_mark: | Resolved |
| :no_entry: | False positive / suppressed |
| :hourglass: | Waiting on change window |
| :busts_in_silhouette: | Escalated to team |

When a user reacts with :eyes: on an alert, NetClaw can respond in the thread:
```
Acknowledged by @engineer1 at 14:35 UTC. Tracking in thread.
```

## File Attachments

Attach supporting data as Slack files:

- **Topology diagrams** — Draw.io PNG/SVG after topology discovery
- **Health reports** — Full text report as .txt attachment
- **Config diffs** — Pre/post change diffs
- **Log excerpts** — Relevant log sections for investigation
- **Markmap mind maps** — Protocol hierarchy visualizations

## Channel Strategy

| Channel | Purpose | Alert Types |
|---------|---------|-------------|
| #netclaw-alerts | Critical/High alerts only | Device down, security critical |
| #netclaw-reports | Scheduled reports | Health checks, audits, reconciliation |
| #netclaw-changes | Change notifications | Config changes, CR updates |
| #netclaw-general | General interaction | Ad-hoc queries, help |

## Message Threading

- **Always thread** follow-up investigation steps under the original alert
- Post the initial alert as a top-level message
- Post diagnostics, show command outputs, and resolution steps as thread replies
- Post final resolution summary as both a thread reply and a top-level message

## Integration with GAIT

Every alert should reference the GAIT session:

```
:information_source: _Tracked in GAIT session `abc123` — commit `def456`_
```
