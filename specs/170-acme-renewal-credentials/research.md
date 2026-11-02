# Research

- Live Risk: `journalctl --user -u netclaw-mesh` showed `acme: renew … failed (rc=1):
  cloudflare: some credentials information are missing` on every start. The token was in
  `~/.openclaw/.env` and valid (Cloudflare token verify: active). `/proc/<pid>/environ`
  of the daemon had `N2N_ACME_*` but no `CLOUDFLARE_*`.
- `systemd-analyze --user verify` on the generated unit: `EnvironmentFile= path is not
  absolute, ignoring: "<home>/mesh.systemd.env"`. Introduced by `_quote()` in
  `in2n-services.py` (`482758a0`, spec149). The same file loads with an unquoted path.
- `e5d3774b` added the prefix filter to `peering-launch.py`; `federation-control.py` and
  `claw-services.mjs` filter the same way and read `.env` then `mesh.systemd.env`.
- lego 4.19.2 `dnshelp --code <id>` prints `  - "NAME":  description` for credentials and
  additional configuration, and exits 1 for an unknown provider. lego accepts `<NAME>_FILE`
  for credentials. Names vary by provider (Route53 uses `AWS_*`), so a prefix rule would
  not work.
- `lego renew` logged `renewal: random delay of 7m57s` before contacting the CA; lego's
  `--no-random-sleep` disables it. `RotationManager.renew_one` is awaited by the hourly
  cycle and by the two operator endpoints.
- `scripts/write-env.py` `values()` parses assignments literally (JSON or `shlex` split,
  no expansion or execution); the launchers already use it.
