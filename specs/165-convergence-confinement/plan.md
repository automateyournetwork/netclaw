# Plan

T001 member confinement (worker A): controls.py gains a cached probe of whether a
user-scope mount-namespaced unit can stat /proc/self/ns/pid. sandbox_available()
reports unavailable with remediation when OpenClaw members use user units and the
probe fails; it accepts system-scope member units. in2n-services.py gains an explicit
`--system` scope: units with User=/Group= under /etc/systemd/system, full hardening
(portable + kernel set, since the system manager supports it), installed and managed
through explicit sudo (sudo -n failure prints the exact command; never silent).
Default stays user scope. confined_cold_start unchanged; posture names the cold-start
gap. Tests: tests/n2n/test_durable_services.py, test_posture.py, test_cold_start.py
(extend; new focused test file allowed).

T002 Border hardening helper (worker B): scripts/border-harden.py with --dry-run and
--apply for OpenClaw: sandbox mode=all, backend docker, scope session,
workspaceAccess none, docker.network none, tools.elevated.enabled=false, sandbox
alsoAllow bundle-mcp (merged with existing), skills.workshop.autonomous.mode off.
Uses `openclaw config set --batch-file --dry-run` then apply; checks Docker access
and the sandbox image, printing build instructions rather than building silently.
Docs: docs/CONVERGENCE.md and docs/N2N-RISK.md. Tests in tests/setup-installer or a
new focused test with a fake openclaw binary.

T003 guidance (coordinator): convergence-observations skill text, HUD envelope task
and limits text, regenerate catalog/descriptors, HUD unit tests.

T004 checks + independent verification. T005 VM qualification (owner budget).

## Continuation (owner, 2026-10-31 20:33)

Owner: fix advisories now, run as many qualification attempts as needed, commit and
PR upstream so OpenClaw upgrades do not break members. Upstream PR311 merged at
20:18 (main 4edf8708 contains 2d930087; no drift in touched files).
T006 worker owns controls.py, in2n-services.py, service.py cold-start path, posture
code if needed, their tests and the N2N-RISK durable-services text. Fixes: A tolerate
an already-removed system unit; B refuse user-scope disable for a system-bound member;
C OpenClaw production cold-start fails fast when user-scope confinement cannot run it
and the sandbox control is degraded while spawnable on-demand OpenClaw members exist;
D install all units or report exactly which were installed and still daemon-reload;
E refuse --system as root; F probe retries after a timeout instead of caching it,
probe also applies ProtectSystem=strict, quote Environment=PATH, docs mention --system.
T008 reliability target: three consecutive final-text passes per scenario (S1, S2,
S3) after T007, every run counted; failures with a new hypothesis feed one more
guidance iteration (max3), otherwise stop and report the residual rate.
