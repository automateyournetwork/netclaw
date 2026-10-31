# Spec 165: Confinement and guidance for Convergence federation on current OpenClaw

Created 2026-10-31; branch `165-convergence-confinement`; status: implementation.
Owner requested the spec164 T005 follow-ups and qualification on the current OpenClaw
release (2026.10.9, the newest stable). Spec164 T005 remains BUDGET_EXHAUSTED; this
spec does not relabel it.

## Problem evidence (spec164 verification.md)

1. OpenClaw 2026.10.9 records gateway-lock identity as hostname + boot id + the inode
of `/proc/self/ns/pid`. In a systemd `--user` unit with any mount-namespace directive
(PrivateTmp, ProtectSystem, ProtectHome, InaccessiblePaths) that stat returns EACCES,
so `openclaw agent --local` refuses its own lock (GatewayLockNamespaceError) and every
hardened OpenClaw member fails. A system-manager unit with `User=` and the same
directives can read it. Releases before the check (e.g. 2026.10.6) are unaffected.
2. A standalone Border with host exec/read reached Convergence secrets; NetClaw
production mode confines members only. OpenClaw's Docker sandbox contained it.
3. OpenClaw Skill Workshop autonomous learning (default auto) persisted a bypass
procedure as a reusable skill and makes extra provider calls.
4. The Border rarely searched for corroborating monitoring tools, omitted the
latest-100 bound, and invented exchange/reply semantics.

## User scenarios and acceptance

1. P1: On a native Linux OpenClaw 2026.10.9 Risk, an operator can run always-on
members as system-scope units that keep the full feature-057 hardening, and an
embedded member completes a delegated task. The posture reports the sandbox control
unavailable, with a remediation, when user-scope confinement cannot run an OpenClaw
member, instead of claiming confinement that breaks execution. User-scope behaviour
for hosts and runtimes unaffected by the probe is unchanged. No silent sudo.
2. P1: An operator can opt in to Border hardening with one documented helper: OpenClaw
Docker sandbox for all sessions (no network, no workspace exposure, elevated exec off,
MCP tools allowed through the sandbox gate) and Skill Workshop learning off. Dry-run
shows the change; apply validates with OpenClaw before writing; existing settings are
preserved. Not a global default: no-network sandboxing breaks host-script skills.
3. P1: The observation skill and HUD envelope tell the Border to search for available
monitoring/metrics/inventory sources by capability before declaring gaps, to state
the latest-100 bound, and to describe each record only as source -> destination with
its counters (no exchange, reply, session or verdict language).

## Requirements and boundaries

No new third-party dependencies or tools. Keep Hermes behaviour unchanged. Cold-start
(on-demand) OpenClaw members under user-scope confinement remain a reported gap; the
posture must say so. Qualification on the VM needs separate owner-approved provider
attempts. Configuration success is not model-answer qualification.
