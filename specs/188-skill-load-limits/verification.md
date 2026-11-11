# Verification: spec 188 skill load limits

Run on macOS, pytest 9.1.1, python3 3.14 (Homebrew), 2026-11-11.

## Real results
- `pytest tests/skill-limits -q`: 31 passed (policy validation, raise-only merge, idempotence, Border `merge_config`, member config, CLI check, reconcile surface).
- `pytest tests/n2n/test_member_spec_184.py tests/n2n/test_member_spec_providers_186.py tests/n2n/test_member_mcp_mappings_183.py tests/skill-limits -q`: 262 passed, 9 skipped (skips are pre-existing; baseline before this change on the 183/184/186 files was 231 passed, 9 skipped). One existing assertion in `test_member_spec_184.py` was updated because spec members now also carry `skills.limits`.
- `python3 scripts/check-skill-limits.py`: exit 0, 240 shipped skills covered. A synthetic 401-skill directory exits 1 naming `maxSkillsLoadedPerSource 400 < 401`.
- `python3 scripts/install-mcp-config.py ... --config <tmp>` run by hand twice: the first run raised limits and kept an operator value of 999; the second run created no new backup (idempotent).
- `python3 scripts/reconcile-mcp.py` (exit code read directly, not through a pipe): rc=1 both before and after this change. Failures are the pre-existing ones only (humanrail dependency pin; `startup` surface on servers that cannot start on this host). The new `skill-limits` surface passes.
- Measured need: 240 skills, 97,281 estimated prompt characters; budget set to 122,000 (1.25x, rounded up).

## Decisions made without a human
- Limits 400/400/400/122000; headroom about 1.6x on counts, 1.25x on characters.
- Spec members get the policy values directly (no Border merge). Profile members copy the Border config and have limits raised raise-only on that copy. A spec member's own workspace holds only its copied skills, so the limit rarely binds there; added for determinism.
- The character estimate is a heuristic (name + description + 120 overhead), not OpenClaw's real formatting.

## Not verified
- Behaviour against a real OpenClaw. Option names `skills.limits.maxSkillsLoadedPerSource`, `maxCandidatesPerRoot`, `maxSkillsInPrompt`, `maxSkillsPromptChars` are taken from issue #326; no gateway was run and `openclaw skills check` was not run.
- The real prompt-token cost of the larger budget, and whether OpenClaw accepts values this large (400, 122000).
- A full installer run (`scripts/install.sh`); only `install-mcp-config.py` and its tests were exercised. The Hermes exclusion is verified by reading the installer branch, not by running Hermes.
- The CI workflow path-trigger change was not executed.
