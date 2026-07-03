---
name: defenseclaw-ops
description: Manage DefenseClaw enterprise security - scan components, manage tool permissions, view alerts, configure guardrails
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: [security, enterprise, defenseclaw, audit, compliance]
---

# DefenseClaw Operations

This skill manages DefenseClaw enterprise security for NetClaw deployments.

## Overview

DefenseClaw from Cisco AI Defense provides enterprise-grade security:
- OpenShell kernel-level sandbox
- Component scanning (skills, MCPs, plugins)
- Runtime guardrails (LLM inspection, tool call inspection)
- Audit logging with SIEM integration

## Prerequisites

- DefenseClaw installed and enabled
- `defenseclaw` CLI in PATH

Check status:
```bash
defenseclaw --version
```

## Common Operations

### Check Security Status

```bash
# View DefenseClaw version
defenseclaw --version

# Check gateway status
pgrep defenseclaw-gateway

# View current configuration
cat ~/.openclaw/config/openclaw.json | grep -A2 security
```

### Scan Components

Before deploying new skills, MCPs, or plugins, scan them:

```bash
# Scan a skill
defenseclaw skill scan pyats-health-check

# Scan an MCP server
defenseclaw mcp scan meraki-mcp

# Scan a plugin
defenseclaw plugin scan custom-tool
```

**Expected output for clean component:**
```
Scanning skill: pyats-health-check
✓ No HIGH/CRITICAL findings
Status: ALLOWED
```

**Expected output for blocked component:**
```
Scanning skill: bad-skill
✗ HIGH: Hardcoded credential detected
  Location: config.py:15
Status: BLOCKED
```

### Manage Tool Permissions

Block or allow specific tools:

```bash
# Block a destructive tool
defenseclaw tool block delete_file --reason "destructive operation"

# Block all write operations
defenseclaw tool block "*_write" --reason "read-only policy"

# Allow a previously blocked tool
defenseclaw tool allow delete_file

# List all tool rules
defenseclaw tool list
```

### View Security Alerts

```bash
# View recent alerts
defenseclaw alerts

# View last 50 alerts
defenseclaw alerts --limit 50

# Filter by severity
defenseclaw alerts --severity HIGH

# Filter by date
defenseclaw alerts --after 2026-04-01
```

### Export Audit Data

For compliance reporting:

```bash
# Export to JSON
defenseclaw alerts --export json > audit-$(date +%Y%m%d).json

# Export to CSV
defenseclaw alerts --export csv > audit-$(date +%Y%m%d).csv
```

### Configure Guardrail Mode

```bash
# Check current mode
defenseclaw config get guardrail.mode

# Enable observe mode (logging only - default)
defenseclaw setup guardrail --mode observe

# Enable action mode (blocking)
defenseclaw setup guardrail --mode action --restart

# Restart gateway after mode change
defenseclaw setup guardrail --restart
```

## Guardrail Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **observe** | Log violations, allow execution | Development, onboarding |
| **action** | Log violations AND block | Production, compliance |

## Security Categories

Guardrails check for these categories:

| Category | Description |
|----------|-------------|
| `secret` | Credential exfiltration |
| `command` | Shell command execution |
| `sensitive-path` | File system access |
| `c2` | Command & control communication |
| `cognitive-file` | AI memory manipulation |
| `trust-exploit` | Prompt injection |

## SIEM Integration

Configure external SIEM:

```bash
# Splunk HEC
defenseclaw config siem --type splunk \
  --endpoint https://splunk.example.com:8088 \
  --token $SPLUNK_HEC_TOKEN

# OTLP
defenseclaw config siem --type otlp \
  --endpoint https://otel-collector.example.com:4318

# Test connectivity
defenseclaw config siem --test
```

## Webhook Notifications

```bash
# Slack
defenseclaw config webhook --slack $SLACK_WEBHOOK_URL

# PagerDuty
defenseclaw config webhook --pagerduty $PD_ROUTING_KEY

# Webex
defenseclaw config webhook --webex $WEBEX_WEBHOOK_URL
```

## Troubleshooting

### DefenseClaw Not in PATH

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Gateway Not Running

```bash
# Check status
pgrep defenseclaw-gateway

# Start manually
defenseclaw-gateway start

# Check logs
tail -f ~/.defenseclaw/logs/gateway.log
```

### Component Falsely Blocked

```bash
# View detailed findings
defenseclaw skill scan <name> --verbose

# Add exception if false positive
defenseclaw exception add <component> --finding <id> --reason "reviewed"
```

## Related Documentation

- [docs/DEFENSECLAW.md](../../docs/DEFENSECLAW.md) - Full enterprise guide
- [docs/SOUL-DEFENSE.md](../../docs/SOUL-DEFENSE.md) - Security principles
- [docs/UPGRADE-TO-DEFENSECLAW.md](../../docs/UPGRADE-TO-DEFENSECLAW.md) - Migration guide
