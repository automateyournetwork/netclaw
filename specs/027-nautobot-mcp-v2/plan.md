# Implementation Plan: Enhanced Nautobot MCP Server v2

**Branch**: `027-nautobot-mcp-v2` | **Date**: 2026-04-09 | **Spec**: `specs/027-nautobot-mcp-v2/spec.md`
**Input**: Feature specification from `/specs/027-nautobot-mcp-v2/spec.md`

## Summary

Replace the existing mcp-nautobot (v1, 5 REST-only IPAM tools) with a comprehensive Nautobot 3.1.0 MCP server using GraphQL for reads (7 tools) and REST API for writes (5 tools) plus a connection test tool. Covers devices, interfaces, VLANs, prefixes, IP addresses, cables, raw GraphQL, ITSM-gated writes, and live-vs-SoT reconciliation. Python 3.10+ with FastMCP, httpx, stdio transport.

## Technical Context

**Language/Version**: Python 3.10+ (3.13 in Docker)
**Primary Dependencies**: FastMCP (mcp SDK), httpx (async HTTP), python-dotenv
**Storage**: N/A (stateless proxy to Nautobot API)
**Testing**: Manual validation against live Nautobot at 192.168.3.253
**Target Platform**: Linux (Docker container, stdio MCP transport)
**Project Type**: MCP server (stdio transport)
**Performance Goals**: Query responses within 3 seconds (SC-001)
**Constraints**: GraphQL for reads only (no mutations in Nautobot 3.1.0), REST for writes
**Scale/Scope**: 13 tools (7 read, 5 write, 1 connection test), ~3 source files

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | Read tools are read-only via GraphQL. Write tools are ITSM-gated. |
| II. Read-Before-Write | PASS | Write tools resolve existing state via GraphQL before REST writes. Update tool returns old+new values. |
| III. ITSM-Gated Changes | PASS | All write tools require cr_number when ITSM_ENABLED=true and ITSM_LAB_MODE=false. |
| IV. Immutable Audit Trail | PASS | All operations logged to stderr. GAIT integration at skill level. |
| V. MCP-Native Integration | PASS | FastMCP server with stdio transport, proper JSON-RPC lifecycle. |
| VI. Multi-Vendor Neutrality | PASS | Nautobot is vendor-neutral SoT. Reconciliation works with any pyATS-supported device. |
| VII. Skill Modularity | PASS | Replaces v1 in same slot. Companion skill in workspace/skills/. |
| VIII. Verify After Every Change | PASS | Write tools query the object after creation/update to confirm. Reconciliation enables verification. |
| IX. Security by Default | PASS | Credentials from env vars only. SSL verification configurable. |
| X. Observability as First-Class | PASS | Connection test tool. Stderr logging. HUD update. |
| XI. Artifact Coherence | PENDING | Will be completed during implementation. |
| XII. Documentation-as-Code | PENDING | README and SKILL.md created during implementation. |
| XIII. Credential Safety | PASS | NAUTOBOT_URL and NAUTOBOT_TOKEN from env vars. Never logged. |
| XIV. Human-in-the-Loop | PASS | Write operations gated by ITSM. Reconciliation reports diff before any writes. |
| XV. Backwards Compatibility | PASS | Replaces v1 with superset. All v1 query capabilities preserved. |
| XVI. Spec-Driven Development | PASS | Full SDD workflow. |

## Project Structure

### Documentation (this feature)

```text
specs/027-nautobot-mcp-v2/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── mcp-tools.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
mcp-servers/nautobot-mcp-v2/
├── server.py            # FastMCP server with all 13 tool definitions
├── nautobot_client.py   # GraphQL + REST client (reads and writes)
├── reconcile.py         # Reconciliation logic (diff engine)
├── requirements.txt     # Python dependencies
└── README.md            # MCP server documentation

workspace/skills/nautobot-sot/
└── SKILL.md             # Skill documentation
```

**Structure Decision**: New directory `nautobot-mcp-v2/` alongside the existing `mcp-nautobot/`. The v1 directory is preserved for reference but the openclaw.json entry is updated to point to v2. Three source files: server (tool definitions), client (API communication), reconcile (diff logic).

## Complexity Tracking

> No constitution violations. All principles satisfied by design.
