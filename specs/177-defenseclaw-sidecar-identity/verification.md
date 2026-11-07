# Verification

Qualification VM (Ubuntu 24.04 amd64, OpenClaw 2026.10.9, DefenseClaw 1.0.4 pinned),
Risk in production mode. No credentials are recorded here.

## T001 reproduction

- Under the generated foreground unit, `defenseclaw skill enable convergence-setup`
  failed: "gateway enable failed: the gateway is not running (PID file is missing)".
  `defenseclaw skill scan` warned "The gateway isn't running, so this scan result was
  not recorded". `defenseclaw-gateway status` reported the port "held by PID … not by
  this account's gateway", although that PID was the unit's own gateway.
- A hand-written bare PID was rejected: "legacy PID record lacks strong
  executable/start identity". It was removed; this change never writes that record.

## T004 tests

- `tests/n2n/test_defenseclaw_sidecar_177.py` (3 tests): the rendered unit uses
  `Type=forking`, the helper, `stop` for `ExecStop` and `ExecStartPre`, `PIDFile=` under
  the runtime directory, quoted paths and no leftover placeholders; the helper copies
  only the `pid` and leaves DefenseClaw's record untouched; it fails when `start`
  fails, the record has no integer pid, or `RUNTIME_DIRECTORY` is unset. The unit test
  fails against the previous template.
- Every test that loads `in2n-services.py` (`test_coldstart_166`, `test_durable_services`,
  `test_hermes_members_149`, `test_member_scope_165`, `test_defenseclaw_enable`):
  124 passed.
- `ruff check --select F,E9` on the changed Python: clean. `prepare-release.py --check`: PASS.

## T005 live

The unit rendered from this template (gateway `~/.local/bin/defenseclaw-gateway`,
`/usr/bin/python3`, the new helper) replaced the old one; `systemd-analyze --user
verify` printed nothing.

- **Take-over:** a gateway started by hand was running. `systemctl --user start`
  stopped it (`ExecStartPre`) and started a supervised one. MainPID 3012154 equalled
  the `pid` in DefenseClaw's record; one gateway and one watchdog ran.
- **CLI:** `defenseclaw-gateway status` showed the gateway; `defenseclaw skill scan`
  no longer warned that its result went unrecorded; `defenseclaw status` showed the
  sidecar running with the unit's PID.
- **Crash:** `kill -9` of the gateway; within 25 s systemd restarted it (NRestarts=1,
  MainPID 3013047, record updated to the same PID), two processes, `/health` answered.
- **Stop/start:** stop left no gateway process and no record; start brought it back.
- **Posture:** `GET /n2n/posture` returned `production — enforced` afterwards.

## Not verified

DefenseClaw 1.0.8, macOS/launchd, the enterprise system-wide gateway, and a host reboot.
