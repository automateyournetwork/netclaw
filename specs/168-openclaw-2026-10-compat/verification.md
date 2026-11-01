# Verification

Operator Risk on Ubuntu 24.04 amd64: one Border, five always-on OpenClaw members
(specialties: lab automation, device testing, visualization, alert triage, security
operations), moved from `systemd --user` units to system units with spec165's
`in2n-services.py disable` / `generate --system` / `enable --system`. OpenClaw 2026.10.6.
Backups were taken first. No credentials or topology are recorded here.

## T001 diagnosis

- The old user units put an older node (OpenClaw 2026.7.1) first on `PATH`; the system
  units resolve the current one (2026.10.6). 2026.7.1 rejects these member configs
  (`agents: Invalid input`), so the member turns were likely already failing before the move.
- After the move all five members dialed the Border and were live. One routed read-only
  task per member: all five failed in about 13 s with "Agent process exited 1; task
  result unavailable".
- The same `openclaw agent --local --session-id … --json` turn by hand, with the
  member's environment, outside any sandbox: exit 1, `cli_error` "Multiple agents are
  configured, but agent command session creation has no explicit owner. Pass --agent
  <id>". Member homes carried the Border's two agent entries.
- With `--agent main`: success outside the sandbox and inside a transient unit with the
  member unit's exact hardening (ProtectSystem=strict, InaccessiblePaths,
  RestrictAddressFamilies, SystemCallFilter=@system-service, RestrictNamespaces). The
  same was shown for a tool-using turn (testbed inventory through the member's MCP server).
- Not a NetClaw defect, also found: the Border reports outbound task state on demand
  (`GET /n2n/tasks/<id>` returned `failed` with the member's error). Old `submitted`
  rows in `delegated_task` were never polled, not lost work.

## T002 implementation

`gateway.py` (first version): `--agent ${N2N_MEMBER_AGENT:-main}` on the embedded path;
`_cli_error_detail` appends the CLI's structured message (single line, 300 characters,
never stderr). Tests: `tests/n2n/test_gateway_member_agent.py` (default agent and argv
order, override, error detail without stderr). `tests/n2n`: 591 passed, 5 skipped; the
inherited `test_hermes_internal_149::test_official_n2n_mcp_operator_permit_and_owned_handle`
failure is unchanged from main.

## T003 live verification (OpenClaw 2026.10.6)

Routed task per member after the fix, members restarted:
- device testing, visualization, security operations: completed with tool use.
- lab automation: failed, now with the CLI reason "This model was not found" (the
  provider had retired the configured model). Alert triage: failed with the CLI reason
  "Couldn't sign in to the AI service" (the member's model had no credential in its
  home). Both were operator configuration, diagnosed from the new error text.
- After the operator moved both members to their OpenAI subscription: both completed
  with tool use (lab inventory; firing alerts from three metrics sources, read-only).

Five of five members complete routed tasks on 2026.10.6.

## T003 bootstrap files

- The Border's gateway journal on 2026.10.6 logged
  `bootstrap file is unreadable: file=<workspace>/AGENTS.md reason=symlink path component not allowed`
  (and the same for `USER.md`) 17 times each between 2026-10-30 and 2026-11-01; member
  turns printed the same two warnings. The three workspace files were symlinks into the
  checkout, created by an older install (2026-06-28).
- On the operator Risk the links were replaced by copies of their targets (contents
  identical; the link targets were recorded first).
- Installer: `core_deploy` replaces such a link with a copy and preserves regular files
  and links elsewhere. `tests/unit/test_core_deploy_preservation.py` (5 passed, including
  the new legacy-link case with a checkout path containing `&`, `|`, a quote and a space).
  `tests/setup-installer/run-tests.sh`: 277 tests, OK, 32 platform skips. `tests/unit`:
  the 14 failures and 24 collection errors are missing optional modules in this
  environment and fail identically on upstream main.

## T004 OpenClaw 2026.10.9

- `openclaw update --tag 2026.10.9 --yes` (managed npm update): the gateway serves
  2026.10.9 (ready 18:49:30 UTC). The updater reported "failed: gateway verification —
  Gateway process changed during final readiness verification", while the service had
  one start and no restarts; it recorded "verified serving 2026.10.9" and recommended
  `openclaw update repair`. This is OpenClaw's updater, outside NetClaw.
- A home with no agent entries on 2026.10.9: `openclaw agent --local --agent main
  --session-id …` reaches model resolution exactly as the same command without
  `--agent` does (both stop at the deliberately unknown model), so naming the agent is
  safe for Convergence member homes.
- Routed task per member after the upgrade: five of five completed (lab inventory,
  testbed inventory, mind map, firing-alert summary, self-status), all with tool use.
- A member turn with stderr captured on 2026.10.9 printed no bootstrap warnings
  (two before the link repair).

Known: unchanged members still share the Border's workspace path by builder design. A
cloud Border cannot offer that path, so member-owned workspaces are an input to that
work rather than part of this fix.

## Review correction

Self-review before the PR found that forcing `--agent main` would regress a home whose
only agent has another id. On 2026.10.9, in a throwaway home with one agent `ops`:
`--agent main` gives "Unknown agent id \"main\""; `--agent ops` and the unnamed command
both reach model resolution. `_member_agent_args` now names `main` only when the config
(`OPENCLAW_CONFIG_PATH`, else the state dir's `openclaw.json`) lists several agents
including `main` (`agents.entries` or `agents.list`), uses `N2N_MEMBER_AGENT` when set,
and otherwise adds nothing. `tests/n2n/test_gateway_member_agent.py`: 8 passed (several
agents, list layout, zero/one/several-without-main/unreadable config, override, error
detail). `tests/n2n`: 764 passed, 5 skipped, the inherited Hermes failure unchanged.

Final run with the corrected selection (members restarted 19:10 UTC, OpenClaw 2026.10.9
after `openclaw update repair`): lab inventory, testbed inventory, alert summary and
self-status completed; four members' homes list `main` and `alert`, one lists only
`main` and so ran unnamed. The visualization task hit the member's 600 s skill timeout
(an earlier run of the same request on 2026.10.9 completed; this member's model spends
1.6-3.9 M tokens on it). A timeout records an empty task error; that diagnostic gap is
outside this change and noted as a follow-up.
