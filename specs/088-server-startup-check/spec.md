# Spec 088 — Server Startup Check (fifth reconcile surface)

**Status**: implemented — findings resolved by [090](../090-fix-dead-servers/spec.md)
**Branch**: `088-server-startup-check`
**Date**: 2026-08-04

## Problem

NetClaw's reconciliation gate (`scripts/reconcile-mcp.py`, spec 075, extended by 077)
had four surfaces. All four validate that things are **declared** consistently:

| Surface | What it compares |
|---|---|
| `catalog` | installer coverage vs. vendored state |
| `docs` | documented capability counts vs. registrations |
| `portability` | registration paths vs. portability rules |
| `dependencies` | pin bounds and install paths in `requirements.txt` / install steps |

**None of them ran anything.** Nothing in the repository ever checked whether a
registered MCP server could start. So `reconcile-mcp.py` exited 0 — and CI passed —
while **seven of the 98 registered servers could not start at all**, with **22 skills**
routing to them.

This is the third instance of the same meta-pattern in this repo, and the reason this
spec generalises rather than just fixing the seven:

1. `check-dependency-pins.py` read only `requirements.txt`, never an installed version.
2. `verify-inventory-counts.py` checks headline arithmetic, never table membership.
3. Nothing checked whether a registered server can start.

A check that validates declarations cannot detect a declaration that is uniformly,
consistently wrong.

### How the seven were found — and why static analysis was not enough

A first pass by static import analysis reported 11 findings, **5 of them false**:
`netclaw_tokens` resolves at runtime via `sys.path`, so reading source cannot tell
whether an import will succeed. Only launching the process gave the truth. That result
is recorded in the script's own docstring so nobody repeats the shortcut.

## Requirements

- **FR-001** Launch every registered stdio server and detect fatal startup failure.
- **FR-002** A server that imports cleanly and then blocks reading stdio is **correct
  MCP behaviour**. A timeout MUST NOT be reported as a failure. (Getting this backwards
  flags all 75 working servers.)
- **FR-003** Distinguish *missing Python module* from *entry point does not exist* — they
  need different fixes, and installing packages would never have fixed `aruba-cx-mcp`.
- **FR-004** Skip remote/HTTP servers and servers whose interpreter is absent from the
  host: a missing `node` is an install gap, not a broken registration, and conflating
  them makes the check noisy enough to ignore.
- **FR-005** Name both the server and the specific cause in every finding.
- **FR-006** Support `--warn-only` (exit 0 with findings), matching every other surface.
- **FR-007** Support `--config` so the check is testable against fixtures with known
  startup behaviour, not only the live repository config.
- **FR-008** Run fast enough for CI. (First working version took **>10 minutes**;
  `TIMEOUT` 25→6 plus `ThreadPoolExecutor(8)` brought it to **14 s**.)
- **FR-009** Register as a fifth reconcile surface.
- **FR-010** A `WARN` surface MUST NOT render as a bare `PASS`. The summary line reads
  `PASS (with warnings)`.

## The seven findings, and why each needs a different fix

Deliberately **not** silenced into `STARTUP_EXCEPTIONS` — that would defeat the check on
the day it was written. Recorded in the script, and visible on every run.

**1. Gated SDK — no install can fix it**
- ~~`prisma-sdwan-mcp` → `prisma_sase` (no matching distribution on PyPI)~~
  **CORRECTED by spec 090: this was wrong.** `pypi.org/prisma-sase` returns 200 and it
  installed cleanly as 6.8.1b1. The original bare `pip install` had died on **PEP 668**,
  not on availability — one error read as another.
- `radkit-mcp` → `radkit_client` (Cisco RADKit). **Confirmed by spec 090**: `radkit-client`
  404s and `cisco-radkit-client` is a *relocation stub* whose build fails with "This package
  has been relocated!" — Cisco ships code-signed wheels from radkit.cisco.com only.

Needs an `EXTERNAL_INTEGRATIONS` entry or unregistration. A registered server nobody can
install advertises a capability NetClaw does not have.

**2. No entry point at all**
- `aruba-cx-mcp` → `mcp-servers/aruba-cx-mcp/aruba_cx_mcp_server.py` does not exist

5 skills route to it. Either vendor the server or unregister it.

**3. Wrong environment, not a missing package**
- `arista-cvp-mcp` → `urllib3`

It launches via `uv run --directory ... --with fastmcp`, an ephemeral uv environment.
`urllib3` **is** installed system-wide (2.6.3) — it is absent from *that* env. The fix is
that server's `--with` list. Recorded because the naive reading ("install urllib3") is
wrong and would waste someone's afternoon. This server has 0 skills routing to it.

**4. Installable, blocked by the host**
- `meraki-magic-mcp` → `meraki` (PyPI 4.3.1)
- `gnmi-mcp` → `pygnmi` (PyPI 0.8.15)
- `junos-mcp` → `jnpr` (PyPI junos-eznc 2.8.2)

All three are public and a dry-run confirmed **none pulls a shared pin**
(fastmcp/mcp/httpx/cryptography/pydantic all unmoved). But this host's system
interpreter is **PEP 668 externally-managed**, and `netclaw_pip_install`
(`scripts/lib/pip-helper.sh`) is a bare `"$py" -m pip install "$@"` with **no PEP 668
handling** — so it cannot install them either.

> **This is a gap in the helper, not in these servers.** Spec 077 mandates
> `netclaw_pip_install` as the only sanctioned install path, and on this host that path
> does not work for new packages. Filed as follow-up; not fixed here, because changing the
> repo's single install helper is its own change with its own blast radius.

## Why warn-only, and when it stops

`startup` is in `ALWAYS_WARN` in `reconcile-mcp.py`: it reports but never fails the
build, regardless of `--warn-only`. Two of the seven need an SDK that is not publicly
distributable, so **nobody can make this surface green today**. Hard-failing would force
either reverting the check or papering the seven into `STARTUP_EXCEPTIONS` — both worse
than a loud warning.

**Exit condition, written into the code:** remove `"startup"` from `ALWAYS_WARN` once the
seven are resolved. After that, a server that cannot start breaks the build.

## Verification

`tests/reconcile/run-tests.sh` — 32 assertions total (23 pre-existing, 9 new), bash +
Python stdlib only, fixtures in a temp dir, repository never modified. New assertions
cover: stdio-blocking is not a failure, missing module fails and is named, absent entry
point is distinguished, `--warn-only` exits 0, remote servers are skipped, and
`STARTUP_EXCEPTIONS` actually suppresses (an untested suppression list is how a check
quietly stops checking).

Every assertion captures the exit code **directly** — never through a pipe. That mistake
misdiagnosed spec 075's central premise.

## Out of scope

- Fixing the seven (four different fixes, two impossible without vendor access).
- Adding PEP 668 handling to `netclaw_pip_install` (follow-up).
- Checking that a server that starts also serves a valid tool manifest — a deeper probe
  requiring an MCP handshake, not just a launch.
