# Phase 0 Research — Arista ANTA validation (R25)

**Date**: 2026-08-05 | **Plan**: [plan.md](plan.md)

Everything below was measured — against PyPI, against a real virtualenv, and against
`clab-mandible-veos1` (vEOS-lab 4.36.1F) over live eAPI. Nothing is quoted from documentation.

---

## R1 — Licence and adoptability

**Decision**: Adoptable as a library. **Apache-2.0, "Copyright 2022 Arista Networks"** — read from
the upstream `LICENSE`, licence-identical to NetClaw, so none of the vendoring question that
deferred R11's candidate or blocked R15's two.

ANTA 1.9.0, Python ≥3.10, 12 declared dependencies.

**Important distinction**: ANTA is a **library and CLI, not an MCP server.** There is nothing to
adopt directly. The only question is how much NetClaw writes around it — answer: as little as
possible beyond the verdict discipline and the manifest shape.

---

## R2 — The dependency hazard, measured before installing

**Decision**: **Dedicated virtualenv, mandatory.**

A dry-run against the system interpreter (`pip install --dry-run anta`) reported it would install:

```
PySocks-1.7.1  anta-1.9.0  asyncssh-2.24.0  cryptography-50.0.0  cvprac-2.2.0
pydantic-extra-types-2.11.1
```

**`cryptography` 46.0.5 → 50.0.0** — four majors. Four installed distributions depend on it, **none
with an upper bound**:

| Dependent | Declares |
|---|---|
| `Authlib` | `cryptography` (unbounded) |
| `pygnmi` | `cryptography` (unbounded) |
| `service-identity` | `cryptography` (unbounded) |
| `sshsig` | `cryptography` (unbounded) |

NetClaw's own federation TLS stack (spec 060) is built on `cryptography`. **Spec 076's cryptography
incident is the standing warning, and this is the same shape.** The dry-run was run *first*,
precisely because of it.

**Every other shared dependency was already satisfied** — httpx 0.28.1 (needs ≥0.27), pydantic
2.13.4 (≥2.7), rich 13.9.4 (≥13.5.2,<16), requests 2.32.5, PyYAML 6.0.3, Jinja2 3.1.6. Only
`cryptography` moves, and only it forces the venv.

**Isolation verified after install**: venv holds `cryptography` 50.0.0; **system still reports
46.0.5.**

**Install-time note**: `python3 -m venv` **fails on this host** (no `ensurepip`). `virtualenv -p
/usr/bin/python3` works — the same route spec 076's installer uses, and the reason
`netclaw_venv_create` exists.

---

## R3 — Catalogue size: the manifest risk, quantified

**Decision**: Dispatcher + discovery. One tool per test is arithmetically impossible.

Enumerated from the installed package: **208 tests across 33 modules.**

| Category | Tests |
|---|---|
| interfaces | 26 |
| routing.bgp | 24 |
| security | 16 |
| hardware | 14 |
| snmp | 12 |
| system | 12 |
| logging | 10 |
| routing.generic | 8 |
| aaa, routing.isis, stp | 7, 7, 7 |
| mlag | 6 |
| *(21 further categories)* | |

At the ~283 tokens/tool that Catalyst Center measured, 208 tools ≈ **58,000 tokens — 11.6× the
ceiling**, squarely in the territory that forced 087 to build a dispatcher and rejected R5 at 2.36×.

---

## R4 — Does it actually work? Live proof

**Decision**: Yes. Verified against `clab-mandible-veos1`, `established=True`, `hw_model=vEOS-lab`.

| Case | Verdict | Message |
|---|---|---|
| `VerifyEOSVersion` (correct version) | **success** | — |
| `VerifyEOSVersion` (wrong version) | **failure** | *"EOS version mismatch - Actual: 4.36.1F not in Expected: 4.99.9M"* |
| `VerifyUptime` | success | — |
| `VerifyNTP` | **failure** | *"NTP status mismatch - Expected: synchronised Actual: …"* — a real finding on the lab device |
| `VerifyInterfaceUtilization` | success | — |
| unreachable address | **error** | *"show version has failed: ConnectError: All connection attempts failed"* |

**FR-001 is satisfied natively**: failures name observed *and* expected values without NetClaw
having to construct the message.

**FR-005 is satisfied natively**: an unreachable device yields `error`, not a set of failures. ANTA
gets this right, which is worth recording because specs 094 and 095 both had to *build* that
distinction.

---

## R5 — The trap this feature must block

**Finding**: **ANTA reports "feature not configured" as `failure`, not `skipped`.**

```
VerifyBGPPeerCount → failure
  "'show bgp summary vrf all' failed on veos1: BGP inactive"
```

BGP is not configured on this device. The honest answer is *"not applicable — this device does not
run BGP"*. ANTA says **failure**, and a summary that counts it would report a BGP problem on a device
that has no BGP at all.

This is the class of defect this repository keeps finding: R13's inert Suricata reporting 0 alerts,
R15's BMC timeout, R12's capped count of 10,000, R5's empty-org `count: 1`. **An absence rendered as
a finding, where the wrong reading is the natural one.**

The verdict enum genuinely has five values — `unset`, `success`, `failure`, `error`, `skipped` — so
`skipped` exists and is simply not used for this case.

**Consequence for design**: a failure whose message indicates the feature is inactive or the command
is unsupported MUST NOT be summarised as a plain failure. It is a **coverage gap**, and the summary
must say so separately. This is what FR-004 exists for, and the probe proves it is not hypothetical.

---

## R6 — Device targeting

**Decision**: Per-call address, credentials from the environment (clarified 2026-08-05, FR-013).

`AsyncEOSDevice` takes `host`, `username`, `password`, plus `port`, `proto`, `insecure`,
`disable_cache`, `enable`. No inventory file is required to construct a device — the per-call model
maps directly onto the library, so this choice costs nothing structurally.

**Note for the plan**: the lab device serves a self-signed certificate, so the `insecure` /
certificate posture must be explicit and disclosed in output — the same discipline spec 094 applied
to BMC TLS.
