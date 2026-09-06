# Plan — Spec 119

## Approach

Mirror spec 079 (Globalping): a remote HTTP MCP registered by `url` in
`config/openclaw.json`, an installer component that only registers and
checks a credential, one owning skill, and every documentation surface
`docs/ADDING-AN-MCP.md` lists. No vendored code, no write tools.

## Key decisions

- Config entry, not `EXTERNAL_INTEGRATIONS` (research R1) — avoids the
  double-count that `thousandeyes-official-mcp` carries.
- `PROFILE_MULTIVENDOR` only, per roadmap note — IGP link-state analysis is
  a multivendor-network concern, not a baseline install.
- Consume the upstream read-only surface; scope further client-side with
  `defenseclaw tool allow`.

## Tasks

1. **Upstream** — land `TOPOLOGRAPH_MCP_READ_ONLY` in `topolograph-mcp-server`
   (read-only default, mutation tools hidden). → verify: `tools/list` in the
   default mode contains no `upload_graph`/`*_lsp`.
2. **config/openclaw.json** — add `topolograph-mcp` with `url` +
   `Authorization: Bearer ${TOPOLOGRAPH_API_TOKEN}`. → verify:
   `verify-catalog-coverage.py` still passes; key strips to catalog id.
3. **catalog.sh** — add `topolograph|Observability|Topolograph|...` entry;
   add `topolograph` to `PROFILE_MULTIVENDOR`. → verify: `reconcile-mcp.py
   --surface catalog` passes.
4. **install-steps.sh** — `component_install_topolograph()`: no download,
   registration + `TOPOLOGRAPH_API_TOKEN` presence check (globalping shape).
5. **Docs surfaces** — README MCP Servers table row + `## MCP Servers (N)` +
   both prose counts; SOUL.md identity line counts + cross-ref +
   `### IGP Topology Analysis — Topolograph (1)` capability section;
   `.env.example` block; `TOOLS.md` env-var line + detail section; HUD node
   list + annotation map in `ui/netclaw-visual/server.js`. → verify:
   `verify-inventory-counts.py` PASS.
6. **Skill** — `workspace/skills/topolograph-igp-analysis/SKILL.md`:
   tool catalogue, `defenseclaw tool allow` allowlist, routing boundary vs
   platform routing skills, read-only note. → verify: skill dir counted,
   counts bumped.
7. **Gate** — `python3 scripts/reconcile-mcp.py` exits 0;
   `python3 scripts/verify-spec-artifacts.py` passes.

## Deferred (research R4)

Manifest token-count measurement (read-only vs full) and the functional
acceptance matrix against a live Topolograph + MongoDB + Docker stack.
