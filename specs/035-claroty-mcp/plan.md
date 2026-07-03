# Implementation Plan: Claroty xDome MCP Server

**Branch**: `035-claroty-mcp` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)

## Summary

Add a FastMCP/stdio MCP server (`claroty-mcp`) plus three skills (`claroty-asset-inventory`, `claroty-risk-triage`, `claroty-ot-topology`) that expose 21 tools (15 read + 6 ITSM-gated writes) against the Claroty xDome REST API. All writes validate a ServiceNow CR before calling xDome. All responses serialise via GCF. All required Coherence Checklist artifacts are updated in this same PR.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastMCP (`mcp>=1.0.0`), `httpx>=0.27.0`, `python-dotenv>=1.0.0`, `anyio>=4.0.0`
**Storage**: N/A (stateless proxy to xDome REST API; in-memory rate-limit window only)
**Testing**: smoke test in `quickstart.md` with `NETCLAW_LAB_MODE=true`; integration test deferred to follow-up
**Target Platform**: Linux / macOS / Windows (anywhere openclaw runs)
**Project Type**: MCP server (single Python package under `mcp-servers/claroty-mcp/`)
**Performance Goals**: respect 2000 req/min upstream cap; never surface a 429 to the user under normal load; p95 list_devices latency < 2 s
**Constraints**: stdio JSON-RPC only; no persistent state; credentials only in env vars
**Scale/Scope**: 21 tools, ~600 LOC server + ~250 LOC skills + spec

## Constitution Check

| Principle | How this plan satisfies it |
|-----------|----------------------------|
| **V (MCP-Native)** | FastMCP entry point, stdio transport, JSON-RPC lifecycle handled by FastMCP itself. |
| **II (Read-Before-Write)** | 15 reads ship alongside 6 writes; every write is preceded by a read counterpart (list_alerts before acknowledge, list_vulns before set_relevance, etc.). |
| **III (ITSM-Gated)** | Every write tool calls `validate_change_request` from `utils/itsm_gate.py`, copied verbatim from `gnmi-mcp` so the gate semantics are identical project-wide. |
| **VIII (Verify After)** | Each write tool returns `{"itsm_gate": ..., "applied": ..., "response": ...}` so the caller can verify the xDome side actually committed. |
| **XI (Artifact Coherence)** | All 12 artifact slots covered — see Section "Project Structure" below and `checklists/requirements.md`. |
| **XIII (Credential Safety)** | `CLAROTY_API_TOKEN` read from env only; never logged; `.env.example` documents without values. |
| **XV (Backwards Compat)** | No shared schemas changed; new MCP slot is additive only; existing skills untouched. |
| **XVI (SDD)** | Spec, plan, tasks, data-model, contracts, research, quickstart, checklists all present under `specs/035-claroty-mcp/`. |
| **XVII (Milestone Blog)** | Blog draft tracked as a closing task; if WordPress MCP unavailable, draft saved as markdown for manual publish. |

No principle violations to document under Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/035-claroty-mcp/
├── spec.md              ✓ shipped
├── plan.md              ✓ this file
├── tasks.md             ✓ shipped
├── data-model.md        ✓ shipped
├── research.md          ✓ shipped
├── quickstart.md        ✓ shipped
├── contracts/
│   └── mcp-tools.md     ✓ shipped
└── checklists/
    └── requirements.md  ✓ shipped
```

### Source Code (repository root)

```text
mcp-servers/claroty-mcp/
├── claroty_mcp_server.py
├── clients/claroty_client.py
├── tools/
│   ├── devices.py
│   ├── alerts.py
│   ├── vulnerabilities.py
│   ├── sites_edge.py
│   ├── servers_ot.py
│   ├── audit_governance.py
│   └── user_actions.py
├── models/responses.py
├── utils/
│   ├── itsm_gate.py
│   ├── gcf_helper.py
│   └── rate_limiter.py
├── requirements.txt
├── .env.example
└── README.md

workspace/skills/
├── claroty-asset-inventory/SKILL.md
├── claroty-risk-triage/SKILL.md
└── claroty-ot-topology/SKILL.md
```

**Structure Decision**: Mirror `mcp-servers/azure-network-mcp/` (which has the cleanest `tools/`, `clients/`, `utils/`, `models/` separation) and copy the `gnmi-mcp` ITSM gate verbatim.

## Complexity Tracking

> No constitution violations to justify.
