# Skill: Twitter Check

**Purpose**: Quick invocation to check mentions and respond to #netclaw threads.

**Trigger**: `/twitter-check` or "check twitter" or "#netclaw check"

**MCP Server**: twitter-mcp

## Overview

This skill provides a quick way for John to invoke the Twitter mention check and auto-respond workflow directly from Claude Code.

## Usage

```
/twitter-check           # Check and respond to mentions
/twitter-check dry       # Preview what would happen (no posting)
/twitter-check heartbeat # Also post a heartbeat tweet
```

## Workflow

When invoked:

1. **Fetch mentions**: Get recent @mentions via OAuth 2.0
2. **Filter**: Find unprocessed mentions in #netclaw threads
3. **Auto-respond**: Reply based on mention category
4. **Report**: Show summary of actions taken

## Tool Call

```json
{
  "tool": "twitter_heartbeat_cycle",
  "arguments": {
    "post_heartbeat": false,
    "respond_to_netclaw_only": true,
    "dry_run": false
  }
}
```

## Example Session

```
User: /twitter-check