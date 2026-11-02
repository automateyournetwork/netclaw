# Plan

T001 Diagnose on the operator Risk (logs, daemon environment, unit verification); renew
the expired certificate by hand with only the provider token passed to lego.
T002 `acme.py`: `_provider_names()` from `lego dnshelp --code`; `_env_file_values()` from
`NETCLAW_RUNTIME_ENV` and its sibling `mesh.systemd.env` via `write-env.py`; `_lego_env()`
merges those names into a copy of the environment (environment wins); `issue()` and
`renew()` pass it to `_run()`, which gains an `env` argument. `renew()` adds
`--no-random-sleep`.
T003 Tests: `tests/n2n/test_acme_provider_env_170.py` (fake lego with real `dnshelp`
layout: passed set, `_FILE` form, precedence, unknown provider, no runtime env, unreadable
file); update the renew argv assertion in `test_rotation_truthfulness.py`.
T004 Live: staging issuance through the new code with the real lego and DNS provider and
a daemon-equivalent environment; apply to the operator Risk and restart the mesh.
Release 1.18.3, PR.
