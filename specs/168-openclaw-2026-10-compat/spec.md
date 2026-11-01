# Spec 168: Existing Risks on OpenClaw 2026.10

Created 2026-11-01; branch `168-openclaw-2026-10-compat` from upstream main (1.18.0);
status: implementation and live verification. Found while moving an operator's existing
Risk (five always-on members, multi-agent Border) to system-scope member units
(spec165) and then from OpenClaw 2026.10.6 to 2026.10.9.

## Problem

1. **Member turns.** `gateway.run_agent_turn(local=True)` runs
   `openclaw agent --local --session-id <id>` without `--agent`. OpenClaw 2026.10 and
   later refuse that command when the home configures more than one agent ("Multiple
   agents are configured, but agent command session creation has no explicit owner.
   Pass --agent <id>"). `in2n-member-home.py` deep-copies the Border's config, so a
   Border with several agent entries gives every member several agents, and every
   delegated member task fails. The Border sees only "Agent process exited 1; task
   result unavailable": the CLI's own reason is discarded.
2. **Bootstrap files.** Older installs linked the workspace's `AGENTS.md`, `USER.md` and
   `TOOLS.md` into the NetClaw checkout. OpenClaw 2026.10 refuses symlinked bootstrap
   files ("symlink path component not allowed") and continues without them, so the
   Border and its members run without NetClaw's agent instructions and the operator's
   user profile, with only a log warning. Current installs copy these files, but the
   installer preserves any existing entry, including those legacy links.

The spec165-167 qualification VM showed neither: its Border has one agent and was
installed after the installer switched to copies.

## User scenarios and acceptance

1. P1: A member whose home has several agent entries including `main` completes a
   delegated task on OpenClaw 2026.10.x as agent `main`; `N2N_MEMBER_AGENT` names
   another agent.
2. P1: A home with zero or one agent (Convergence builder, or a single agent with another
   id) keeps the unnamed command and behaves exactly as before.
3. P2: A failed embedded turn records the CLI's structured error message (single line,
   at most 300 characters, never stderr) in the task error.
4. P1: Re-running the installer replaces a workspace bootstrap file that is a symlink
   into the NetClaw checkout with a regular copy of its target. Regular files and
   symlinks elsewhere are preserved.

## Boundaries

Member-home builders, existing member homes and Hermes are unchanged. Members keep
sharing the Border's workspace path; that layout is recorded as an input to cloud
Border work, not changed here. Operator-owned bootstrap files are never overwritten.
