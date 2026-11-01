# Spec 166: Confined on-demand OpenClaw members on OpenClaw 2026.10.9+

Created 2026-10-31; branch `166-coldstart-system-members` (stacked on spec165 /
upstream PR #312); status: implementation. Owner prioritized this before Convergence
goes further because it must be fixed upstream.

## Problem

Spec165 showed OpenClaw 2026.10.9 cannot run an embedded member inside a
mount-namespaced `systemd --user` unit (`/proc/self/ns/pid` EACCES ->
GatewayLockNamespaceError). Spec165 moved always-on members to system units, but
production cold-start of on-demand members still uses user-scope `systemd-run`,
so on affected hosts on-demand OpenClaw members cannot run confined; the posture
reports the gap and cold-start fails fast. The unprivileged Border cannot start a
system unit without an authorization path.

## User scenarios and acceptance

1. P1: An operator installs, once and explicitly (sudo -n, printed commands on
failure), a hardened system template unit and a narrow polkit rule. Afterwards the
Border, running as that operator, cold-starts on-demand members as system instances
without sudo or a password prompt, with the same confinement as spec165 system
members, and the member completes an embedded OpenClaw task.
2. P1: The polkit rule authorizes only the installing operator, only the
`org.freedesktop.systemd1.manage-units` action, only units matching
`netclaw-coldmember@<instance>.service`, and only start/stop. The instance launcher
runs only a registered, local, on-demand member's launch command, resolved from the
Risk registry; unknown instances exit without running anything. A reserved probe
instance verifies authorization without starting a member.
3. P1: Posture and production cold-start use the system template when it is
installed and authorized; otherwise behaviour is unchanged from spec165 (unavailable
with remediation, fail fast). Hermes, hosts where user-scope confinement works and
testing mode are unchanged. Removal deletes the template and rule.

## Boundaries

No new third-party dependencies, no sudoers entries, no root-owned execution of
user-controlled paths beyond running as the operator. Live production-mode cold-start
end to end needs the DefenseClaw model guard; without it the evidence is
mechanism-level and must say so.
