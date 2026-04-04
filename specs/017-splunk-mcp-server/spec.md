# Feature Specification: Splunk MCP Server Integration

**Feature ID**: 017-splunk-mcp-server
**Status**: Draft
**Created**: 2026-04-04

## Overview

Integrate the official Splunk MCP server to provide log aggregation and SPL query capabilities within NetClaw. This integrates with existing syslog-receiver skills and enables powerful log analysis for network troubleshooting.

## Source

- **Repository**: https://github.com/splunk/splunk-mcp-server2
- **Type**: Official (Splunk-maintained)
- **License**: Apache-2.0
- **Transport**: stdio or SSE (Docker available)

## Tools Available (7 total)

| Tool | Description |
|------|-------------|
| `validate_spl` | Validate SPL queries for risks before execution |
| `search_oneshot` | Execute blocking searches with immediate results |
| `search_export` | Stream large result sets efficiently |
| `get_indexes` | List available Splunk indexes with metadata |
| `get_saved_searches` | Access saved search configurations |
| `run_saved_search` | Execute pre-configured saved searches |
| `get_config` | Retrieve server configuration |

## Security Features

- Automatic SPL validation to prevent destructive queries
- Automatic sanitization of sensitive data (credit cards, SSNs)
- Guardrails for resource-intensive queries

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SPLUNK_HOST` | Yes | Splunk server hostname |
| `SPLUNK_PORT` | No | Management port (default: 8089) |
| `SPLUNK_USERNAME` | Yes | Splunk username |
| `SPLUNK_PASSWORD` | Yes | Splunk password |
| `SPLUNK_VERIFY_SSL` | No | SSL verification (default: true) |

## User Stories

### US1: Log Search (Priority: P1) MVP
**As a** network engineer troubleshooting an issue
**I want to** search Splunk logs using SPL from NetClaw
**So that** I can investigate network events without leaving my workflow

**Acceptance Criteria:**
- Can execute SPL queries with time range
- Results returned in structured format (JSON, CSV, or Markdown)
- Large result sets streamed efficiently

### US2: Index Discovery (Priority: P1) MVP
**As a** network engineer
**I want to** list available Splunk indexes
**So that** I know where network logs are stored

**Acceptance Criteria:**
- Can list all indexes with metadata
- Can identify network-specific indexes
- Shows index size and event counts

### US3: Saved Search Execution (Priority: P2)
**As a** network engineer
**I want to** run pre-configured saved searches
**So that** I can execute complex queries without writing SPL

**Acceptance Criteria:**
- Can list available saved searches
- Can execute saved search by name
- Results match direct SPL execution

### US4: Query Validation (Priority: P2)
**As a** network engineer
**I want to** validate SPL queries before execution
**So that** I don't accidentally run destructive or expensive queries

**Acceptance Criteria:**
- Queries validated before execution
- Warnings for resource-intensive queries
- Rejection of destructive commands

## Proposed Skills

| Skill | Tools | Description |
|-------|-------|-------------|
| `splunk-search` | 3 | SPL query execution and validation |
| `splunk-indexes` | 2 | Index discovery and metadata |
| `splunk-saved` | 2 | Saved search management |

## Integration Points

- **Syslog Receiver**: Forward network syslog to Splunk indexes
- **SNMP Trap Receiver**: Correlate SNMP traps with Splunk events
- **Grafana**: Splunk as Grafana data source
- **PagerDuty**: Splunk alerts trigger PagerDuty incidents

## Clarifications

### Session 2026-04-04
- Q: Default output format for search results? → A: Markdown tables (human-readable, structured)

## Security Considerations

- Credentials stored in .env, never logged
- SPL validation prevents injection attacks
- Output sanitization removes sensitive data
- Default output format: Markdown tables for CLI readability

## Success Criteria

1. Can query "search Splunk for firewall deny logs in last hour" and get results
2. Can query "list Splunk indexes" and see network-related indexes
3. Integration appears in NetClaw UI with correct tool count
4. All 3 skills documented with SKILL.md files
