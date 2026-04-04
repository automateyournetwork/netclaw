# Research: Splunk MCP Server Integration

**Feature**: 017-splunk-mcp-server | **Date**: 2026-04-04

## Research Tasks

### RT1: Official Splunk MCP Server Evaluation

**Decision**: Use official Splunk MCP server (splunk-mcp-server2)

**Rationale**:
- Maintained by Splunk (official repository)
- Apache-2.0 licensed
- Built-in SPL validation for safety
- Automatic output sanitization
- 7 focused tools covering core search functionality

**Alternatives Considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Official splunk-mcp-server2 | Safety features, official | Fewer tools than API surface | Selected |
| Custom FastMCP server | Full control | No built-in validation | Rejected |
| Splunk REST API direct | Full API access | No MCP integration | Rejected |

### RT2: Installation Method

**Decision**: stdio transport with Docker option

**Rationale**:
- stdio transport for direct integration
- Docker available for isolated deployments
- SSE transport for browser-based clients
- Consistent with NetClaw deployment patterns

**Configuration Options**:
- `--transport stdio` (default)
- `--transport sse` (for web)
- Docker: `docker run splunk/splunk-mcp-server2`

### RT3: Output Format

**Decision**: Markdown tables (default)

**Rationale**:
- User preference from clarification session
- Human-readable in CLI context
- Structured for parsing if needed
- Consistent with NetClaw output style

**Format Options**:
| Format | Use Case |
|--------|----------|
| Markdown tables | CLI display (selected) |
| JSON | Programmatic processing |
| CSV | Export/import |

### RT4: Authentication Method

**Decision**: Username/password via environment variables

**Rationale**:
- Splunk REST API uses basic auth or tokens
- Environment variables for credential safety
- Support for SSL verification toggle

**Required Variables**:
- `SPLUNK_HOST`: Splunk server hostname
- `SPLUNK_PORT`: Management port (default 8089)
- `SPLUNK_USERNAME`: Authentication username
- `SPLUNK_PASSWORD`: Authentication password
- `SPLUNK_VERIFY_SSL`: SSL verification flag

### RT5: Skill Organization

**Decision**: 3 focused skills aligned with Splunk domains

**Rationale**:
- Search: Core SPL execution (3 tools)
- Indexes: Discovery and metadata (2 tools)
- Saved: Pre-configured searches (2 tools)

**Tool Distribution**:
| Skill | Tools | Description |
|-------|-------|-------------|
| splunk-search | 3 | validate_spl, search_oneshot, search_export |
| splunk-indexes | 2 | get_indexes, get_config |
| splunk-saved | 2 | get_saved_searches, run_saved_search |

## Security Features

### SPL Validation
- Automatic validation before execution
- Prevents destructive commands (DELETE, etc.)
- Warns about resource-intensive queries
- Blocks injection attempts

### Output Sanitization
- Automatic redaction of credit card numbers
- Automatic redaction of SSN patterns
- Configurable sensitive data patterns

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| splunk-mcp-server2 | latest | Official MCP server |
| Splunk | 8.x+ | Backend search platform |
| Python/Node.js | Runtime | Server execution |

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Long-running queries | Medium | Medium | Timeout configuration |
| Large result sets | Medium | Medium | Use search_export for streaming |
| Credential exposure | Low | High | Environment variables, never logged |
| SPL injection | Low | High | Built-in validation |

## Open Questions Resolved

All research tasks completed. No blocking unknowns remain.
