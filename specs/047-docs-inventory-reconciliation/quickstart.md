# Quickstart: Documentation Inventory Reconciliation

## For a maintainer verifying counts today

```bash
cd /home/johncapobianco/netclaw
python3 scripts/verify-inventory-counts.py
```

Read the printed report. If it says `Documentation check: FAIL`, each listed line tells you which file/section claims a stale number and what the correct number is — go fix that line.

## For a maintainer adding a new skill or MCP server in a future PR

1. Add your skill under `workspace/skills/<name>/SKILL.md` or register your MCP server in `config/openclaw.json` as usual.
2. Update the five canonical documentation files (README.md, SOUL.md, SOUL-SKILLS.md, mcp-servers/README.md, ui/netclaw-visual/README.md) as Principle XI/XII of the constitution already requires.
3. Run `python3 scripts/verify-inventory-counts.py` before opening the PR.
4. If your new integration is installed externally (pip/npm/Docker) rather than registered in `config/openclaw.json`, also add it to the hardcoded external-integration list at the top of `scripts/verify-inventory-counts.py` (the script's docstring/comment marks exactly where) — otherwise it will silently undercount forever, repeating the exact failure mode this feature fixes.
5. Confirm exit code `0` before merging.

## For this feature's own implementation (Phase 2 / tasks.md scope)

1. Write `scripts/verify-inventory-counts.py` per `contracts/verify-inventory-counts-cli.md` and `data-model.md`.
2. Run it once against the current repo state to get the authoritative current numbers (do not hand-recompute from this session's audit — branches may have merged since the spec was written; the script is the source of truth at implementation time).
3. Edit README.md: reconcile all count mentions (header prose, "What It Does" intro, Visual HUD prose, "MCP Servers (N)" heading, "Skills (N)" heading) to the script's output; fill in every missing row in the MCP Servers table and Skills section so zero entities are omitted; explicitly confirm Azure, Batfish, GitLab, and NetFlow/IPFIX as already-shipped.
4. Edit SOUL.md: reconcile both count mentions (the "N skills backed by M MCP servers" line and the separate "N skills" mention) to the script's output.
5. Edit SOUL-SKILLS.md: verify it lists every skill from the computed set; it does not currently make a headline count claim, so no count-text edit is expected, but content should be checked for completeness.
6. Edit mcp-servers/README.md: replace the 12-row partial table with a complete table covering every entity in the MCP Integration set.
7. Edit ui/netclaw-visual/README.md and the README's Visual HUD paragraph: rephrase to state that the HUD computes counts live from the codebase (per `ui/netclaw-visual/server.js`'s existing `parseSkills()`/`INTEGRATION_CATALOG` behavior), rather than asserting a specific static number that will drift again the next time a skill is added.
8. Re-run `scripts/verify-inventory-counts.py` — confirm exit code `0`.
9. Add a one-line note to README.md's mission/history log (where specs 038/etc. are referenced, if such a section exists) pointing at spec 038 as prior art and this spec as its successor, per FR-011 — do not edit or delete spec 038's own files.
10. Run the constitution's Artifact Coherence Checklist mentally: this feature touches only documentation + one new script, so most checklist items (install.sh, .env.example, TOOLS.md, new MCP server registration) are not applicable — confirm none of them were accidentally required (i.e., confirm no code/config changes crept in beyond the five docs + one script).

## Verifying success

- `python3 scripts/verify-inventory-counts.py` exits `0`.
- Grep for the previously-conflicting numbers (113, 66, 48, 103, 74, 127, 188, 47, 183, and whatever stale numbers were actually present at implementation time) across README.md and SOUL.md returns zero matches outside of historical/mission-log sections that are explicitly dated past entries (e.g., "MISSION02... 78 skills" is a historical record of what was true in the past and is not part of the current-state claims this feature fixes — it should not be changed).
- Manually search README.md for "Azure", "Batfish", "GitLab", "NetFlow" — each returns a hit describing it as a current, shipped capability.
