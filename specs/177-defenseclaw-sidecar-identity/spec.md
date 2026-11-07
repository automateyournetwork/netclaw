# Spec 177: The DefenseClaw CLI can reach the sidecar that NetClaw supervises

Created 2026-11-06; branch `177-defenseclaw-sidecar-identity`, on 1.18.6; status:
implementation and verification. Found on the qualification VM while enabling a skill
DefenseClaw had quarantined.

## Problem

`scripts/in2n-services.py generate` writes `defenseclaw-sidecar.service`, which runs
`defenseclaw-gateway` in the foreground (`Type=simple`). DefenseClaw writes its PID
record (`~/.defenseclaw/gateway.pid`: pid, executable, start identity) only in the
parent of `defenseclaw-gateway start`. Under NetClaw's unit there is never a record, so
the DefenseClaw CLI treats the running gateway as "not this account's gateway":

- `defenseclaw skill enable` and `disable` fail with "the gateway is not running";
- CLI scans warn that their result was not recorded in the audit log;
- `defenseclaw-gateway status` refuses to show the gateway's state.

On the qualification VM a quarantined skill could not be re-enabled. The only way
through was to stop the unit and start the gateway by hand, unsupervised. DefenseClaw
1.0.8 lists the same limit for gateways started directly by systemd.

## User scenarios and acceptance

1. P1: On a Risk host in production mode, `defenseclaw skill enable`, `disable` and
   CLI scans reach the gateway that `defenseclaw-sidecar.service` runs, and
   `defenseclaw-gateway status` shows it.
2. P1: systemd still supervises the gateway: a crash restarts it, `systemctl --user
   stop` stops it, and production posture stays `enforced`.
3. P2: Regenerating and restarting the unit takes over a gateway that was started by
   hand, so exactly one supervised gateway runs.

## Boundaries

- NetClaw never writes or edits DefenseClaw's PID record. The unit starts the gateway
  with DefenseClaw's own `start`, and copies only the `pid` field into a separate,
  plain file for systemd's `PIDFile=`.
- No DefenseClaw version change; works with the pinned 1.0.4.
- Existing hosts keep the old unit until `generate` and a restart; the docs and release
  notes say how.
