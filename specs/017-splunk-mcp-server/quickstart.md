# Quickstart: Splunk MCP Server Integration

**Feature**: 017-splunk-mcp-server | **Date**: 2026-04-04

## Prerequisites

1. Splunk Enterprise or Splunk Cloud instance
2. Splunk user with search capabilities
3. Network access to Splunk management port (8089)
4. NetClaw OpenClaw gateway running

## Setup (5 minutes)

### Step 1: Create Splunk User (if needed)

1. Log in to Splunk
2. Navigate to **Settings** → **Access Controls** → **Users**
3. Create a user with `user` or `power` role
4. Note the username and password

### Step 2: Configure Environment

Add to your `.env` file:

```bash
# Splunk MCP Server
SPLUNK_HOST=splunk.example.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=netclaw
SPLUNK_PASSWORD=your_password_here

# Optional: Disable SSL verification for self-signed certs
# SPLUNK_VERIFY_SSL=false
```

### Step 3: Register MCP Server

Add to `config/openclaw.json`:

```json
{
  "mcpServers": {
    "splunk-mcp": {
      "command": "npx",
      "args": ["@splunk/mcp-server2", "--transport", "stdio"],
      "env": {
        "SPLUNK_HOST": "${SPLUNK_HOST}",
        "SPLUNK_PORT": "${SPLUNK_PORT}",
        "SPLUNK_USERNAME": "${SPLUNK_USERNAME}",
        "SPLUNK_PASSWORD": "${SPLUNK_PASSWORD}",
        "SPLUNK_VERIFY_SSL": "${SPLUNK_VERIFY_SSL}"
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

### Test 1: List Indexes

```
List all Splunk indexes
```

**Expected**: Markdown table of indexes with names, sizes, and event counts.

### Test 2: Basic Search

```
Search Splunk for errors in the last hour
```

**Expected**: Markdown table of log entries with timestamps and messages.

### Test 3: SPL Validation

```
Validate this SPL: index=network | stats count by host
```

**Expected**: Validation result with risk level and any warnings.

### Test 4: Saved Search

```
List available Splunk saved searches
```

**Expected**: List of saved searches with names and descriptions.

## Skills Available

| Skill | Invocation | Description |
|-------|------------|-------------|
| `/splunk-search` | SPL queries | Execute and validate SPL searches |
| `/splunk-indexes` | Index discovery | List indexes and configuration |
| `/splunk-saved` | Saved searches | Run pre-configured searches |

## Common Queries

### Search Operations

```
# Basic error search
Search Splunk for sourcetype=syslog level=error in the last hour

# Host-specific search
Search Splunk for all events from router-01 today

# Statistical query
Search Splunk and show count of events by host for network index
```

### SPL Examples

```
# Find BGP errors
index=network sourcetype=syslog BGP error | table _time, host, message

# Interface traffic analysis
index=network sourcetype=snmp | stats avg(ifInOctets) by host, interface

# Top talkers
index=netflow | stats sum(bytes) as total_bytes by src_ip | sort -total_bytes | head 10
```

### Index Operations

```
# List all indexes
Show all Splunk indexes and their sizes

# Find network indexes
List Splunk indexes that contain network data
```

### Saved Search Operations

```
# List saved searches
List all saved searches in Splunk

# Run specific saved search
Run the "Network Errors Daily" saved search
```

## Troubleshooting

### "Unauthorized" Error

- Verify `SPLUNK_USERNAME` and `SPLUNK_PASSWORD` are correct
- Ensure user has search capabilities role
- Check Splunk authentication settings

### "Connection Refused" Error

- Verify `SPLUNK_HOST` and `SPLUNK_PORT` are correct
- Check network connectivity to Splunk
- Ensure Splunk management port is accessible

### "SSL Certificate" Error

- For self-signed certs, set `SPLUNK_VERIFY_SSL=false`
- Or add the CA certificate to your trust store

### "Query Blocked" Error

- SPL validation blocked a potentially dangerous query
- Review the validation message for details
- Modify query to remove blocked commands

## Output Format

Results are returned as Markdown tables by default:

```markdown
| _time | host | sourcetype | message |
|-------|------|------------|---------|
| 2026-04-04T10:00:00Z | router-01 | syslog | BGP peer down |
| 2026-04-04T10:01:00Z | switch-01 | syslog | Port flapping |
```

## Security Notes

- Credentials stored in .env, never logged
- SPL validation prevents destructive queries
- Sensitive data automatically sanitized in output
- Use dedicated service account for NetClaw
