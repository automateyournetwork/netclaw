# Tasks — Claroty xDome MCP Server

Dependency-ordered task list. Items marked **[parallel-safe]** can be executed in parallel with each other; sequential items must complete first.

## Phase 1: Foundation

- [x] T-001 Create branch `035-claroty-mcp` from `main`.
- [x] T-002 Scaffold `mcp-servers/claroty-mcp/` directory layout (`tools/`, `clients/`, `utils/`, `models/`, `__init__.py` per package).
- [x] T-003 `requirements.txt` (mcp, httpx, python-dotenv, anyio).
- [x] T-004 `.env.example` with 5 CLAROTY_* vars + commented `NETCLAW_LAB_MODE`.

## Phase 2: Utilities

- [x] T-005 [parallel-safe] `utils/gcf_helper.py` — 9-line shim per project convention.
- [x] T-006 [parallel-safe] `utils/itsm_gate.py` — copy of `gnmi-mcp/itsm_gate.py` with module logger renamed and "gNMI Set" reworded to "Claroty write".
- [x] T-007 [parallel-safe] `utils/rate_limiter.py` — `SlidingWindowRateLimiter` (NEW).

## Phase 3: Client + models

- [x] T-008 `clients/claroty_client.py` — async httpx client with Bearer auth, `post()`, `paginate()`, `collect()`, 429+Retry-After backoff, embedded rate gate.
- [x] T-009 `models/responses.py` — Device, Alert, Vulnerability, Site, EdgeLocation, Server, OTActivityEvent, AuditEntry, OrganizationZone dataclasses + `from_xdome_*` mappers.

## Phase 4: Tools

- [x] T-010 [parallel-safe] `tools/devices.py` — `list_devices`, `get_device_details`, `get_device_communication_map`, `set_device_purdue_level`, `set_device_custom_attribute`.
- [x] T-011 [parallel-safe] `tools/alerts.py` — `list_alerts`, `get_alert_with_devices`, `acknowledge_alert`.
- [x] T-012 [parallel-safe] `tools/vulnerabilities.py` — `list_vulnerabilities`, `get_vulnerable_devices`, `set_vulnerability_relevance`.
- [x] T-013 [parallel-safe] `tools/sites_edge.py` — `list_sites`, `get_site`, `list_edge_locations`.
- [x] T-014 [parallel-safe] `tools/servers_ot.py` — `list_servers`, `get_server_interfaces`, `list_ot_activity_events`.
- [x] T-015 [parallel-safe] `tools/audit_governance.py` — `get_audit_log`, `list_organization_zones`.
- [x] T-016 [parallel-safe] `tools/user_actions.py` — `label_alerts`, `assign_alerts`.

## Phase 5: Server entry

- [x] T-017 `claroty_mcp_server.py` — FastMCP entry; import all 21 tools; `client.validate_config()` at startup; `mcp.run(transport="stdio")`.

## Phase 6: Skills

- [x] T-018 [parallel-safe] `workspace/skills/claroty-asset-inventory/SKILL.md`.
- [x] T-019 [parallel-safe] `workspace/skills/claroty-risk-triage/SKILL.md`.
- [x] T-020 [parallel-safe] `workspace/skills/claroty-ot-topology/SKILL.md`.

## Phase 7: Documentation

- [x] T-021 `mcp-servers/claroty-mcp/README.md` — tool inventory, env vars, transport, install, ITSM-gate semantics, deferred-scope list.
- [x] T-022 SDD spec: `specs/035-claroty-mcp/{spec,plan,research,data-model,quickstart,tasks}.md`, `contracts/mcp-tools.md`, `checklists/requirements.md`.

## Phase 8: Coherence (Principle XI)

- [x] T-023 `config/openclaw.json` — register `claroty-mcp` under `mcpServers`.
- [x] T-024 `.env.example` (repo root) — append 5 CLAROTY_* vars.
- [x] T-025 `scripts/install.sh` — add a Claroty MCP install step.
- [x] T-026 `ui/netclaw-visual/server.js` — add to `INTEGRATION_CATALOG` and `ENV_MAP`.
- [x] T-027 `README.md` — bullet under "What It Does"; new row in MCP Server table; bump counts.
- [x] T-028 `TOOLS.md` — Claroty section listing the 21 tools.
- [x] T-029 `SOUL.md` — new "Claroty OT Security Skills (3)" section.
- [x] T-030 `SOUL-SKILLS.md` — three new procedure blocks.

## Phase 9: Verification

- [x] T-031 Smoke test in lab mode: offline component smoke (7/7 passed) — config fail-fast on missing `CLAROTY_API_TOKEN`, GCF helper delegates to `netclaw_tokens.gcf_serializer` (JSON fallback when `gcf-python` absent, matching `azure-network-mcp`), ITSM gate reject (empty/bad-format) + accept (lab mode), gated write blocks POST on invalid CR, 21 tools registered, rate-limiter acquire. `python -m compileall` clean; `node --check server.js` and `bash -n install.sh` clean. End-to-end agent smoke (live xDome tenant) still pending — needs a token.
- [x] T-032 Regression smoke: final `git diff --stat main` shows **zero deletions** and touches only Claroty additions + the 9 coherence files — no existing MCP/skill/spec modified. `config/openclaw.json` re-validated as JSON; `azure-network-mcp` GCF helper parity confirmed.

## Phase 9b: Re-base remediation (added during PR prep)

- [x] T-035 Re-based the feature onto current `main` (was cut from PR #63; main had since merged PRs #65–#70). Avoids reverting memory-mcp, IP Fabric, Check Point specs, and the TOON→GCF migration.
- [x] T-036 Renumbered `031-claroty-mcp` → `035-claroty-mcp` (031 was already taken by the merged Check Point integration). Branch, spec dir, and all internal references updated.
- [x] T-037 Migrated serialization from the removed `toon_serializer`/`toon_helper` to `gcf_serializer`/`gcf_helper` (`gcf_dumps`) across all 7 tool modules + docs, matching the repo standard.
- [x] T-038 Re-derived coherence counts against current main: README MCP Servers 73→74 + new row 74; SOUL.md 164→167 skills, 87→88 MCP integrations; install.sh step `50h` (50c was taken); `.gitignore` un-ignore for `mcp-servers/claroty-mcp/`.

## Phase 10: Milestone

- [x] T-033 WordPress blog post drafted at `docs/blog/2026-06-08-claroty-mcp.md` (Principle XVII). **Present to John for review before publishing.**
- [x] T-039 GAIT session log recorded at `specs/035-claroty-mcp/gait-session-log.md` (Principle IV) — reconstructed 031 build trail + Turn 9 PR-prep remediation addendum; corrected an unverified pyats-health-check regression claim.
- [ ] T-034 Commits on `035-claroty-mcp` (feature + GAIT log). **Pending: John pushes / opens PR.**
