# Verification

Run coldstart-20261031: start23:23UTC, deadline00:08UTC. Checkout
/home/ubuntu/netclaw-convergence-linux, branch166-coldstart-system-members from
9dda95e0 (spec165, upstream PR #312, CI 40/40). Default3 attempts/task. Worker owns
T001 files; coordinator owns specs and VM validation. No provider calls expected;
any live model turn will be recorded as a counted run.

T001 attempt1 (worker + coordinator): scripts/in2n-coldstart.py (reserved `probe`
no-op; instance regex; resolves only routable, local, on-demand, non-service-owned
members; execvp of shlex argv, no shell), `in2n-services.py coldstart
install|remove|status` (template + polkit rule via sudo -n, partial-install report,
root refusal, `--no-ask-password` probe), controls.system_coldstart_available
(cached success keyed on template identity, short refusal cache, not cached on
timeout), confined_cold_start(system=True), sandbox_available and production
cold-start integration with fail-fast on a refused start, N2N-RISK docs.
Coordinator change: the launcher reads the Border registry through a read-only
SQLite URI instead of FederationManager (which migrates/writes); test proves a 0400
registry is unchanged. Checks: test_coldstart_166 66 passed; tests/n2n 703 passed/5
skipped/1 inherited failure; ruff F/E9 clean (pre-existing service.py F401 only);
docs reconcile exit0; systemd-analyze verify of template rc0; polkit rule evaluated
under Node with a stub in 11 allow/deny cases. Not yet exercised: real polkitd,
sudo install, system manager instance, idle exit/restart (T002).
T002 C1 begins: one member-side model turn (minimax-m3) via /n2n/route to the cold-started system instance.

T002 attempt1 PASS (dedicated test VM: Ubuntu 24.04, systemd 255, polkitd 124,
OpenClaw 2026.10.9, Risk testing mode). Spec166 code deployed onto the spec165 tree.
- Member converted: `disable --system` removed its always-on system unit; registered
  on_demand with launch_cmd and idle-exit 120.
- `coldstart install` (sudo -n) installed template + polkit rule; template shows
  User=operator, ProtectSystem=strict, PrivateTmp, RestrictNamespaces,
  SystemCallFilter, Restart=no.
- `coldstart status`: authorized from an SSH session and from a `systemd --user`
  service context (the mesh daemon's context), both with --no-ask-password.
- Real polkitd from the service context: allowed start of netclaw-coldmember@probe;
  refused (Interactive authentication required) restart of the same instance, stop
  cron.service (cron stayed active), start of netclaw-member-*.service, and start of
  a look-alike netclaw-coldmemberX@ template.
- Cold start via the exact controls.confined_cold_start(system=True) argv from the
  service context: instance active as User=operator with full hardening; launcher
  "starting t005-risk/convergence"; member dialed and became active.
- C1 (one member-side minimax-m3 turn, counted): /n2n/route
  capability=convergence-observations -> task completed inside the system instance;
  member called convergence_flow_summary (empty current window, correctly reported
  with exact window, latest-100 bound and direct provenance).
- Idle exit: member exited after 123s with no in-flight task; unit Result=success,
  status 0; member unreachable. Restart via start -> active; allowed stop -> inactive.
- Posture with template installed and on-demand member: sandbox available ("on-demand
  members cold-start as confined system instances"). `coldstart remove` deleted both
  files; posture reverted to unavailable with remediation; probe start refused.
  status rc 1 without template, 0 after reinstall (left installed).
Not exercised live: production-mode delegation end to end (the production preflight
refuses without the DefenseClaw model guard before any cold start); the production
glue is covered by unit tests only.

T003 independent verification: FAIL with one MEDIUM-HIGH security finding, two LOW.
Verified otherwise: polkit rule against 45 adversarial cases under Node (only
manage-units, operator, anchored template regex, start/stop; restart, reload,
kill, set-property, enable/mask, escapes, unicode, newlines, other users/templates
all fall through), template/launcher/controls/service behaviour, additive tests,
tests/n2n 703/5/1 inherited. Release/doc edits made during the review were outside
its snapshot.
Finding 1 (fixed): systemd 257+ authorizes StartTransientUnit through manage-units
with unit=<requested name>, verb=start (v255, this VM, passes no details for
transient units). With the rule present but the template absent, the operator (or a
confined member, AF_UNIX allowed) could run `systemd-run --system
--unit=netclaw-coldmember@x.service -p User=root` -> root. Only the template's unit
file (non-pristine name) blocks it. States reachable: rule installed after a failed
template install, removal deleting the template first, manual template deletion.
Fix: the rule re-checks the template with polkit.spawn(test -f) on every request and
returns no result otherwise; install order template -> daemon-reload -> rule,
stopping at the first failure; remove deletes the rule first; N2N-RISK and 1.17.0
notes corrected (no "grants no privilege" claim). Tests updated to the stronger
contract (ordering, first-failure stop, template-failure never installs the rule,
rule contains the gate before YES). Live on polkitd 124: a throwaway mirror rule gated
on a flag file refused start while the flag was absent and allowed it when present
(spawn gate effective); the real rule reinstalled with the gate (`grep polkit.spawn`
1), status authorized, service-context probe authorized, restart refused, member
cold-start/stop works. The systemd 257 transient path itself was not exercised (VM
runs 255).
Finding 2 (fixed): launcher refuses colliding slugs ("ambiguous: ...", exit 3, test);
confined_cold_start refuses a member whose slug is the reserved `probe`.
Finding 3 (fixed): a hung `systemctl start` is killed after 30s and the cached
authorization forgotten (test).
Checks: test_coldstart_166 70 passed; tests/n2n 707 passed/5 skipped/1 inherited;
ruff F/E9 clean on changed files; docs reconcile/links PASS; diff --check clean.
Coordinator slip recorded: one deploy piped tar and a heredoc into the same SSH
stdin, so the first reinstall used old code; detected (rule lacked the gate),
redeployed and re-verified.

Security re-verification: PASS. Confirmed against systemd v257 source that an
existing template blocks same-named transient units for every instance (fragment
fallback to the template; checked before auxiliary units), polkit 124
js_polkit_spawn throws on non-zero exit, and the rule evaluated under Node in
128/128 cases (YES only after a successful spawn). Fault injection at every
install/remove step left only safe states. New LOW (fixed): GNU `install` unlinks
then recreates the destination, so a reinstall while the rule was loaded left the
template briefly absent; `coldstart install` now removes any existing rule first,
then installs template, daemon-reload, rule. INFO (fixed): printed manual commands
say to stop at the first error; ProcessLookupError on kill tolerated; the misnamed
test now covers both template and daemon-reload failures (parametrized). Remaining
INFO: after the rule is deleted polkitd reloads it asynchronously (tens of ms) before
the template is removed; the spawn gate limits that to a negligible straddle.
Checks: test_coldstart_166 71 passed; tests/n2n 708 passed/5 skipped/1 inherited;
ruff F/E9 clean; diff --check clean. Live: reinstall over an existing install ->
rule gate present, status 0, service-context probe authorized.
Release 1.17.0: VERSION, CHANGELOG and docs/releases/1.17.0.md; prepare-release
--check PASS. docs/CONVERGENCE.md points to `coldstart install`.

T004: commit 9c09c34f pushed to fork branch 166-coldstart-system-members; upstream
[automateyournetwork/netclaw#313](https://github.com/automateyournetwork/netclaw/pull/313)
opened against main, stacked on #312 (merge #312 first). Hosted CI reported on the PR.
