# Research: PagerDuty MCP Server Integration

**Feature**: 015-pagerduty-mcp-server | **Date**: 2026-04-04

## Research Tasks

### RT1: Official PagerDuty MCP Server Evaluation

**Decision**: Use official PagerDuty MCP server (pagerduty-mcp)

**Rationale**:
- Maintained by PagerDuty directly (official repository)
- Apache-2.0 licensed
- Comprehensive toolset (70 tools covering all major API endpoints)
- Active development with recent commits
- Supports both uvx and Docker deployment

**Alternatives Considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Official pagerduty-mcp | Full API coverage, official support | None | Selected |
| Custom FastMCP server | Full control | Maintenance burden, API changes | Rejected |
| REST API direct | No MCP dependency | No MCP integration | Rejected |

### RT2: Installation Method

**Decision**: uvx (recommended by PagerDuty)

**Rationale**:
- Zero-dependency installation
- Automatic version management
- Consistent with community MCP server patterns in NetClaw
- Official recommendation from PagerDuty documentation

**Alternatives Considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| uvx | Zero-dep, auto-update | Requires uvx installed | Selected |
| pip install | Standard Python | Dependency management | Backup option |
| Docker | Isolation | Overhead for simple server | Available |

### RT3: Write Tools Policy

**Decision**: Enable write tools by default (--enable-write-tools)

**Rationale**:
- User preference from clarification session
- Full tool access provides complete incident management capability
- Write operations for production services gated by ServiceNow CR workflow
- Aligns with NetClaw's operational focus

**Alternatives Considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Write tools enabled | Full functionality | Risk of unintended changes | Selected (with ITSM gating) |
| Read-only by default | Safer | Limits operational capability | Rejected |

### RT4: Authentication Method

**Decision**: User API Token via environment variable

**Rationale**:
- PagerDuty REST API v2 uses User Token authentication
- Token stored in PAGERDUTY_USER_API_KEY environment variable
- Standard pattern for NetClaw MCP servers
- Never logged or exposed in output

**Token Requirements**:
- Created from PagerDuty user settings
- Requires appropriate roles for write operations
- EU customers use api.eu.pagerduty.com endpoint

### RT5: Skill Organization

**Decision**: 4 focused skills aligned with PagerDuty domains

**Rationale**:
- Incidents: Core operational focus (8 tools)
- On-Call: Schedule and coverage visibility (6 tools)
- Services: Catalog and health (4 tools)
- Orchestration: Event routing configuration (5 tools)

**Tool Distribution**:
| Skill | Read Tools | Write Tools | Total |
|-------|------------|-------------|-------|
| pagerduty-incidents | 8 | 4 | 12 |
| pagerduty-oncall | 6 | 3 | 9 |
| pagerduty-services | 2 | 2 | 4 |
| pagerduty-orchestration | 5 | 2 | 7 |
| (Other tools) | - | - | 38 |

Note: Remaining tools cover teams, users, status pages, and additional management functions.

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| pagerduty-mcp | latest | Official MCP server |
| uvx | latest | Package runner |
| Python | 3.10+ | Runtime (via uvx) |

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limiting | Medium | Medium | Caching in future iteration |
| Token expiration | Low | Medium | Documentation for token refresh |
| Write tool misuse | Low | High | ServiceNow CR gating for production |
| PagerDuty API changes | Low | Medium | Pin to stable pagerduty-mcp version |

## Open Questions Resolved

All research tasks completed. No blocking unknowns remain.
