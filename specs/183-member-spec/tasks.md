# Tasks

- [x] T001 Research OpenClaw MCP tool naming, allowlist matching and layering, core tool ids, skill loading (research.md).
- [x] T002 Spec format and strict validation in `in2n-profiles.py` (`load_member_spec`, `MemberSpecError`).
- [x] T003 Allowlist entries: built-in ids or `<kept server>__<tool>`; refuse groups, `*`, `bundle-mcp`, renamed servers, non-kept servers.
- [x] T004 Skills: warn when not installed; scope through the existing `scope custom` path.
- [x] T005 `spec_member_servers`, `spec_env_slice_keys`, `spec_tool_policy` reusing `_kept`/`_slice` and the 182 deny lists.
- [x] T006 `in2n-member-home.py --spec`: shared generic path, `--member` check, tool policy, Hermes refusal.
- [x] T007 `in2n-migrate.py --spec/--specs-only`: staged slice, runbook, exact `--spec` member-home command.
- [x] T008 `netclaw risk add spec` and `in2n-profiles.py spec`.
- [x] T009 Docs: N2N-RISK.md "Member spec"; `n2n-federation` skill.
- [x] T010 Tests: each format error, non-kept server patterns, env slice, generated config, 182 protections, migrate, CLI, OpenClaw cross-check.
- [x] T011 Run the 183 and 182 tests, `tests/n2n`, `verify-spec-artifacts.py`, `git diff --check`; validate a generated home with `openclaw config validate`.
- [x] T012 Review round 1: component-launched servers' env keys (catalog settings + installer-access contract) join every member slice, deny lists unchanged; fixes spec 182's profile slices too.
- [x] T013 Review round 1: per-agent skill allowlist (`spec_skill_allowlist`) on every agent entry and the defaults; `[]` for no skills.
- [x] T014 Review round 1: tests, OpenClaw skill-filter cross-check, `openclaw config validate` and `openclaw skills list` on generated homes; docs and spec updated.

- [x] T015 Refuse dangerous built-ins without recorded explicit opt-in; reject Border-only servers and env derivation.
- [x] T016 Own workspace, copied base skills, Workshop off, narrowed sandbox, stripped inherited agent policy/state.
- [x] T017 Reserve all profile names and print complete cold/hot staging arguments; focused regression coverage.
- [x] T018 Opt-in reaches staging: `in2n-migrate.py --allow-dangerous-tools` and `netclaw risk add spec ... --allow-dangerous-tools`; the printed member-home command carries it only for a spec that needs it; `--allow-dangerous-tools` without `--spec` is a usage error.
- [x] T019 `risk add spec` prints a real Border endpoint (placeholder → loopback default) and `--hot ""`.
- [x] T020 Installed-OpenClaw tests: dangerous set vs. catalog groups/sandbox deny; sandbox resolver on a hardened member; `openclaw config validate` with a negative control. Profile member keeps the Border workspace symlink; Border-only refs never reach a profile slice.
- [x] T022 Round 2: spec member config built from `SPEC_MEMBER_TOP_KEYS` (no gateway/env/hooks/cron/other providers/plugins/memory search/sandbox binds), provider via `${ANTHROPIC_API_KEY}`.
- [x] T023 Round 2: own memory-mcp and gait-mcp stores; Border store keys out of the spec slice.
- [x] T024 Round 2: explicit `SAFE_BUILTINS` (read, session_status); everything else needs the opt-in.
- [x] T025 Round 2: `copy_skill` opens `O_NOFOLLOW` and checks `fstat` (regular, one link).
- [x] T026 Round 2: profile-member exposure documented (spec.md Known behaviour, research.md Follow-up); tests and verification.
- [x] T021 Final verification: 183/182 tests, full `tests/n2n` against the main baseline, `verify-spec-artifacts.py`, `git diff --check` (verification.md).
