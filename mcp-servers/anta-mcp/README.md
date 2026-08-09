# anta-mcp — Arista ANTA validation

**Spec**: [098](../../specs/098-arista-anta-validation/spec.md) · **Roadmap**: R25
**Upstream**: [ANTA](https://github.com/aristanetworks/anta) 1.9.0 — Apache-2.0, Copyright 2022
Arista Networks

The **assertion layer**. Every other NetClaw source reads state; this one asserts on it and returns
a structured verdict.

| | |
|---|---|
| Tools | **4** |
| Catalogue reachable | **208 tests / 33 modules** |
| Manifest | **1,272 / 5,000 tokens** (0.25×) |
| Transport | stdio |
| Posture | **read-only** — ANTA tests, it never configures |
| Runtime | **its own virtualenv** (see below) |

## Tools

| Tool | Contacts a device? |
|---|---|
| `anta_list_tests(category, keyword, limit)` | no |
| `anta_describe_test(test)` | no |
| `anta_run_tests(host, tests\|category, inputs, verify_tls, port)` | yes |
| `anta_status()` | no |

Discovery works with **no device configured at all**, so an operator can explore what is testable
before connecting anything.

## Why 4 tools and not 208

One tool per test would cost roughly **58,000 tokens — 11.6× the ceiling**, the same failure that
forced spec 087 to build a dispatcher over Catalyst Center's 515 tools. Tests are described on
demand instead of enumerated.

## Why its own virtualenv

Not a preference. `pip install anta` moves **cryptography 46.0.5 → 50.0.0**, and four installed
distributions depend on `cryptography` with **no upper bound** — `Authlib`, `pygnmi`,
`service-identity`, `sshsig` — including NetClaw's federation TLS stack (spec 060).

Measured by `pip install --dry-run` **before** installing anything, which is the lesson spec 076's
cryptography incident taught. Verified after: venv holds 50.0.0, system still reports 46.0.5.

> `python3 -m venv` fails on hosts without `ensurepip`. Use `netclaw_venv_create`, or
> `virtualenv -p /usr/bin/python3`.

## The verdict model

Five outcomes, counted separately: `pass`, `fail`, **`not_applicable`**, `skipped`, `error`.

**`not_applicable` is a reclassification, and it is the point of this server.** ANTA natively
reports a test for an *unconfigured* feature as a **failure**. Measured against
`clab-mandible-veos1`:

```
VerifyBGPPeerCount → failure
  "'show bgp summary vrf all' failed on veos1: BGP inactive"
```

That switch has no BGP. Counted as a failure, it claims a BGP fault where there is no BGP —
an absence rendered as a finding, the same class as spec 091's inert Suricata, 094's BMC timeout,
096's capped count and 095's empty Mist org.

The rule is **deliberately narrow**: only messages clearly indicating an inactive feature or an
unsupported command are reclassified, the original message is always preserved, and anything
uncertain stays `fail`. An over-eager rule would hide real failures, which is worse than the problem
it solves.

**No health percentage is ever emitted.** `passed / total` is meaningless with `not_applicable` and
`skipped` in the denominator; `verdict.health_percentage()` raises rather than computing one.

## Environment

| Variable | Meaning |
|---|---|
| `ANTA_USERNAME` / `ANTA_PASSWORD` | device credentials — **environment only**, never tool arguments, never returned |
| `ANTA_ENABLE_PASSWORD` | optional, for tests needing enable mode |
| `ANTA_VERIFY_TLS` | default `false` (lab switches ship self-signed certs) — **always disclosed** in output as `tls_verified` |
| `ANTA_TIMEOUT` | per-device timeout, default 30s |

## Install and test

```bash
./scripts/install.sh                 # select "Arista ANTA Validation"
bash tests/anta/run-tests.sh         # 21 assertions; live ones skip without ANTA_TEST_HOST
```

## Boundaries

EOS only — this is not multivendor validation. `arista-cvp-mcp` is the management plane, pyATS and
the multivendor CLI driver are the device-CLI plane, and this is the validation plane. Use it to
assert, not to fetch.
