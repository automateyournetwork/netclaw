# Plan

T001 (worker): `scripts/in2n-coldstart.py <instance>` (stdlib + existing federation
package): reserved instance `probe` exits 0 doing nothing; otherwise validate the
instance, resolve the member whose slug matches among local on_demand members with a
launch_cmd, and exec it (shlex argv, no shell); otherwise exit non-zero without
running anything. in2n-services.py: `coldstart install|remove|status` (system
scope, sudo -n only, refuse root) writing the template unit (User/Group/HOME, portable
+ kernel hardening, Restart=no, ExecStart = n2n python + launcher %i) and
`/etc/polkit-1/rules.d/60-netclaw-coldmember-<user>.rules`. controls.py: cached
`system_coldstart_available()` (template file present and `systemctl start` of
`netclaw-coldmember@probe.service` succeeds); `confined_cold_start` returns
`systemctl start --no-block netclaw-coldmember@<slug>.service` when available;
sandbox_available treats on-demand OpenClaw members as confined when available.
service.py production cold-start fail-fast honours it. Tests mock systemctl/sudo.
Docs: N2N-RISK durable/cold-start sections, release notes later.
T002 (coordinator): VM live validation: install, real probe, polkit denial for other
units/users, member cold-start via the real controls argv from the mesh daemon's
user context, embedded task completion, idle exit and restart, removal.
T003: independent verification. T004: commit, push, upstream PR (depends on #312).
