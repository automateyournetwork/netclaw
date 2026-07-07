# CLI Contract: `scripts/verify-inventory-counts.py`

This feature has no network API. Its one external interface is a command-line contract, documented here in place of an API spec.

## Invocation

```bash
python3 scripts/verify-inventory-counts.py
```

- No required or optional arguments for the default run.
- Must be run from the repository root (paths are resolved relative to the script's own location, not the caller's `cwd`, so it also works if invoked with a full path from elsewhere).
- No environment variables, no `.env` file, no network access required.

## stdout contract

On every run, regardless of pass/fail, the script prints a human-readable report to stdout containing at minimum:

```text
Skill count: <int>
  workspace/skills/ directories with SKILL.md: <int>

MCP integration count: <int>
  config/openclaw.json top-level entries: <int>
  + externally-installed (documented, not in config): <int>

Documentation check: <PASS|FAIL>
  <if FAIL, one line per discrepancy:>
  README.md:<line-or-section> claims <N> skills, computed <M>
  SOUL.md:<line-or-section> claims <N> MCP servers, computed <M>
  ...
```

The exact column widths/formatting are not contractual — only that the three headline numbers (skill count, MCP integration count, PASS/FAIL) are present and human-readable, and that every discrepancy is listed with enough context (file + what was claimed vs. computed) for a maintainer to locate and fix it without re-running a separate diff.

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Computed counts derived successfully AND every parsed documentation claim matches |
| `1`  | Computed counts derived successfully but at least one documentation claim disagrees (drift detected) |
| `2`  | Script could not compute counts at all (e.g., `workspace/skills/` or `config/openclaw.json` missing/unreadable) — an environment problem, not a documentation problem |

## Inputs read (contract with the repository, not a user)

- `workspace/skills/*/SKILL.md` (existence check per directory)
- `config/openclaw.json` (`mcpServers` key)
- A small hardcoded list, maintained inside the script itself, of externally-installed integration names documented in README's MCP Servers table but absent from `config/openclaw.json` (see data-model.md, Entity: MCP Integration, `source: external-documented`). This list is the one piece of the script that requires a human edit when a new externally-installed (non-vendored, non-registered) integration is added — documented as a code comment at the top of the list so future maintainers know to update it in the same PR.
- `README.md` and `SOUL.md` text, for the best-effort discrepancy check (regex-based extraction of numeric claims near the words "skill"/"skills" and "MCP"). This parsing is inherently best-effort against prose; a failure to find an expected claim is reported as an informational note, not a hard error, since prose phrasing can legitimately change.

## Non-goals (explicitly not part of this contract)

- The script does not modify any file.
- The script does not verify `SOUL-SKILLS.md`, `mcp-servers/README.md`, or `ui/netclaw-visual/README.md` table *completeness* (i.e., it does not diff table rows against the computed entity list) — only the two headline-number files (README.md, SOUL.md) get automated discrepancy parsing in this iteration. Table-completeness for the other files is verified manually during the Phase 1 documentation edit pass (tasks.md) and can be added to the script later if drift recurs there.
