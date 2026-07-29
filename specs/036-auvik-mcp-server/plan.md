# Implementation Plan: Auvik API MCP Server

**Branch**: `036-auvik-mcp-server` (work branch `claude/epic-heyrovsky-5c9b55`) | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/036-auvik-mcp-server/spec.md`

## Summary

A read-only FastMCP server that proxies the Auvik REST API (JSON:API, HTTP Basic auth) and exposes 20 tools across four themes — inventory, network alerts, lifecycle, performance — plus billing/usage. Operators address assets by name/hostname/IP (a shared resolver maps these to Auvik IDs, returning candidates on ambiguity), and list tools transparently aggregate all result pages by following `links.next`. The server mirrors the established `azure-network-mcp` / `claroty-mcp` layout (`clients/ models/ tools/ utils/`), serializes responses through the TOON shim, and ships with four `SKILL.md` skills and all Principle XI coherence artifacts.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastMCP, httpx (async, `BasicAuth`), python-dotenv; `netclaw_tokens` (TOON, optional import with JSON fallback)
**Storage**: N/A (stateless proxy to Auvik REST API)
**Testing**: pytest + pytest-asyncio; httpx via `respx`/monkeypatched transport (no live API in unit tests)
**Target Platform**: Linux/Windows host, stdio MCP server under OpenClaw
**Project Type**: Single project — MCP server package under `mcp-servers/auvik-mcp/`
**Performance Goals**: Bounded concurrency under `AUVIK_RATE_LIMIT`; full-result correctness within `AUVIK_MAX_PAGES`
**Constraints**: Read-only (no mutations); credentials only from env; stdout reserved for JSON-RPC (logs to stderr)
**Scale/Scope**: 20 tools, 4 skills, ~9 server modules, 12 coherence artifacts

## Constitution Check

*GATE: must pass before Phase 0 and re-checked after design.*

| Principle | Status | Note |
|---|---|---|
| I/II Safety / Read-before-write | ✅ | Read-only server; no device writes. Observation-only by construction. |
| IV Immutable Audit (GAIT) | ✅ | Session GAIT log maintained + committed each turn; session ends with summary commit. |
| V MCP-Native | ✅ | FastMCP stdio, standard lifecycle. |
| VI Multi-vendor neutrality | ✅ | Vendor-specific Auvik logic isolated in its own server. |
| VII/XII Skill modularity + docs-as-code | ✅ | 4 single-purpose skills, each with `SKILL.md`. |
| IX Security by default | ✅ | Least privilege (read-only API role); no elevated perms. |
| X Observability | ✅ | HUD node added; server exposes `auvik_verify_credentials` health tool. |
| XI Full-Stack Artifact Coherence | ⏳ | Tracked in [checklists/requirements.md](./checklists/requirements.md); completed before merge. |
| XIII Credential Safety | ✅ | `AUVIK_*` from env only; `.env.example` documents without values; `.env` git-ignored. |
| XIV Human-in-the-loop | ✅ | No external-comms or mutation tools. |
| XV Backwards compatibility | ✅ | New isolated package; no shared-interface changes. SC-004 regression check. |
| XVI Spec-Driven Development | ✅ | This SDD artifact set. |
| XVII Milestone blog | ⏳ | WordPress draft at completion (or note in session log if MCP unavailable). |

**No violations** → Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)
```text
specs/036-auvik-mcp-server/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/mcp-tools.md
├── tasks.md
├── checklists/requirements.md
└── gait-session-log.md
```

### Source code (repository root)
```text
mcp-servers/auvik-mcp/
├── auvik_mcp_server.py        # entrypoint: FastMCP("auvik-mcp"), env load + fail-fast, register 20 tools, mcp.run()
├── clients/
│   ├── __init__.py
│   └── auvik_client.py        # async httpx BasicAuth client: get(), get_all() (auto-paginate links.next), 429/Retry-After
├── models/
│   ├── __init__.py
│   └── responses.py           # dataclasses per entity + to_dict()/to_json() (TOON)
├── tools/
│   ├── __init__.py
│   ├── inventory.py           # devices, networks, interfaces, components, tenants, entity notes/audits, usage, verify
│   ├── alerts.py              # alerts
│   ├── lifecycle.py           # lifecycle, warranty, configurations
│   └── performance.py         # device/interface/service/component/oid stats, snmp poller settings + history
├── utils/
│   ├── __init__.py
│   ├── constants.py           # base URL default, enum vocabularies (statId/interval/componentType/deviceType…)
│   ├── pagination.py          # cursor walk helper used by client.get_all()
│   ├── rate_limiter.py        # sliding-window limiter + Retry-After parsing
│   ├── resolver.py            # name/IP/partial → Auvik ID; ambiguity candidates; ID-shape detection; tenant-scoped
│   └── toon_helper.py         # gcf_dumps() with JSON fallback
├── requirements.txt
├── README.md
└── .env.example

workspace/skills/
├── auvik-inventory/SKILL.md
├── auvik-network-alerts/SKILL.md
├── auvik-lifecycle/SKILL.md
└── auvik-performance/SKILL.md

tests/auvik-mcp/                # pytest (resolver, pagination, client, tool param-mapping, read-only assertion)
```

**Structure Decision**: Single MCP-server package mirroring `azure-network-mcp`. Split by responsibility — transport (`clients/`), shaping (`models/`), cross-cutting behavior (`utils/`), and one tool module per theme (`tools/`) so each file stays focused and independently testable.

## Phases

- **Phase 0 — Research** ✅ ([research.md](./research.md)): API surface, conventions, gotchas, decisions (D1–D6). No open clarifications.
- **Phase 1 — Design** ✅: [data-model.md](./data-model.md), [contracts/mcp-tools.md](./contracts/mcp-tools.md), [quickstart.md](./quickstart.md).
- **Phase 2 — Tasks** → [tasks.md](./tasks.md): dependency-ordered TDD tasks (utils → client → models → tools → server → skills → coherence → verify).
- **Phase 3 — Implement**: execute tasks; per-task tests + commits.
- **Phase 4 — Coherence**: complete [checklists/requirements.md](./checklists/requirements.md) (Principle XI), regression check (SC-004).
- **Phase 5 — Review/Blog**: PR review vs constitution; WordPress milestone draft (XVII); final GAIT summary commit.
