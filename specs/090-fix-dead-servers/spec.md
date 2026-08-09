# Spec 090 — Fix the dead servers, and make `startup` a hard gate

**Status**: implemented
**Branch**: `090-fix-dead-servers`
**Date**: 2026-08-04
**Follows**: [088](../088-server-startup-check/spec.md) (found them), [089](../089-meraki-official/spec.md) (retired one)

## Summary

Spec 088 found **7 registered MCP servers that could not start** and shipped its check
warn-only, because two were believed to need SDKs that were not publicly distributable.

**Six are now fixed and one is excepted with a written reason**, so the `startup` surface is
promoted from advisory to a **hard gate**: a registered server that cannot start now fails
the build. That was 088's stated exit condition, and this spec meets it.

| Server | Cause | Resolution |
|---|---|---|
| `meraki-magic-mcp` | missing `meraki` SDK | retired in 089 (official server adopted) |
| `gnmi-mcp` | missing `pygnmi` | installed 0.8.15 |
| `junos-mcp` | missing `jnpr`, **then** missing `devices.json` | installed junos-eznc 2.8.2; installer seeds an empty inventory |
| `prisma-sdwan-mcp` | missing `prisma_sase` | installed prisma-sase 6.8.1b1 |
| `aruba-cx-mcp` | "entry point does not exist" | **registration path was wrong**, nothing was missing |
| `arista-cvp-mcp` | missing `urllib3`, **then** hardcoded `/home/admin/app.log` | `--with` list extended; log path patched at install |
| `radkit-mcp` | missing `radkit_client` | **excepted** — not obtainable from PyPI |

## The root cause, and the correction it forces

`netclaw_pip_install` (`scripts/lib/pip-helper.sh`) — the single install path spec 077
mandates — was a bare `"$py" -m pip install "$@"` with **no PEP 668 handling**. On this
externally-managed host it could not install *any* new package.

Meanwhile **56 call sites** in `install-steps.sh` each papered over that independently:

```bash
netclaw_pip_install X 2>/dev/null || \
    netclaw_pip_install --break-system-packages X 2>/dev/null || \
    log_warn "… install failed"
```

Both calls discarded stderr, so a **total** install failure produced one warning line in a
long install log and **exit 0**. That is why three servers sat dead while the installer
reported success.

### A correction to spec 088

Spec 088 recorded `prisma_sase` as "not on PyPI, no install can fix it". **That was wrong.**
`pypi.org/prisma-sase` returns 200 and it installed cleanly. The claim came from a bare
`pip install` that had actually died on **PEP 668** — I read an environment error as an
availability error, and then wrote the wrong conclusion into a spec. Corrected in 088's own
text rather than quietly here.

RADKit, by contrast, is confirmed unobtainable: `radkit-client` 404s, and
`cisco-radkit-client` is a **relocation stub** whose build fails with *"This package has been
relocated!"* — Cisco distributes code-signed wheels from `radkit.cisco.com` only. It is
already declared in `EXTERNAL_INTEGRATIONS`, so it is excepted, not unregistered: the
integration is real for operators who have RADKit.

## Two defects hidden behind one error message

Fixing the reported error revealed a second, different failure in two cases. Worth recording,
because "the check is green" after one fix would have been wrong both times.

**`junos-mcp`** — installing `junos-eznc` fixed the import, and the server then died on a
missing `devices.json`. The repo ships only `devices-template.json`, which contains
placeholder credentials and a device whose `ip` is literally `"ip"`. Seeding that would plant
fake credentials, so the installer writes an **empty** `{}` inventory: the server starts and
honestly reports `0 device(s)`.

**`arista-cvp-mcp`** — the `uv run --with` list omitted `urllib3` and `python-dotenv`.
`urllib3` **is** installed host-wide, which is irrelevant: `uv run` never sees system
site-packages, so the obvious reading of the error was wrong. Underneath that, upstream
hardcodes `logging.basicConfig(filename='/home/admin/app.log')` — a foreign home directory,
raising `FileNotFoundError` before startup. **This is the same defect class spec 075 was
written for**, which found three integrations hardcoded to a foreign home; this was a fourth,
hidden behind an unrelated `ModuleNotFoundError`.

That clone is gitignored, so a working-copy edit is lost on the next fresh install. It is
patched **at install time**, idempotently, re-applied after every `git pull` — the same
durable-patch shape the Slack `fetch-interceptor` problem taught us to use for vendored code.
The patch was verified against a **pristine upstream download**, not just the local copy,
because the committed artifact is the patch and not the edit.

**A third defect surfaced once it got that far**: `fastmcp run` defaults to HTTP on
`127.0.0.1:8000`, so a server registered as stdio would bind a port and be unreachable by
its own client. `--transport stdio` is now explicit. This was latent — the server never
previously survived long enough to choose a transport. Swept the whole config: it is the only
`fastmcp run` registration, so this is not systemic.

## Requirements

- **FR-001** `netclaw_pip_install` MUST handle PEP 668 itself: detect
  `externally-managed-environment`, announce the retry, and retry with
  `--break-system-packages`.
- **FR-002** It MUST NOT swallow failures. On failure it prints what it was installing and
  the real pip output, and returns non-zero. A single install path is only worth having if
  its failures are legible.
- **FR-003** Remove the redundant per-call-site `--break-system-packages` retry. **53 sites**
  collapsed; `netclaw_pip_install` calls went 129 → 80 and stderr-discarding pip calls
  120 → 21, with the 94 `component_install_*` functions unchanged.
- **FR-004** Install the three obtainable SDKs **without moving a shared pin**.
- **FR-005** Fix `aruba-cx-mcp`'s registration path and `arista-cvp-mcp`'s environment and
  log path.
- **FR-006** Except `radkit-mcp` with a reason precise enough that nobody retries `pip`.
- **FR-007** Remove `startup` from `ALWAYS_WARN`. A dead server MUST fail the build.
- **FR-008** The checker MUST distinguish *a data file the server loads* from *a missing
  entry point* — 088's generic pattern reported `devices.json` as an entry-point failure and
  sent me looking in the wrong place.

## Shared-pin safety

Spec 076's cryptography incident is the standing warning, so this was checked rather than
assumed. `junos-eznc` pulls **paramiko 5.0.0**, which would be alarming — except
`multivendor-cli-mcp` runs from its own `.venv` (paramiko 4.0.0, netmiko 4.7.0, nornir 3.5.0,
napalm 5.2.0, cryptography 49.0.0), untouched by a system-interpreter install. Verified
directly.

| Pin | Before | After |
|---|---|---|
| `fastmcp` | 2.14.7 | 2.14.7 |
| `mcp` | 1.28.1 | 1.28.1 |
| `httpx` | 0.28.1 | 0.28.1 |
| `cryptography` | 46.0.5 | 46.0.5 |
| `pydantic` | 2.13.4 | 2.13.4 |
| `urllib3` | 2.6.3 | 2.6.3 |

## Verification

Reconciliation is **PASS on all six surfaces with no warnings** — the first time since 088.

The hard gate was proven non-vacuous: pointing `gnmi-mcp` at a nonexistent file produced
`Reconciliation: FAIL` and **exit 1**, then restored to green.

`tests/reconcile/run-tests.sh` — **50 assertions, 0 failures** (42 before, 8 new): PEP 668
retry happens and is announced; a genuine failure returns non-zero with the real pip error;
the failure names what it was installing; no `--break-system-packages` call sites remain; a
dead server fails reconciliation; and a missing data file is distinguished from a missing
entry point.

One pre-existing test was **passing for the wrong reason** and is fixed: the
`STARTUP_EXCEPTIONS` test replaced an empty `= {}` literal, which silently stopped matching
once the dict held a real entry. It now injects after the opening brace and asserts the
injection took.

## Out of scope

- The 21 remaining `2>/dev/null` pip call sites, which are optional-dependency installs
  where a failure is genuinely tolerable. They no longer hide a PEP 668 refusal, since the
  helper handles that before returning.
- Obtaining RADKit. That needs a Cisco account and a code-signed wheel from
  `radkit.cisco.com`; the exception documents the path.

## The hard gate cannot live in CI — learned the hard way

The first push made `startup` a hard gate in `reconcile-mcp.py`, and **CI failed immediately
on a healthy tree**: a fresh container has no vendored clones (they are gitignored runtime
clones), so 30+ *uninstalled* components read as "entry point does not exist".

The workflow's own header already stated the constraint I had broken — spec 075's **SC-013**:
this job "needs no dependencies, no network access, no credentials, and **no installed
NetClaw agent**". A surface that launches real servers violates that by construction.

A first attempt to fix it by skipping components whose vendored *directory* is absent was
**too coarse**: `prisma-sdwan-mcp`'s directory is tracked while its server file is a runtime
clone, so it still failed. Directory presence cannot distinguish "misregistered" from "not
installed".

The resolution splits the two kinds of check rather than weakening either:

- **CI gates the five declaration surfaces.** They compare repository artifacts against each
  other, need nothing installed, and are meaningful in a fresh container — SC-013 honoured.
- **`startup` gates locally**, where install state is real, and runs `--warn-only` in CI so a
  regression is still visible in the log.

Verified by cloning the branch into a clean tree and running both: the declaration gate exits
0, and the contract tests pass (51 there, 52 locally — the junos assertion skips itself when
`junos-mcp-server` is not cloned).

One pre-existing test had silently acquired the same defect: `"reconcile-mcp.py exits 0 on a
reconciled tree"` ran the full set, so once `startup` joined it, it asserted something about
the machine rather than the repository. Now scoped to the declaration surfaces.

## A known limitation of the check

`check-server-startup.py` treats "imported cleanly and did not exit fatally" as success. It
therefore **passed `arista-cvp-mcp` while it was binding an HTTP port** instead of speaking
stdio — starting is not the same as being reachable. Catching that needs an MCP handshake
over the transport the registration declares, which is a deeper probe than this surface
performs. Recorded rather than left implied: this gate proves servers start, not that clients
can talk to them.
