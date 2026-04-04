# Quickstart: PagerDuty MCP Server Integration

**Feature**: 015-pagerduty-mcp-server | **Date**: 2026-04-04

## Prerequisites

1. PagerDuty account with API access
2. uvx installed (or pip)
3. NetClaw OpenClaw gateway running

## Setup (5 minutes)

### Step 1: Generate PagerDuty API Token

1. Log in to PagerDuty
2. Navigate to **User Settings** → **Create API User Token**
3. Copy the generated token

### Step 2: Configure Environment

Add to your `.env` file:

```bash
# PagerDuty MCP Server
PAGERDUTY_USER_API_KEY=your_api_token_here

# Optional: EU datacenter
# PAGERDUTY_API_HOST=https://api.eu.pagerduty.com
```

### Step 3: Register MCP Server

Add to `config/openclaw.json`:

```json
{
  "mcpServers": {
    "pagerduty-mcp": {
      "command": "uvx",
      "args": ["pagerduty-mcp", "--enable-write-tools"],
      "env": {
        "PAGERDUTY_USER_API_KEY": "${PAGERDUTY_USER_API_KEY}"
      }
    }
  }
}
```

### Step 4: Restart OpenClaw Gateway

```bash
# Restart to load new MCP server
openclaw restart
```

## Verification

### Test 1: List Active Incidents

```
Show all active PagerDuty incidents
```

**Expected**: List of incidents with title, status, urgency, and assigned responders.

### Test 2: On-Call Query

```
Who is on-call for the network-core escalation policy?
```

**Expected**: Current on-call engineer(s) with contact information.

### Test 3: Service Health

```
What is the status of all PagerDuty services?
```

**Expected**: List of services with current health status.

### Test 4: Create Test Incident (Write Test)

```
Create a low-urgency test incident on the test-service with title "NetClaw Integration Test"
```

**Expected**: Incident created and ID returned. Remember to resolve it after testing.

## Skills Available

| Skill | Invocation | Description |
|-------|------------|-------------|
| `/pagerduty-incidents` | Incident management | View, create, acknowledge, resolve incidents |
| `/pagerduty-oncall` | On-call visibility | Schedules, rotations, coverage |
| `/pagerduty-services` | Service catalog | Service health and configuration |
| `/pagerduty-orchestration` | Event routing | Orchestration rules and alert grouping |

## Common Queries

### Incident Operations

```
# View active incidents
Show all triggered and acknowledged incidents

# Get incident details
Show details for incident P1234567

# Acknowledge incident
Acknowledge incident P1234567

# Resolve incident
Resolve incident P1234567 with note "Fixed by network configuration change"
```

### On-Call Operations

```
# Current on-call
Who is on-call right now?

# Specific schedule
Show the network-core on-call schedule for this week

# Create override
Create an on-call override for jsmith on network-core from 2pm to 6pm today
```

### Service Operations

```
# List all services
List all PagerDuty services

# Service details
Show details for the network-core service

# Service incidents
Show all incidents for the network-core service
```

## Troubleshooting

### "Unauthorized" Error

- Verify `PAGERDUTY_USER_API_KEY` is set correctly
- Check token hasn't expired
- Ensure token has required permissions

### "Rate Limited" Error

- PagerDuty enforces API rate limits
- Wait and retry
- Consider caching frequent queries

### Write Operations Fail

- Verify `--enable-write-tools` flag is set
- Check user has write permissions in PagerDuty
- For production services, ensure ServiceNow CR is approved

## Security Notes

- API token is never logged or displayed
- Write operations on production services should be gated by ITSM approval
- Consider using a dedicated service account for NetClaw integration
