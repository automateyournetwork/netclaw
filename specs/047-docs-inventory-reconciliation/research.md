# Phase 0 Research: Documentation Inventory Reconciliation

No `NEEDS CLARIFICATION` markers remain in the Technical Context — this feature reuses existing repo conventions throughout. This document records the decisions made and the alternatives considered.

## Decision 1: Counting methodology for skills

**Decision**: Skill count = number of directories under `workspace/skills/` that contain a `SKILL.md` file, excluding `SKILL-SCHEMA.md` (a schema reference file at the top level of `workspace/skills/`, not a skill directory).

**Rationale**: `workspace/skills/` is the single deployed location the runtime agent reads from (per CLAUDE.md and SOUL.md), and every skill directory found there during this session's audit (190 total) contained a `SKILL.md`. Counting `SKILL.md` presence rather than raw directory count guards against a future stray non-skill directory (e.g., a `.gitkeep` placeholder or WIP scratch folder) silently inflating the count.

**Alternatives considered**:
- *Count raw directories via `ls | wc -l`*: simplest, matches this session's manual audit exactly, but has no protection against non-skill directories being miscounted. Rejected in favor of the `SKILL.md`-presence check, which is one `os.path.exists` check more robust for near-zero extra cost.
- *Parse skill metadata from `ui/netclaw-visual/server.js`'s `parseSkills()`*: would guarantee the script and the HUD always agree by construction, but couples a documentation-verification script to a Node.js UI module and requires a JS runtime or JS-parsing logic in Python. Rejected as unnecessary coupling — both independently reading the same source directory (`workspace/skills/`) is sufficient to keep them in agreement, and simpler to maintain.

## Decision 2: Counting methodology for MCP integrations

**Decision**: MCP integration count = (top-level entries in `config/openclaw.json` under `mcpServers` — confirmed during implementation to already be fully individually registered, e.g. the Check Point suite's 15 `chkp-*` servers are 15 separate top-level keys, not one bundle needing expansion, even though they share a single vendored directory `checkpoint-mcp-servers/` under `mcp-servers/`) **plus** an explicitly maintained list in the script of externally-installed servers that ship with NetClaw's supported integration set but are not present in `config/openclaw.json` at all (installed via pip/npm/Docker at runtime instead: pyATS, F5, Catalyst Center, ACI, ISE, NetBox, community Nautobot, Itential, ServiceNow, Microsoft Graph, GitHub, Packet Buddy, CML, NSO, FMC, Meraki, ThousandEyes ×2, RADKit, AWS ×6, GCP ×4, and roughly 30 more — confirmed against README's MCP Servers table and the `mcp-servers/` vendored directories during implementation; see the script's `EXTERNAL_INTEGRATIONS` list for the definitive current set).

**Rationale**: `config/openclaw.json` is the closest thing to a single source of truth for *registered* servers, but this session's audit already proved it undercounts the real total (49 entries there vs. README's own table already documenting more) because some servers are intentionally not registered there — they're installed on demand via `pip`/`npx`/`docker` per their README installation instructions. A pure `config/openclaw.json` count would still under-report and repeat the exact drift this feature exists to fix. The explicit-list approach makes the "not in config, but real" set visible and auditable in one place (the script itself) rather than scattered across prose.

**Alternatives considered**:
- *Count only `config/openclaw.json` entries*: simplest, fully automatable, zero maintenance — but factually wrong today (undercounts by the externally-installed servers), and would misrepresent real capability the same way the current README does. Rejected.
- *Count only `mcp-servers/` vendored directories*: also simple, but this population doesn't overlap 1:1 with `config/openclaw.json` either (some vendored directories, like `checkpoint-mcp-servers/`, are one directory representing 15 registered servers; others aren't registered in config at all, e.g. community servers only referenced in README prose). Rejected for the same undercount/overcount risk.
- *Full auto-discovery by grepping README.md's own MCP Servers table*: would avoid a manually maintained list, but makes the script depend on README's prose formatting staying parseable, and circularly trusts the exact document this feature is fixing as its own ground truth. Rejected — a short, explicit, human-reviewed list in the script is more honest about where the "un-registered but real" servers come from and is easy to update in the same PR that adds a new externally-installed integration.

## Decision 3: Script scope and failure mode

**Decision**: `scripts/verify-inventory-counts.py` is a read-only reporting tool. It prints the computed skill count and MCP integration count, and (best-effort) parses the numeric claims out of README.md and SOUL.md to flag any that disagree with the computed totals, exiting non-zero if a disagreement is found. It does not edit files itself.

**Rationale**: Spec.md FR-010 requires "a documented, repeatable procedure... so future documentation updates can be verified without manual recounting" — a verifier, not an auto-editor. Auto-rewriting prose (which contains counts embedded in sentences, not just structured data) risks mangling hand-written copy and is out of proportion to the problem. A verifier that a maintainer runs before merging a doc change is sufficient to catch the drift pattern that caused this spec and spec 038, and is safer.

**Alternatives considered**:
- *Auto-generate the README's MCP/Skills tables from `config/openclaw.json` and `workspace/skills/` metadata*: would prevent table-omission drift permanently, but requires either a templating step wired into CI or a pre-commit hook, and NetClaw's docs currently contain substantial hand-written prose per skill/server (descriptions, tool counts, env vars) that isn't mechanically derivable from directory names alone. Rejected as out of scope for this documentation-focused fix; noted as a possible future enhancement once a verifier is in place and proven useful.
- *A CI check that fails PRs on drift*: valuable long-term, but adding new CI wiring is an infrastructure change beyond "documentation reconciliation," and the constitution's existing Artifact Coherence Checklist (Principle XI) already relies on manual PR review rather than CI gates for this class of check. Rejected for this feature; the script is written so it *could* be wired into CI later without modification.

## Decision 4: Where the script lives and how it's invoked

**Decision**: `scripts/verify-inventory-counts.py`, run as `python3 scripts/verify-inventory-counts.py` from repo root, no arguments, no dependencies beyond the Python 3.10+ standard library.

**Rationale**: Matches every other maintenance script in `scripts/` (`scan-all-mcp-source.py`, `register-all-mcps.py`, `add-skill-licenses.py`) — same language, same invocation style, same directory. No new tooling pattern introduced.

**Alternatives considered**: A Bash equivalent (matching `scan-all-mcps.sh`) was considered, but counting/parsing JSON and doing light text pattern matching against README prose is meaningfully easier and more maintainable in Python with its standard `json` and `re` modules than in Bash/`jq`+`grep`. Python was already the majority pattern for scripts doing structured-data work in this directory.
