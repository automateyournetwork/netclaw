# Spec 170: Domain certificates renew again

Created 2026-11-02; branch `170-acme-renewal-credentials`, stacked on spec169 (1.18.2);
status: implementation and verification. Found on an operator Risk whose Let's Encrypt
certificate for the Border's public name expired on 2026-10-15 although a valid DNS
provider token was configured.

## Problem

1. **Credentials never reach lego.** Since `e5d3774b` (2026-09-27), the mesh launchers
   (`scripts/federation-control.py`, `scripts/peering-launch.py`, the HUD's
   `claw-services.mjs`) pass only `NETCLAW_`/`N2N_`/`BGP_` settings from the runtime
   env files to the daemon. That keeps unrelated secrets out of the daemon and its
   children, but `acme.py` runs lego with the daemon's environment and expects the
   provider's own variables (`CLOUDFLARE_DNS_API_TOKEN`, `GODADDY_API_KEY`, …), as
   `.env.example` and feature 060 document. Every renewal since then failed with lego's
   "some credentials information are missing", recorded as `renewal-failed`.
2. **Renewal outlasts its timeout.** `lego renew` sleeps a random delay of up to about
   8 minutes before renewing when run non-interactively. `acme._run` kills lego after
   180 s, and operator rotation (`POST /n2n/certs/rotate`, `/n2n/certs/renew`) waits for
   the result. With credentials present, most renewals would still time out.

## User scenarios and acceptance

1. P1: With `N2N_ACME_DNS_PROVIDER` set and the provider's variables in the runtime
   `.env` (or `mesh.systemd.env`), issuance and renewal give lego exactly the variables
   `lego dnshelp --code <provider>` lists (and their `_FILE` forms). Other variables in
   those files are not passed, and the daemon's own environment is unchanged.
2. P1: Precedence: a variable already in the daemon's environment wins, then
   `mesh.systemd.env`, then `.env` (the launchers' file order).
3. P2: An unknown provider, a missing `NETCLAW_RUNTIME_ENV`, or an unreadable env file
   passes nothing extra; an unreadable file is logged by exception type only.
4. P1: Renewal runs with `--no-random-sleep`. NetClaw already renews only when its
   rotation registry says a credential is due, on an hourly check offset by daemon start.

## Boundaries

The launchers' prefix filter stays: provider secrets go to the lego process only.
Found and not changed: `in2n-services.py` writes the mesh unit's
`EnvironmentFile=-"<home>/mesh.systemd.env"` with quotes, which systemd ignores ("path is
not absolute"). The launchers read that file themselves, so settings there still apply;
making systemd load it would put the whole file, including any secrets and a stale
`PATH`, into the daemon's environment, against `e5d3774b`'s intent. Recorded for
maintainers rather than changed here.
