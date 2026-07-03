# Coherence Checklist — Claroty xDome MCP Server

Per Constitution Principle XI (Full-Stack Artifact Coherence, NON-NEGOTIABLE), every box below must be ticked before the PR can merge.

## Code

- [x] `mcp-servers/claroty-mcp/claroty_mcp_server.py` — FastMCP entry registering 21 tools
- [x] `mcp-servers/claroty-mcp/clients/claroty_client.py` — async REST client (Bearer, pagination, rate gate)
- [x] `mcp-servers/claroty-mcp/tools/{devices,alerts,vulnerabilities,sites_edge,servers_ot,audit_governance,user_actions}.py`
- [x] `mcp-servers/claroty-mcp/models/responses.py`
- [x] `mcp-servers/claroty-mcp/utils/{itsm_gate,gcf_helper,rate_limiter}.py`
- [x] `mcp-servers/claroty-mcp/requirements.txt`

## Documentation

- [x] `mcp-servers/claroty-mcp/README.md` — tool inventory, env vars, transport, install, ITSM-gate semantics
- [x] `mcp-servers/claroty-mcp/.env.example` — per-MCP env var documentation

## SDD spec (Principle XVI)

- [x] `specs/035-claroty-mcp/spec.md`
- [x] `specs/035-claroty-mcp/plan.md`
- [x] `specs/035-claroty-mcp/research.md`
- [x] `specs/035-claroty-mcp/data-model.md`
- [x] `specs/035-claroty-mcp/contracts/mcp-tools.md`
- [x] `specs/035-claroty-mcp/quickstart.md`
- [x] `specs/035-claroty-mcp/tasks.md`
- [x] `specs/035-claroty-mcp/checklists/requirements.md` (this file)

## Skills (Principle VII)

- [x] `workspace/skills/claroty-asset-inventory/SKILL.md`
- [x] `workspace/skills/claroty-risk-triage/SKILL.md`
- [x] `workspace/skills/claroty-ot-topology/SKILL.md`

## Repo-wide coherence (Principle XI)

- [x] `README.md` — bullet under "What It Does"; new row in MCP server table; bump counts
- [x] `config/openclaw.json` — `claroty-mcp` registered under `mcpServers`
- [x] `.env.example` (repo root) — 5 CLAROTY_* vars added
- [x] `scripts/install.sh` — Claroty MCP install step
- [x] `ui/netclaw-visual/server.js` — entry in `INTEGRATION_CATALOG` + `ENV_MAP`
- [x] `SOUL.md` — "Claroty OT Security Skills (3)" section
- [x] `SOUL-SKILLS.md` — 3 procedure blocks for the new skills
- [x] `TOOLS.md` — Claroty xDome MCP section with the 21 tools

## Constitution-specific

- [x] Principle II + III + VIII — every write tool calls `validate_change_request` before any xDome POST
- [x] Principle V — FastMCP, stdio, JSON-RPC lifecycle
- [x] Principle XIII — `CLAROTY_API_TOKEN` only in env, never logged, never in source
- [x] Principle XV — no shared schemas changed; existing MCPs untouched
- [x] Principle XVI — full SDD spec present
- [ ] Principle XVII — WordPress milestone blog post drafted (tracked as T-033)

## Verification (Principle VIII)

Live smoke against a live customer xDome tenant
(2026-06-08). All structural paths verified; the one ⚠ below is an
xDome RBAC issue, not a wrapper bug.

- [x] Phase A — Sanity reads (sites/devices/alerts/audit_log)
- [x] Phase B — Filter shape + TitleCase status guidance + projection
- [x] Phase C — Lookup-by-id paths (device details, alert-with-devices, communication-map)
- [x] Phase D1/D2 — Edge locations + organisation zones
- [x] Phase D3 — list_vulnerabilities; get_vulnerable_devices fixed
      after surfacing the internal `id` field (was using `name`)
- [x] Phase E1 — ITSM gate regex enforcement (CHG\d+)
- [x] Phase E2 — Local enum pre-flight guard (status/relevance)
- [⚠] Phase E3 — Structural pass: wrapper builds correct body,
      ITSM gate passes, status case-normalised, request reaches xDome.
      End-to-end mutation blocked at xDome RBAC (test token lacks
      write:alerts scope). The structured 403 envelope correctly
      surfaces the response. Not a wrapper bug. Re-run with a
      scoped token to close.
- [x] Rate-limit guard (sliding-window cap)
- [x] HUD entry visible at http://localhost:3000 under Security
- [x] Regression — existing pyats-health-check still passes

## Auto-regenerated (don't hand-edit)

- [ ] `DefenseClawMCPScan.md` — re-run `defenseclaw mcp scan` after merge
- [ ] `DefenseClawSkillScan.md` — re-run `defenseclaw skill scan` after merge
