# Research: Skill Load and Prompt Limits

## R1 Where limits are written
- Border: `scripts/install-mcp-config.py:merge_config` is the only writer of the OpenClaw runtime config during install; `install-steps.sh core_deploy` passes `--config` only in the non-Hermes branch, so Hermes is unaffected by construction. It supports both `mcp.servers` and legacy `mcpServers` layouts and preserves operator keys; limits go in a top-level `skills.limits` object.
- Spec members: `in2n-member-home.py:spec_member_config` builds `skills` via `spec_skills_section` from scratch (Workshop off + enabled flags) and asserts top-level keys; limits are added inside `skills`, no new top-level key.
- Profile members: the Border config is copied and so inherits the Border's limits; no change.
- `merge_config` already compares revisions and writes a backup before changing; the limits edit happens before serialisation so the same protections apply. If the only change is limits, the file is still rewritten (data != original).

## R2 Decision: limits
| Key | Default | Value | Rationale |
|---|---|---|---|
| maxSkillsLoadedPerSource | 200 | 400 | ~1.6x 240 shipped |
| maxCandidatesPerRoot | 300 | 400 | candidates must be >= loadable; default 300 would also stop scanning at 300 |
| maxSkillsInPrompt | 150 | 400 | must cover every eligible skill (spec FR-003) |
| maxSkillsPromptChars | 18000 | computed, see R3 | |

Alternative rejected: leave prompt limits at defaults and let the model see about 150 skills. That hides eligible skills in an order the operator cannot see, which the issue explicitly warns about. Alternative rejected: shrink the Border's skill set; skills are a shipped product surface.

Cost recorded: the prompt skill list grows with eligible skills (about 100k+ characters worst case, all 240 eligible, versus 18k). Real Borders typically have far fewer eligible (152 observed). Operators who prefer a smaller prompt can disable skills via `skills.entries.<name>.enabled=false`; the policy is raise-only so they should lower prompt limits only together with that.

## R3 Char measurement
Measured per shipped skill: len(name) + len(frontmatter description) + 120 overhead; empty description counts 200. Budget = ceil(total * 1.25 / 1000) * 1000. The policy stores the chosen number; the check fails if measured need exceeds it, so adding skills forces a conscious policy bump. Warning at 80%.

## R4 Raise-only semantics
`max(existing, policy)` per key when existing is a positive int (bool excluded); otherwise policy value. Non-dict `skills` or `skills.limits` is replaced only if invalid (non-dict); sibling keys preserved. Idempotent.

## R5 Check placement
`reconcile-mcp.py` runs scripts as subprocesses via a SURFACES map and CI runs it. Add `"skill-limits": ("check-skill-limits.py", ...)`. Findings are lines prefixed `skill-limits:` and must be added to the prefix list in `extract_findings` so they show.

## R6 Tests
No central pytest config for tests/; n2n tests run with `python3 -m pytest tests/n2n`. New dir `tests/skill-limits/` run with `python3 -m pytest tests/skill-limits`.

## R7 Not verifiable here
Real OpenClaw option behaviour (names per the issue) cannot be exercised on this host without a gateway; recorded in verification.md.
