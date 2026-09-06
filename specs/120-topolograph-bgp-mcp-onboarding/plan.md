# Plan — Spec 120

## Approach

Same registration, new documentation and a new skill. No `config/openclaw.json`
change, no new catalog id, no new credential — this is a tool-surface growth
on an already-onboarded remote MCP (spec 119), not a new integration.

## Key decisions

- Second skill (`topolograph-bgp-analysis`), not a section bolted onto
  `topolograph-igp-analysis` (research R4) — different control plane,
  different question domain, keeps each skill's boundary section legible.
- Document against the reviewed upstream PR branch rather than waiting for
  merge (research R6) — same precedent as spec 119's `READ_ONLY` docs.
- `catalog.sh`/`install-steps.sh` get description-string updates only (same
  component id `topolograph`), not new entries.

## Tasks

1. **`workspace/skills/topolograph-bgp-analysis/SKILL.md`** — tool
   catalogue (14 tools), `defenseclaw tool allow` allowlist, boundary vs
   `topolograph-igp-analysis` and vs the platform routing skills' live BGP
   RIB view, read-only note, "snapshot not the wire" caveat matching spec
   119's skill. → verify: skill dir counted by
   `scripts/verify-inventory-counts.py`.
2. **`TOOLS.md`** — new `## Topolograph BGP Topology Analysis` section
   mirroring the existing IGP one's table format. → verify: manual read,
   no automated check owns prose content here.
3. **`README.md`** — MCP Servers table row (line ~641) and prose list entry
   (line ~675) tool count `13` → `27`, description mentions BGP; `## Skills
   (N)` heading and both numeric "N skills" prose claims incremented by 1.
4. **`SOUL.md`** — new `### BGP Topology Analysis — Topolograph (2)`
   capability section (numbered as the second Topolograph-sourced skill,
   matching the existing `(1)` on the IGP section); identity-line and
   cross-reference skill counts incremented by 1.
5. **`catalog.sh` / `install-steps.sh`** — extend the existing `topolograph`
   entry's description string and the installer's echo lines to mention BGP
   topology (sessions, routes, VRF/VPN) alongside IGP. Same component id,
   no new `component_install_*` function.
6. **Gate** — `python3 scripts/reconcile-mcp.py` exits 0;
   `python3 scripts/verify-spec-artifacts.py` passes;
   `python3 scripts/verify-inventory-counts.py` PASS at skill count +1,
   MCP integration count unchanged.

## Deferred (research R5)

Manifest token-count measurement and the functional acceptance matrix
against a live Topolograph + BMP watcher + MongoDB stack — same deferral
spec 119 already carries for its own tool surface.
