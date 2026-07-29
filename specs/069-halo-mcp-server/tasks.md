# Tasks — Halo (HaloPSA / HaloITSM) MCP Server

Dependency-ordered task list. Items marked **[parallel-safe]** can run in parallel with each other; sequential items must complete first. Checked boxes are done on branch `069-halo-mcp-server`; unchecked boxes are the remaining coherence/skills/tests/milestone tail.

## Phase 1: Foundation

- [x] T-001 Create branch `069-halo-mcp-server` from `main`.
- [x] T-002 Scaffold `mcp-servers/halo-mcp/` layout (`tools/`, `clients/`, `models/`, `utils/`, `__init__.py` per package).
- [x] T-003 `requirements.txt` (`fastmcp>=2.0.0`, `httpx>=0.27.0`, `python-dotenv>=1.0.0`).
- [x] T-004 `mcp-servers/halo-mcp/.env.example` — 5 core `HALO_*` vars + 6 commented tuning vars.

## Phase 2: Utilities

- [x] T-005 [parallel-safe] `utils/constants.py` — `API_PREFIX`, `AUTH_TOKEN_PATH`, `DEFAULT_SCOPE/PAGE_SIZE/MAX_PAGES/TIMEOUT`, Halo-vocabulary docstring (Faults / Request Types / Devices / FieldInfo).
- [x] T-006 [parallel-safe] `utils/pagination.py` — `extract_list()` (items + record_count from a Halo page).
- [x] T-007 [parallel-safe] `utils/rate_limiter.py` — `SlidingWindowRateLimiter` + `parse_retry_after()`.
- [x] T-008 [parallel-safe] `utils/toon_helper.py` — TOON serialization shim (`gcf_dumps`, JSON fallback).
- [x] T-009 `utils/resolver.py` — name→id resolution (exact→substring; `Resolution`, `resolve_or_error`, `looks_like_id`, `resolve_ticket_type/client/site/asset`).

## Phase 3: Client + models

- [x] T-010 `clients/halo_client.py` — async httpx client: OAuth2 **client-credentials** token acquire/cache/refresh, `get()`, `get_all()` (page paging), `post()` (array body), 401 single-refresh retry, 429 `Retry-After` backoff, structured `{success,data,error}` envelope.
- [x] T-011 `models/responses.py` — curated dataclasses: `Ticket`, `TicketType`, `TicketTypeField`, `FieldInfo`, `CustomField`, `Asset`, `Action`, `Client`, `Site`, `User`, `Contract`, `KBArticle` + `to_dict`/`to_json`/`_g` helpers.

## Phase 4: Tools

- [x] T-012 `tools/_common.py` — `_build_params`, `_single_result`, `_list_result`, error envelopes (`ValidationError | Ambiguous | NotFound | UpstreamError`).
- [x] T-013 [parallel-safe] `tools/ticket_types.py` — `halo_list_ticket_types`, `halo_get_ticket_type` (field-schema read).
- [x] T-014 [parallel-safe] `tools/fields.py` — `halo_list_fields`, `halo_get_field`.
- [x] T-015 [parallel-safe] `tools/tickets.py` — `halo_get_ticket`, `halo_list_tickets`, `halo_get_ticket_actions`, `halo_get_asset_tickets`, and **`halo_create_change_request`** (the confirm-before-submit gated write; `_normalize_custom_fields` into `customfields[{id|name,value}]`).
- [x] T-016 [parallel-safe] `tools/assets.py` — `halo_get_asset`, `halo_list_assets`, `halo_get_asset_relationships`.
- [x] T-017 [parallel-safe] `tools/context.py` — `halo_list_clients`, `halo_list_sites`, `halo_list_users`, `halo_list_contracts`.
- [x] T-018 [parallel-safe] `tools/knowledge.py` — `halo_list_kb_articles`, `halo_get_kb_article`.

## Phase 5: Server entry

- [x] T-019 `halo_mcp_server.py` — FastMCP entry; env read at load; lazy singleton `HaloClient` with fail-fast config validation; 18 `@mcp.tool()` wrappers; `TOOL_FUNCS` + `REGISTERED_TOOL_NAMES` exports; `mcp.run()` (stdio); logging to stderr only.

## Phase 6: Per-MCP documentation

- [x] T-020 `mcp-servers/halo-mcp/README.md` — tool inventory, transport/auth, env-var table, install/configure/run, change-request safety section, deferred scope.

## Phase 7: SDD spec (Principle XVI)

- [x] T-021 `specs/069-halo-mcp-server/{spec,plan,research,data-model,quickstart,tasks}.md`, `contracts/mcp-tools.md`, `checklists/requirements.md`, `gait-session-log.md`.

## Phase 8: Skills (Principle VII)

- [x] T-022 [parallel-safe] `workspace/skills/halo-change-request/SKILL.md` — the per-org flow: discover → confirm → remember (Memory MCP) → learn fields → assemble → confirm-before-submit → create.
- [x] T-023 [parallel-safe] `workspace/skills/halo-asset-context/SKILL.md` — review an asset (Device) with its related tickets + CMDB/CI relationships (read-only).
- [x] T-024 [parallel-safe] `workspace/skills/halo-ticket-context/SKILL.md` — review a ticket's resolution context: detail, action/note history, linked assets, related KB (read-only).

## Phase 9: Coherence (Principle XI)

- [x] T-025 `config/openclaw.json` — register `halo-mcp` under `mcpServers`.
- [x] T-026 `.env.example` (repo root) — append the `HALO_*` vars.
- [x] T-027 `.gitignore` — un-ignore `mcp-servers/halo-mcp/` sources as needed.
- [x] T-028 `scripts/lib/catalog.sh` — add the Halo component to the installer catalog.
- [x] T-029 `scripts/lib/install-steps.sh` — add the Halo MCP install step.
- [x] T-030 `ui/netclaw-visual/server.js` — add Halo to `INTEGRATION_CATALOG` + `ENV_MAP`.
- [x] T-031 `README.md` (root) — bullet under "What It Does"; new MCP-server table row; bump counts.
- [x] T-032 `TOOLS.md` — Halo section listing the 18 tools.
- [x] T-033 `SOUL.md` — new "Halo ITSM Skills (3)" section.
- [x] T-034 `SOUL-SKILLS.md` — three new procedure blocks.

## Phase 10: Tests

- [x] T-035 Unit tests (`tests/halo-mcp/`) — resolver (exact/substring/ambiguous/not-found/id-passthrough), pagination/`get_all`, client, ticket-types, fields, and ticket tools against `REGISTERED_TOOL_NAMES`.
- [x] T-036 Gated-write test — `halo_create_change_request(submit=false)` makes **zero** HTTP writes and returns the exact preview body; `submit=true` posts the array body (via injected transport).

## Phase 11: Verification

- [x] T-037 Offline component smoke — config fail-fast on missing `HALO_BASE_URL`/`HALO_CLIENT_ID`/`HALO_CLIENT_SECRET`; `python -m compileall` clean; 18 tools registered; resolver + gated-write preview verified with a mock transport.
- [ ] T-038 Live end-to-end smoke against a Halo tenant (needs a client-credentials app) — auth/read (Smoke #1–2), change preview (Smoke #3), change submit (Smoke #4), field discovery (Smoke #5).
- [ ] T-039 Regression — `git diff --stat main` shows zero deletions; only Halo additions + coherence files touched; `config/openclaw.json` re-validated as JSON.

## Phase 12: Milestone

- [ ] T-040 WordPress milestone blog draft (`docs/blog/2026-07-24-halo-mcp.md` if the WordPress MCP is unavailable) — Principle XVII. Present for review before publishing.
- [x] T-041 GAIT session log at `specs/069-halo-mcp-server/gait-session-log.md` (Principle IV).
- [ ] T-042 Commit on `069-halo-mcp-server` (feature + GAIT log) and open PR.

## Auto-regenerated (don't hand-edit)

- [ ] T-043 `DefenseClawMCPScan.md` — re-run `defenseclaw mcp scan` after merge.
- [ ] T-044 `DefenseClawSkillScan.md` — re-run `defenseclaw skill scan` after merge.
