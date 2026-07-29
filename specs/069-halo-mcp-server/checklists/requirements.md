# Coherence Checklist — Halo (HaloPSA / HaloITSM) MCP Server

Per Constitution Principle XI (Full-Stack Artifact Coherence, NON-NEGOTIABLE), every box below must be ticked before the PR can merge. Status reflects branch `069-halo-mcp-server` as of this writing: the server, per-MCP docs, SDD spec, the three skills, the repo-wide coherence wiring, and the test suite are complete; the live-tenant smoke, regression diff, and the milestone blog are the remaining tail.

## Code

- [x] `mcp-servers/halo-mcp/halo_mcp_server.py` — FastMCP entry registering 18 tools (17 read + 1 gated write)
- [x] `mcp-servers/halo-mcp/clients/halo_client.py` — async REST client (OAuth2 client-credentials, page paging, 401 refresh, 429 backoff)
- [x] `mcp-servers/halo-mcp/tools/{_common,ticket_types,fields,tickets,assets,context,knowledge}.py`
- [x] `mcp-servers/halo-mcp/models/responses.py` — curated dataclasses + serialization helpers
- [x] `mcp-servers/halo-mcp/utils/{constants,resolver,pagination,rate_limiter,toon_helper}.py`
- [x] `mcp-servers/halo-mcp/requirements.txt`

## Per-MCP documentation

- [x] `mcp-servers/halo-mcp/README.md` — tool inventory, transport/auth, env vars, change-request safety, deferred scope
- [x] `mcp-servers/halo-mcp/.env.example` — 5 core `HALO_*` vars + commented tuning vars

## SDD spec (Principle XVI)

- [x] `specs/069-halo-mcp-server/spec.md`
- [x] `specs/069-halo-mcp-server/plan.md`
- [x] `specs/069-halo-mcp-server/research.md`
- [x] `specs/069-halo-mcp-server/data-model.md`
- [x] `specs/069-halo-mcp-server/contracts/mcp-tools.md`
- [x] `specs/069-halo-mcp-server/quickstart.md`
- [x] `specs/069-halo-mcp-server/tasks.md`
- [x] `specs/069-halo-mcp-server/checklists/requirements.md` (this file)
- [x] `specs/069-halo-mcp-server/gait-session-log.md` (Principle IV)

## Skills (Principle VII)

- [x] `workspace/skills/halo-change-request/SKILL.md` — discover → confirm → remember → learn → assemble → confirm-before-submit → create
- [x] `workspace/skills/halo-asset-context/SKILL.md` — review an asset (Device) with its related tickets + CMDB/CI relationships
- [x] `workspace/skills/halo-ticket-context/SKILL.md` — review a ticket's resolution context: detail, actions, linked assets, KB

## Repo-wide coherence (Principle XI)

- [x] `config/openclaw.json` — `halo-mcp` registered under `mcpServers`
- [x] `.env.example` (repo root) — `HALO_*` vars added
- [x] `.gitignore` — `mcp-servers/halo-mcp/` sources un-ignored as needed
- [x] `scripts/lib/catalog.sh` — Halo component added to the installer catalog
- [x] `scripts/lib/install-steps.sh` — Halo MCP install step
- [x] `ui/netclaw-visual/server.js` — entry in `INTEGRATION_CATALOG` + `ENV_MAP`
- [x] `README.md` (root) — bullet under "What It Does"; new MCP-server table row; count bump
- [x] `TOOLS.md` — Halo MCP section with the 18 tools
- [x] `SOUL.md` — "Halo ITSM Skills (3)" section
- [x] `SOUL-SKILLS.md` — 3 procedure blocks for the new skills

## Tests

- [x] Unit (`tests/halo-mcp/`) — resolver (exact/substring/ambiguous/not-found/id-passthrough), pagination/`get_all`, client, ticket-types, fields, ticket tools; 18-tool registry
- [x] Gated write — `halo_create_change_request(submit=false)` makes zero writes and returns the exact preview body; `submit=true` posts the array body

## Constitution-specific

- [x] Principle I + II + III — exactly one write; it defaults to a no-write preview; the change flow requires field-discovery + review reads first
- [x] Principle V — FastMCP, stdio, JSON-RPC lifecycle
- [x] Principle VIII — the submit path returns `{created, ticket}` echoing the created object for verification
- [x] Principle XIII — `HALO_CLIENT_SECRET` only in env, never logged (startup log omits it), token held in memory; `.env.example` documents without values
- [x] Principle XV — no shared schemas changed; existing MCPs untouched (additive-only)
- [x] Principle XVI — full SDD spec present
- [ ] Principle XVII — WordPress milestone blog post drafted (tracked as T-040)

## Verification (Principle VIII)

- [x] Offline component smoke — config fail-fast on missing required env; `python -m compileall` clean; 18 tools registered; resolver + gated-write preview verified with an injected transport
- [ ] Live end-to-end smoke against a Halo tenant (needs a client-credentials API app) — auth/read, change **preview** (no write), change **submit** (one write), field discovery
- [ ] Regression — `git diff --stat main` = zero deletions; only Halo additions + coherence files touched

## Auto-regenerated (don't hand-edit)

- [ ] `DefenseClawMCPScan.md` — re-run `defenseclaw mcp scan` after merge
- [ ] `DefenseClawSkillScan.md` — re-run `defenseclaw skill scan` after merge
