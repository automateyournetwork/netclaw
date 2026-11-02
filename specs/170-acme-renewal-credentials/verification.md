# Verification

Operator Risk on Ubuntu 24.04 amd64, OpenClaw 2026.10.9, lego 4.19.2, Cloudflare DNS.
Commands ran with `umask 077`. No credentials or tokens are recorded here.

## T001 diagnosis (live)

- The Border's Let's Encrypt certificate had expired on 2026-10-15. Each mesh start logged
  `acme: renew … failed (rc=1): cloudflare: some credentials information are missing`
  and `cert-event renewal-failed`.
- The provider token was in `~/.openclaw/.env` and valid (Cloudflare token verify:
  `active`). The daemon's `/proc/<pid>/environ` had `N2N_ACME_DNS_PROVIDER` and
  `N2N_ACME_EMAIL` but no `CLOUDFLARE_*`: `peering-launch.py` passes only prefixed keys.
- `systemd-analyze --user verify` on the mesh unit: `EnvironmentFile= path is not
  absolute, ignoring: "<home>/mesh.systemd.env"`. A token added to that file also never
  reached the daemon (recorded in the spec's boundaries).
- Manual renewal with only the provider token passed to lego: lego logged `renewal:
  random delay of 7m57s`; the first attempt through `acme.renew` hit the 180 s timeout
  during that delay. A direct run then renewed: new certificate valid to 2027-01-31.

## T003 tests

- `tests/n2n/test_acme_provider_env_170.py` (5 tests, fake lego printing lego's real
  `dnshelp` layout): exactly the listed variables are passed (`CLOUDFLARE_*`, including
  an additional-configuration one), never `OTHER_SECRET`, and `os.environ` is unchanged;
  renew argv ends `renew --days 30 --reuse-key --no-random-sleep`; `_FILE` form passed;
  precedence environment > `mesh.systemd.env` > `.env`; unknown provider and missing
  `NETCLAW_RUNTIME_ENV` pass nothing; an unparsable `.env` is skipped and its content is
  not logged. Four fail on 1.18.2; the "passes nothing" case passes on both, as expected.
- `tests/n2n/test_rotation_truthfulness.py::test_acme_renewal_requests_existing_pinned_key`
  updated: its `_run` stub accepts `env=`/`timeout_s=` and the renew argv includes
  `--no-random-sleep`.
- `tests/n2n`: 771 passed, 5 skipped, 1 failed. The failure,
  `test_hermes_internal_149::test_official_n2n_mcp_operator_permit_and_owned_handle`, is
  inherited and fails identically on main.
- `ruff check --select F,E9` on changed Python, `git diff --check`,
  `prepare-release.py --check` (1.18.3), `verify-spec-artifacts.py`, catalog metadata and
  links pass. The hash-pinned `mcp-servers/n2n-mcp/server.py` is unchanged.

## T004 live

- Staging issuance through the new `acme.issue()` with the real lego and Cloudflare, from
  a daemon-equivalent environment (prefixed settings only, every `CF_*`/`CLOUDFLARE_*`
  removed, `NETCLAW_RUNTIME_ENV` set) into a throwaway directory:
  `_provider_names("cloudflare")` returned 24 names including
  `CLOUDFLARE_DNS_API_TOKEN`; a Let's Encrypt staging certificate was issued in 12 s.
  The production certificate and account were not touched.
- Applied to the operator Risk and restarted the mesh: `acme: domain-verified credential
  ready`, no renewal failure; `GET /n2n/certs` shows the ACME credential `active` until
  2027-01-31; the daemon environment still has no `CLOUDFLARE_*`.

## Not covered

A production renewal by the daemon itself: the certificate is not due until about
2027-01-01. Forcing rotation of a not-due certificate makes lego return it unchanged,
which rotation correctly records as a failure. Providers other than Cloudflare are
covered by the generic `dnshelp` parsing only.
