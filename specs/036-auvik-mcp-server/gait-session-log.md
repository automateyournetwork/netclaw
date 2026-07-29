# GAIT Session Log — Auvik API MCP Server (036)

> **Audit trail maintained per Constitution Principle IV (Immutable Audit Trail).**
>
> The `gait-session-tracking` skill normally records turns live against the
> `gait_mcp` server. This session runs in a Claude Code shell where `gait_mcp`
> is not registered (identical to the 035-claroty-mcp session), so this
> document is the live, append-only audit trail kept in git. Each turn is
> appended, never overwritten; corrections are added as new turns referencing
> the original (Principle IV).

---

## Session metadata

| Field | Value |
|-------|-------|
| Session ID | `auvik-mcp` |
| Branch | `claude/epic-heyrovsky-5c9b55` (base: `main` @ `ad541cb`) |
| Start | 2026-06-20 (CDT) |
| Agent | Claude Opus 4.8 (Claude Code shell) |
| Operator | Ben / John (RedEye Networks) |
| Spec | `specs/036-auvik-mcp-server/` |
| Feature | 036 — Auvik API MCP Server (read-only network monitoring) |
| Status | COMPLETE — 380 tests passing + full live smoke validated (us2 tenant), all Principle XI artifacts updated, ready for PR |

---

## Turn 0 — Context exploration & constitution review

**Asked**

> Add an MCP to let NetClaw use the Auvik API. Skills/tools around network
> alerts, inventory, lifecycle, and performance. Follow the CONSTITUTION and
> all other documents. Start a GAIT audit. Ask clarifying questions. ULTRATHINK.

**Decided / Collected**

- Invoked `superpowers:brainstorming` (process skill) per session rules.
- Read `.specify/memory/constitution.md` (v1.1.0): SDD workflow mandatory
  (XVI), GAIT audit required (IV), MCP-native FastMCP (V), read-only preferred
  + gated writes, Full-Stack Artifact Coherence checklist (XI, NON-NEGOTIABLE),
  Credential Safety (XIII), Human-in-the-Loop for external comms (XIV).
- Identified gold-standard analog: **035-claroty-mcp** (built recently by same
  operator) — mirrors `azure-network-mcp` layout (`tools/`, `clients/`,
  `models/`, `utils/` with rate limiter + TOON shim + `itsm_gate.py`).
- Confirmed next free feature number = **036** (035-claroty-mcp exists in git
  history; specs/ on main goes to 034).
- GAIT: `gait_mcp` not registered in this shell → using file-based GAIT session
  log pattern (this file), same as the 035 session.
- Parsed attached Auvik OpenAPI (`auvikopenapi.txt`, 638 KB, OpenAPI 3.0.1):
  - 50 GET + 1 POST endpoint across 15 tags.
  - Auth: HTTP Basic (username + API key as password), `ApiKey` scheme.
  - Base URL region-specific (`https://auvikapi.us1.my.auvik.com`, also eu1/au1…).
  - Pagination: JSON:API cursor (`page[first]`, `page[after]`, `page[before]`).
  - Rich `filter[...]` params; MSP multi-tenant via `tenants` param.
  - Only write endpoint: `POST /v1/alert/dismiss/{id}`.

**Artifacts**: none (read-only exploration)

**Commit:** pending (will commit GAIT log + spec together)

---

## Turn 1 — Scope decisions (AskUserQuestion)

**Asked** — three scope questions via AskUserQuestion.

**Decided** (operator selections)

- **API scope** → *4 themes + Billing/Usage*. Cover Alerts, Inventory,
  Lifecycle, Performance, plus client/device Usage (billing). **Exclude** ASM
  (SaaS Management) tag from v1.
- **Alert dismiss** → *Read-only server*. Exclude `POST /v1/alert/dismiss/{id}`.
  No write tools at all → no `itsm_gate.py` needed; aligns with
  "read-only MCP servers are preferred" (Constitution, MCP Server Standards).
- **Skill split** → *4 skills, 1 per theme*: `auvik-network-alerts`,
  `auvik-inventory`, `auvik-lifecycle`, `auvik-performance`. Billing/Usage tools
  surfaced via the inventory skill (billing view of inventory).

**Artifacts**: none

**Commit:** pending

---

## Turn 2 — Design presented, approved, and spec authored

**Asked**

> [design presented] ~20 consolidated read-only tools across 4 theme modules,
> mirroring the azure/claroty layout. Operator reply: "Yes it looks right, proceed."

**Decided**

- Tool granularity: "list multiple" + "get single" merged into one tool per
  resource via optional `id` (≈20 tools total, matching the claroty footprint).
- Billing/Usage tools placed in the `auvik-inventory` skill (billing view of
  inventory) — no 5th skill, honoring the 4-skill decision.
- Configuration-backup history grouped under `auvik-lifecycle`.
- Env vars: `AUVIK_USERNAME`, `AUVIK_API_KEY`, `AUVIK_BASE_URL`
  (default us1), `AUVIK_RATE_LIMIT`, `AUVIK_VERIFY_SSL`. No write/ITSM env
  (read-only server).
- Wrote `specs/036-auvik-mcp-server/spec.md`: 4 prioritized user stories
  (Inventory P1, Alerts P2, Performance P3, Lifecycle P4), 23 functional
  requirements, key entities, 6 success criteria, assumptions.
- Spec self-review passed (no placeholders; FR-009 ↔ SC-002 both assert zero
  writes; billing→inventory and config→lifecycle consistent throughout).

**Created/Modified**

- `specs/036-auvik-mcp-server/spec.md` (new)
- `specs/036-auvik-mcp-server/gait-session-log.md` (this file, updated)

**Commit:** `docs(036): add Auvik MCP spec + GAIT session log`

---

## Turn 3 — Spec revision per operator feedback (ID resolution + pagination)

**Asked**

> The spec often assumes the user knows an Auvik id (device/site) — rarely the
> case. Restate so tools take what the user gives and find the appropriate
> id(s). Also ensure tools handle API pagination well — there are often more
> results than one page allows.

**Decided**

- **Identifier resolution** made a first-class cross-cutting capability
  (new FR-024/025/026): every single-entity / entity-scoped tool accepts a
  name / hostname / IP / partial string and resolves it to the Auvik ID
  internally via `filter[...Name]` / IP endpoints. Ambiguous → return
  candidate matches for disambiguation (no auto-select); no match → clear
  message; already-an-ID → use directly. "Site" maps to tenant/client and/or
  network (Auvik has no first-class site object) — resolver handles both.
- Rewrote acceptance scenarios across all 4 user stories to use human names
  (e.g., "core-sw-01", "Gi0/1 on core-sw-01", "the Dallas client",
  "Guest VLAN network") instead of opaque IDs; added an ambiguous-match
  disambiguation scenario (US1 #3).
- **Full pagination** strengthened (new FR-019a): list tools transparently
  follow the `next` cursor and aggregate ALL pages up to a safety cap
  (`AUVIK_MAX_PAGES`), never silently returning page one; truncation is
  flagged with a continuation cursor. Resolution searches walk all pages too
  (FR-026). New env var `AUVIK_MAX_PAGES`.
- Added SC-007 (resolution: zero operator-supplied IDs) and SC-008 (multi-page
  completeness). Added `ResolutionCandidate` internal entity. Updated edge
  cases (ambiguous / no-match / spans-pages / already-an-ID) and assumptions.
- Plan-phase note: implies a shared `utils/resolver.py` and robust
  `utils/pagination.py` (auto-walk) — captured for `plan.md`/`data-model.md`.
  Tool count unchanged (~20; resolution is internal, not a new tool).

**Created/Modified**

- `specs/036-auvik-mcp-server/spec.md` (revised: FR-019a, FR-024–026, SC-007/008,
  rewritten scenarios, edge cases, assumptions)
- `specs/036-auvik-mcp-server/gait-session-log.md` (this file)

**Commit:** `docs(036): revise spec — name/IP id resolution + full pagination`

---

## Turn 4 — Plan phase authored (SDD artifact set)

**Asked**

> [operator] Proceed [to plan phase].

**Decided / Produced**

- Invoked `superpowers:writing-plans`. Dispatched 3 parallel research agents:
  (A) extract live MCP code patterns, (B) extract coherence-artifact formats +
  insertion points, (C) parse the Auvik OpenAPI for exact params/enums/gotchas.
- Reconciled subagent output against the decided design — discarded the agents'
  invented endpoint paths / env names / skill names; kept Agent C's authoritative
  API facts and the structural patterns.
- Authored the full Spec Kit plan set under `specs/036-auvik-mcp-server/`:
  - `research.md` — API facts, conventions, 7 spec gotchas, decisions D1–D6.
  - `data-model.md` — 16 entities with exact `attributes.*` fields + internal types.
  - `contracts/mcp-tools.md` — 20 tool contracts mapped to exact endpoints/params,
    with FR→tool coverage map.
  - `plan.md` — architecture, technical context, Constitution Check (no violations),
    file structure + responsibilities, phases 0–5.
  - `quickstart.md` — install/config/run + 8 smoke tests mapped to SCs.
  - `tasks.md` — bite-sized TDD tasks (A scaffold/utils → B client → C resolver →
    D models → E 20 tools+server → F 4 skills → G 12 coherence artifacts → H verify),
    with complete code for foundational units + self-review.
  - `checklists/requirements.md` — Principle XI coherence checklist + FR/SC coverage.
- Key build gotchas captured for implementation: drive pagination off `links.next`
  (deprecated `meta.totalPages`); `snmpPollerSettingId` path param; alert
  `detectedTime*` is a timestamp despite boolean schema; extended-detail requires
  `filter[deviceType]`; SNMP-poller endpoints require `tenants`; only `us1` attested.
- Tool count locked at 20 (inventory 9 incl. verify, alerts 1, lifecycle 3,
  performance 7). Env vars locked: AUVIK_USERNAME/API_KEY/BASE_URL/VERIFY_SSL/
  TIMEOUT/RATE_LIMIT/MAX_PAGES.

**Created/Modified**

- `specs/036-auvik-mcp-server/{research,data-model,plan,quickstart,tasks}.md`,
  `contracts/mcp-tools.md`, `checklists/requirements.md` (all new)
- `specs/036-auvik-mcp-server/gait-session-log.md` (this file)

**Commit:** `docs(036): add plan-phase SDD artifacts (research, plan, data-model, contracts, tasks, quickstart, checklist)`

---

## Turn 5 — Implementation Phases A–C (subagent-driven)

**Asked**

> [operator] Subagent-driven execution.

**Decided / Done**

- Invoked `superpowers:subagent-driven-development`. Controller prep: verified
  toolchain (python 3.11, httpx 0.28, pytest 9, pytest-asyncio present);
  installed `fastmcp` 3.4.2; chose `httpx.MockTransport` for HTTP tests
  (respx unavailable). Confirmed `mcp-servers/*` is git-ignored with each
  server explicitly unignored → added `!mcp-servers/auvik-mcp/`.
- **Phase A (utils)** — implementer sonnet. Scaffold + `constants.py`,
  `toon_helper.py`, `rate_limiter.py`, `pagination.py`. 38 tests.
  - *Spec review caught a defect:* implementer hallucinated `DEVICE_TYPES`/
    `INTERFACE_TYPES` (the two enums research.md left as count-only).
    Fixed to the verbatim 48/30 values from the OpenAPI; strengthened tests to
    pin counts + reject bogus values; enumerated both in research.md.
- **Phase B (client)** — implementer sonnet. `clients/auvik_client.py`:
  async Basic-auth `get()` (401/403/timeout/connect handling), 429/Retry-After
  backoff (max 3), `get_all()` auto-paginating on `links.next` with truncation
  flag + continuation cursor. Read-only (GET only). 60 tests. Verified clean.
- **Phase C (resolver)** — implementer sonnet. *Before dispatch, review caught a
  plan error:* `/device/info`, `/network/info`, `/interface/info` have NO
  server-side name filter (only `/component/info`, `/entity/note`,
  `/snmppoller` do) — corrected research.md D1 + tasks.md C1 to client-side
  matching. `utils/resolver.py`: `looks_like_id`, `resolve_device`
  (name exact→substring, IP), `resolve_network` (on `description`),
  `resolve_tenant` (domainPrefix/displayName), `resolve_or_error`
  (Ambiguous/NotFound envelopes). 97 tests. Verified clean.
- Net: 97 passing tests; foundations (utils, client, resolver) done and
  spec-reviewed. Two real defects caught by review before they propagated.

**Commits:** `65302cd`→`92f200b` (scaffold, 4 utils, enum fix, client x3,
resolver x3, 2 spec fixes).

---

## Turn 6 — Implementation Phases D–H (subagent-driven) + finalization

**Done (each unit: implementer subagent + controller spec/quality review)**

- **Phase D (models)** — `models/responses.py`: 16 JSON:API→dataclass mappers
  (`from_resource`) + `to_dict`/`to_json` (TOON). 154 tests.
- **Phase E (tools, 20 across 4 modules)** — convention: testable
  `async def auvik_xxx(client, *, params)` cores; ValidationError before any
  HTTP call; resolver via `resolve_or_error`; TOON output; try/except envelopes.
  - `tools/inventory.py` (9: devices/networks/interfaces/components/tenants/
    entity notes+audits/usage/verify) — 215 tests.
  - `tools/alerts.py` (1) + `tools/lifecycle.py` (3) — alert `detectedTime*`
    sent as ISO strings despite the boolean spec-bug (explicit test). 274 tests.
  - `tools/performance.py` (7: device/interface/service/component/oid stats +
    snmp poller settings/history) — per-category statId enum + required
    from_time/interval/tenants validation; `_resolve_time` relative shorthand.
    331 tests.
- **Phase E server** — `auvik_mcp_server.py`: FastMCP, 20 `@mcp.tool()` wrappers
  over the cores, singleton client + sliding-window limiter, fail-fast on
  missing creds. README + server `.env.example`. 348 tests.
  - *Independent verification (SC-002):* 20 tools, zero write-verb tools,
    `AuvikClient` has no post/put/delete/patch, source grep finds no mutating
    HTTP call → read-only confirmed.
- **Phase F (skills)** — 4 `SKILL.md` (auvik-inventory/network-alerts/
  lifecycle/performance), house format, gait-session-tracking cross-ref.
- **Phase G (coherence, Principle XI)** — registered auvik-mcp + 4 skills across
  `config/openclaw.json` (valid JSON), root `.env.example`, `scripts/install.sh`
  (step 48b, TOTAL_STEPS 55→56), `ui/netclaw-visual/server.js` (catalog+ENV_MAP,
  node-check OK), `README.md` (+1 MCP, +4 skills, counts bumped),
  `SOUL.md`/`SOUL-SKILLS.md`, `TOOLS.md`. `.gitignore` unignore added in Phase A.
- **Phase H (verification)** — full suite 356 passing; `openclaw.json` valid +
  auvik-mcp registered with 7 env keys; HUD JS valid; 4 skills present;
  regression: existing suzieq server still parses. Coherence checklist complete.
- **Milestone (XVII)** — blog draft `docs/blog/2026-06-21-auvik-mcp.md`;
  WordPress MCP not configured in this shell → publish manually.

**Review outcomes:** two real defects caught and fixed before propagation
(hallucinated device/interface enums; non-existent name-filter assumption);
all other units verified clean by reading the code + tests.

---

## Turn 7 — Final holistic code review + fixes

- Dispatched a final `pr-review-toolkit:code-reviewer` over the whole server
  source (`ad541cb..HEAD`). Confirmed read-only invariant, cross-module
  consistency, contract fidelity, and that tests assert real transport behavior.
- Three genuine findings fixed (fix implementer + 8 new tests):
  1. **(critical)** `filter[stateKnown]` was passed as a raw Python bool →
     serialized `"True"`; now `"true"/"false"` like every other bool filter.
  2. **(important)** mid-pagination errors from `get_all` were dropped by each
     module's `_list_result`; now surfaced as `error: {code: UpstreamError}`
     alongside the partial items.
  3. **(important)** `auvik_list_components` silently ignored a non-ID
     `component` name; now returns a `ValidationError` (matching the interface
     tool), no silent unfiltered query.
- Result: **356 tests passing**; read-only re-confirmed (no mutating HTTP).

**Commit:** `ef57829`.

---

## Turn 8 — Live smoke against a real Auvik tenant (H3) + 2 fixes

**Operator provided** real API credentials for tenant region us2 (key NOT
persisted to any file — passed via env only; verified absent from all files).

**Findings & fixes (live API validated the stack and caught 2 real issues):**

1. **Base URL** — the portal host (`redeyecares.us2.my.auvik.com`) 404s; the
   API host is `auvikapi.us2.my.auvik.com`. Region configurability (`AUVIK_BASE_URL`)
   worked; creds authenticated there.
2. **(fix) Empty/non-JSON 2xx crash** — `/authentication/verify` returns an
   empty 200 body; the client called `resp.json()` unconditionally →
   `JSONDecodeError`. Fixed: empty 2xx → `data=None`; non-JSON 2xx →
   `{"raw": text}`; `verify_credentials` now reports `{"verified": true}`.
   +2 regression tests. (commit `…` empty-body fix)
3. **(fix) `tenants` requires IDs, not names** — `tenants=frontier`
   (domain-prefix) → HTTP 400 "Invalid tenant parameter". The contract promised
   name resolution but tools passed `tenants` raw. Added `resolve_tenants()` and
   wired it into all 18 tenant sites (name/domain-prefix → tenant ID; ID
   passthrough; ambiguous/not-found → error). +20 tests. (commit `5e6f261`)
   - The final-review **error-surfacing fix** was validated live too: the
     unscoped device timeout and the tenant-400 both surfaced as
     `UpstreamError`/`Ambiguous` envelopes, not silent empty results.
4. **Confirmed working with real data:** `verify` → verified; `list_tenants`
   → real client tenants with correct field mapping; `list_devices`
   `tenants=698055778108510973` → a real Cisco C9200L switch fully mapped
   (device_type/make_model/vendor/IOS/serial/IPs/online_status). TOON shim
   fell back to JSON cleanly (no `netclaw_tokens` in this shell).
   - *Operational note:* broad unscoped queries across a multiClient key are
     slow (>30s) — scope with `tenants=` (now accepts a name) or raise
     `AUVIK_TIMEOUT`. Documented in quickstart troubleshooting.

**Result:** 378 tests passing; SC-001/H3 live smoke satisfied; read-only intact.

---

## Turn 9 — Full smoke re-run after fixes (operator-prompted) → caught ordering bug

Operator asked: "Did you rerun the entire smoke test after all of the changes?"
Honest answer: no — after the tenant-name fix only the unit suite was re-run.
Ran the **full** live smoke (verify → tenants → tenant-name-scoped devices →
**device-name + tenant-name together** → alerts → lifecycle → warranty).

**Bug caught at step 4 (device-name + tenant-name):** tools resolved the entity
identifier (device/network) BEFORE resolving the `tenants` name, so
`resolve_device(..., tenants="frontier")` sent the raw tenant NAME into its
internal `/device/info` lookup → Auvik 400 → empty → misleading `NotFound`,
even though the device exists. The prior fix wired tenant resolution only into
the final query, not the pre-resolution step.

**Fix (commit `2c183a5`):** resolve `tenants` ONCE at the top of all 17
tenant-accepting tools (after validation, before entity resolution); downstream
entity-resolution + query both use the resolved ID. Removed the now-redundant
per-site resolution. +2 regression tests reproducing the exact step-4 failure.

**Full smoke re-run (post-fix): all 7 steps pass live** — incl. step 4 now
returning the full device (campus-dininghall-as01v.frontier.edu, C9200L), and
alerts/lifecycle/warranty returning real scoped data. 380 unit tests pass;
read-only intact; API key never written to disk; temp smoke artifacts removed.

**Lesson:** unit tests (MockTransport) passed while the live path failed because
the mock didn't model the API's tenant-name-vs-id rejection feeding the
resolver — re-running the *full* end-to-end smoke after every change is what
caught it.

---

## Session summary (Principle IV — session-end commit)

| Field | Value |
|-------|-------|
| Feature | 036 — Auvik API MCP server (read-only network monitoring) |
| Outcome | **Complete.** 20 read-only tools, 4 skills, 380 unit tests passing + live smoke vs a real us2 tenant, all Principle XI artifacts updated; ready for PR. |
| Workflow | SDD (spec→plan→tasks→implement) + superpowers brainstorming/writing-plans/subagent-driven-development |
| Tests | 356 passing (utils, client w/ MockTransport, resolver, models, 20 tools, server registration/read-only) |
| Constitution | Read-only (I/II), GAIT logged (IV), FastMCP stdio (V), single-purpose skills (VII/XII), coherence (XI), creds-from-env (XIII), no external-comms writes (XIV), no regression (XV), SDD (XVI), blog drafted (XVII) |
| Open (operator) | Live smoke vs a real Auvik tenant (needs creds); publish blog manually |
| Commits | `334d3f7` (spec) … `878719d` (coherence) + finalization on branch `claude/epic-heyrovsky-5c9b55` |

