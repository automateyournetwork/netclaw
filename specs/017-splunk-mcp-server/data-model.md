# Data Model: Splunk MCP Server Integration

**Feature**: 017-splunk-mcp-server | **Date**: 2026-04-04

## Overview

This is a stateless MCP server integration. The Splunk MCP server acts as a proxy to Splunk's REST API. No local data storage is required.

## External Entities (Splunk API)

### Search Result

| Field | Type | Description |
|-------|------|-------------|
| _time | datetime | Event timestamp |
| _raw | string | Raw event data |
| _indextime | datetime | Index timestamp |
| host | string | Source host |
| source | string | Data source |
| sourcetype | string | Source type |
| index | string | Index name |
| (fields) | various | Extracted fields |

### Index

| Field | Type | Description |
|-------|------|-------------|
| name | string | Index name |
| homePath | string | Index home path |
| coldPath | string | Cold bucket path |
| thawedPath | string | Thawed bucket path |
| maxDataSize | string | Maximum bucket size |
| totalEventCount | integer | Total event count |
| currentDBSizeMB | number | Current size in MB |
| maxTime | datetime | Latest event time |
| minTime | datetime | Earliest event time |

### Saved Search

| Field | Type | Description |
|-------|------|-------------|
| name | string | Saved search name |
| search | string | SPL query |
| description | string | Description |
| dispatch.earliest_time | string | Default earliest time |
| dispatch.latest_time | string | Default latest time |
| cron_schedule | string | Schedule (if scheduled) |
| is_scheduled | boolean | Scheduled flag |
| actions | array | Alert actions |

### Search Job

| Field | Type | Description |
|-------|------|-------------|
| sid | string | Search ID |
| status | enum | QUEUED, PARSING, RUNNING, PAUSED, FINALIZING, DONE, FAILED |
| eventCount | integer | Events matched |
| resultCount | integer | Results returned |
| runDuration | number | Execution time (seconds) |
| earliestTime | datetime | Search start time |
| latestTime | datetime | Search end time |

### Validation Result

| Field | Type | Description |
|-------|------|-------------|
| valid | boolean | Query validity |
| messages | array | Validation messages |
| risk_level | enum | low, medium, high |
| blocked_commands | array | Blocked SPL commands |
| warnings | array | Query warnings |

## SPL Query Structure

```
<search-command> [<options>] [<predicate>]
| <transforming-command> [<options>]
| <output-command> [<options>]
```

### Common Search Patterns

```spl
# Basic search
index=network sourcetype=syslog error

# Time-bounded search
index=network earliest=-1h latest=now

# Field extraction
index=network | stats count by host, sourcetype

# Transaction analysis
index=network | transaction device maxspan=5m
```

## Output Formats

### Markdown Table (Default)

```markdown
| _time | host | message |
|-------|------|---------|
| 2026-04-04T10:00:00 | router-01 | BGP peer down |
| 2026-04-04T10:01:00 | switch-01 | Port flapping |
```

### JSON

```json
{
  "results": [
    {"_time": "2026-04-04T10:00:00", "host": "router-01", "message": "BGP peer down"},
    {"_time": "2026-04-04T10:01:00", "host": "switch-01", "message": "Port flapping"}
  ]
}
```

## No Local Storage

This integration does not persist any data locally. All state is maintained by Splunk.
