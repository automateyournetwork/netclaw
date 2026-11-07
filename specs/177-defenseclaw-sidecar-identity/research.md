# Research

- **DefenseClaw 1.0.4 source** (`internal/daemon/daemon.go`): `Daemon.Start` launches
  the child and then calls `writePIDInfoAt(pid, executable, startIdentity, ...)`. The
  child (`DEFENSECLAW_DAEMON=1`) does not write a record, and neither does a gateway run
  without `start`. The CLI's trust check (`cmd_doctor.py`) rejects a record without
  `executable` and `start_identity` ("legacy PID record lacks strong executable/start
  identity"). A hand-written PID is therefore not an option, and would amount to
  forging DefenseClaw's identity check.
- **DefenseClaw 1.0.8 notes**: `defenseclaw-gateway status` recognises a gateway started
  as a transient systemd unit; `defenseclaw status` still does not ("Known limits").
  Upgrading does not fix the foreground unit.
- **Watchdog**: `start` also launches `defenseclaw-gateway watchdog`, which polls
  `/health` and sends desktop notifications. It does not restart the gateway, so
  restarts stay with systemd.
- **systemd**: `PIDFile=` needs a bare PID; DefenseClaw's record is JSON. With
  `Type=forking` and two processes left in the cgroup, systemd cannot reliably guess
  the main PID, so the unit names it explicitly.
