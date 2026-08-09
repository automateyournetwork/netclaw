# Phase 0 Research — Fix the dead servers (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md` and the delivered change.

---

## R1 — Was spec 088's diagnosis correct?

**Decision**: Mostly, with **one wrong conclusion that had to be corrected**.

| 088 said | Reality |
|---|---|
| `prisma_sase` "not on PyPI, no install can fix it" | **Wrong.** `pypi.org/prisma-sase` returns 200; installed cleanly as 6.8.1b1. The bare `pip install` had died on **PEP 668** — an *environment* error read as an *availability* error, and the wrong conclusion written into a spec |
| `radkit_client` unobtainable | **Confirmed.** `radkit-client` 404s; `cisco-radkit-client` is a **relocation stub** whose build fails with *"This package has been relocated!"* Cisco ships code-signed wheels from `radkit.cisco.com` only |

The correction was written **into 088's own text**, not quietly here. RADKit is already declared in
`EXTERNAL_INTEGRATIONS`, so it is **excepted, not unregistered** — the integration is real for
operators who have RADKit.

---

## R2 — What actually caused three servers to sit dead?

**Decision**: The install helper, not the servers.

`netclaw_pip_install` was a bare `"$py" -m pip install "$@"` with no PEP 668 handling — on this
externally-managed host it could not install anything new. **56 call sites** independently papered
over it with a `--break-system-packages` retry, and **both calls discarded stderr**, so a total
failure produced one warning line and **exit 0**.

An installer that reports success while installing nothing is worse than one that fails.

---

## R3 — One error message, two defects

Fixing the reported error revealed a **second, different** failure in two cases. Recorded because
"the check is green after one fix" would have been wrong both times.

**`junos-mcp`** — installing `junos-eznc` fixed the import; the server then died on a missing
`devices.json`. The repo ships only `devices-template.json`, containing placeholder credentials and
a device whose `ip` is literally `"ip"`. Seeding that would plant fake credentials, so the installer
writes an **empty `{}`** inventory: the server starts and honestly reports `0 device(s)`.

**`arista-cvp-mcp`** — the `uv run --with` list omitted `urllib3` and `python-dotenv`. `urllib3`
**is** installed host-wide, which is irrelevant: `uv run` never sees system site-packages, so the
obvious reading of the error was wrong. Underneath that, upstream hardcodes
`logging.basicConfig(filename='/home/admin/app.log')` — a foreign home directory, raising
`FileNotFoundError` before startup.

**That is the same defect class spec 075 was written for**, which found three integrations hardcoded
to a foreign home. This was a fourth, hidden behind an unrelated `ModuleNotFoundError`.

---

## R4 — A third defect, latent until the server survived long enough to hit it

`fastmcp run` defaults to **HTTP on 127.0.0.1:8000**, so a server registered as stdio would bind a
port and be unreachable by its own client. `--transport stdio` is now explicit.

The whole config was swept: it is the **only** `fastmcp run` registration, so this is not systemic.

---

## R5 — Do the installs move a shared pin?

**Decision**: No — verified, not assumed. Spec 076's cryptography incident is the standing warning.

`junos-eznc` pulls **paramiko 5.0.0**, which would be alarming — except `multivendor-cli-mcp` runs
from its own `.venv` (paramiko 4.0.0, netmiko 4.7.0, nornir 3.5.0, napalm 5.2.0, cryptography
49.0.0), untouched by a system-interpreter install. Verified directly. `fastmcp` stayed at 2.14.7.

---

## R6 — Should the checker change too?

**Decision**: Yes. It must distinguish *a data file the server loads* from *a missing entry point*.

088's generic pattern reported `devices.json` as an entry-point failure and sent the investigation
to the wrong place (FR-008).

---

## R7 — Is the gate promotable?

**Decision**: Yes. Six fixed, one excepted with a reason precise enough that nobody retries `pip`.

`startup` comes out of `ALWAYS_WARN`. **A dead server now fails the build** — 088's written exit
condition, met.
