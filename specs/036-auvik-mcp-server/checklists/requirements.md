# Requirements & Coherence Checklist: Auvik MCP (036)

**Status: COMPLETE** (pending only an optional operator-run live smoke against a real Auvik tenant). 348 unit tests passing.

## A. Full-Stack Artifact Coherence (Constitution Principle XI)

- [x] **mcp-servers/auvik-mcp/** created — server, `clients/`, `models/`, `tools/`, `utils/`, `requirements.txt`.
- [x] **mcp-servers/auvik-mcp/README.md** — tool inventory (20), env vars, transport (stdio), install, read-only note.
- [x] **config/openclaw.json** — `"auvik-mcp"` registered (`python3 -u …/auvik_mcp_server.py`; all 7 `AUVIK_*` env with shell defaults). JSON validated.
- [x] **.env.example** — `AUVIK_*` block, descriptive comments, **no values**.
- [x] **scripts/install.sh** — step 48b mirrors the in-repo python-MCP pattern (`pip install -r requirements.txt`); `TOTAL_STEPS` bumped 55→56.
- [x] **ui/netclaw-visual/server.js** — `INTEGRATION_CATALOG` Auvik entry + `ENV_MAP` `auvik` entry. `node --check` passes.
- [x] **README.md** — MCP row added (74); 4-skill section added; counts bumped (MCP 73→74 & intro 67→68; skills 126→130 & intro 113→117).
- [x] **SOUL.md** — Auvik skills line added; counts bumped (skills 164→168, MCP 87→88).
- [x] **SOUL-SKILLS.md** — 4 `### auvik-*` procedure blocks added.
- [x] **TOOLS.md** — Connection Details line for Auvik.
- [x] **workspace/skills/auvik-inventory/SKILL.md** created.
- [x] **workspace/skills/auvik-network-alerts/SKILL.md** created.
- [x] **workspace/skills/auvik-lifecycle/SKILL.md** created.
- [x] **workspace/skills/auvik-performance/SKILL.md** created.
- [x] **.gitignore** — `!mcp-servers/auvik-mcp/` (server is git-ignored-by-default like its peers; explicitly tracked).
- [ ] **CLAUDE.md / AGENTS.md** — optional (not in the XI list); left to the auto-generated SDD context refresh.
- [x] **specs/036-auvik-mcp-server/gait-session-log.md** — kept current; final summary commit (Principle IV).
- [x] **Existing skills verified unbroken** (SC-004) — `openclaw.json` valid; `suzieq` server still parses.
- [x] **WordPress milestone blog drafted** (Principle XVII) — `docs/blog/2026-06-21-auvik-mcp.md`; WordPress MCP unavailable in this shell → publish manually (noted in GAIT log).

## B. Requirement coverage (spec FR → implemented)

- [x] FR-001..007 (inventory) → `tools/inventory.py` (9 tools) · FR-008/009 (alerts, read-only) → `tools/alerts.py` + server read-only assertions
- [x] FR-010/011 (stats) + FR-012/013 (SNMP poller) → `tools/performance.py` (7 tools)
- [x] FR-014/015/016 (lifecycle) → `tools/lifecycle.py` (3 tools)
- [x] FR-017 (Basic auth) · FR-018 (base URL) · FR-020 (rate limit/429) → `clients/auvik_client.py` + `utils/rate_limiter.py`
- [x] FR-019/019a (pagination) → `client.get_all` + `utils/pagination.py` · FR-021 (TOON) → `utils/toon_helper.py` + `models` · FR-022 (verify) → `auvik_verify_credentials` · FR-023 (lifecycle/no-regress) → server + regression check
- [x] FR-024/025/026 (resolution) → `utils/resolver.py` (used by all entity-scoped tools)

## C. Success-criteria verification (spec SC)

- [x] SC-002 zero writes → server test + source grep (no `.post/.put/.delete/.patch`; no write-verb tool)
- [x] SC-003 rate limiting → `test_rate_limiter.py`, `test_client_429.py`
- [x] SC-004 no regression → `openclaw.json` valid, suzieq parses
- [x] SC-005 coherence complete → Section A
- [x] SC-006 4 skills resolve tools + TOON output → server registration test (20 tools) + skills reference real tools
- [x] SC-007 resolution candidates on ambiguity → `test_resolver.py`
- [x] SC-008 multi-page completeness → `test_client_get_all.py`
- [x] SC-001 name/IP ≤3 turns → unit tests + **live smoke (H3) against a real us2 tenant**: real device/tenant data returned; tenant-name resolution added after smoke found `tenants` needs IDs

## D. Constitution gates
- [x] Read-only confirmed (no POST/PUT/DELETE/PATCH tool or client method).
- [x] Credentials only from env; `.env.example` value-free; server reads env at runtime.
- [x] FastMCP stdio lifecycle; stderr-only logging.
- [x] Spec exists (XVI); GAIT logged (IV); milestone blog drafted (XVII).

## Outstanding (operator)
- ~~**H3 live smoke**~~ — DONE: validated against a real us2 tenant (verify, tenants, devices with full attribute mapping); two fixes landed (empty-200 body, tenant-name resolution). See GAIT Turn 8.
- **Publish** the WordPress blog draft manually (MCP not configured here).
