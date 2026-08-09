# Phase 0 Research — Server Startup Check (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md` and the delivered script. Findings were
> measured then; only the write-up is retrospective.

---

## R1 — Can static analysis find dead servers?

**Decision**: **No. The process must actually be launched.**

A first pass by static import analysis reported **11 findings, 5 of them false**. `netclaw_tokens`
resolves at runtime via `sys.path`, so reading source cannot tell whether an import will succeed.

Only launching gave the truth: **7 real failures**. This result is recorded in the script's own
docstring so nobody repeats the shortcut.

**Alternatives considered**: AST import scanning (rejected — 45% false-positive rate); parsing
`requirements.txt` (rejected — that is exactly the declaration-vs-reality gap this surface exists to
close).

---

## R2 — What counts as failure?

**Decision**: Only a **fatal startup error**. A timeout is success.

An MCP stdio server that imports cleanly and then blocks reading stdio is behaving exactly as it
should. Treating a timeout as failure flags all 75 working servers.

This is the single most important design decision in the feature, and the obvious wrong
implementation.

---

## R3 — What must be distinguished?

**Decision**: Four states, not one.

| State | Why it matters |
|---|---|
| Missing Python module | Installable — a package problem |
| Entry point does not exist | **No install can fix it** — the file is absent (`aruba-cx-mcp`) |
| Wrong environment | The package exists system-wide but not in *that* env (`arista-cvp-mcp`) |
| Interpreter absent / remote server | An install gap or not applicable — **not** a broken registration |

Conflating these makes the surface noisy enough to ignore, and sends people to the wrong fix.

---

## R4 — The seven, and why each needs a different remedy

| # | Server | Cause | Remedy |
|---|---|---|---|
| 1 | `prisma-sdwan-mcp` | *originally read as* gated SDK | **Corrected by spec 090** — `pypi.org/prisma-sase` returns 200 and installs as 6.8.1b1. The bare `pip install` had died on **PEP 668**, not availability. One error read as another |
| 2 | `radkit-mcp` | Genuinely gated | Confirmed by 090: `radkit-client` 404s; `cisco-radkit-client` is a **relocation stub** whose build fails. Cisco ships code-signed wheels from radkit.cisco.com only |
| 3 | `aruba-cx-mcp` | Entry point absent | Vendor the server or unregister. **5 skills route to it** |
| 4 | `arista-cvp-mcp` | Wrong env — `urllib3` present system-wide (2.6.3), absent from its ephemeral `uv run --with` env | Fix that server's `--with` list. The naive reading ("install urllib3") is wrong and would waste an afternoon |
| 5–7 | `meraki-magic-mcp`, `gnmi-mcp`, `junos-mcp` | Public packages, blocked by the host | A dry-run confirmed **none pulls a shared pin**. This host's interpreter is **PEP 668 externally-managed**, and `netclaw_pip_install` is a bare `pip install` with no PEP 668 handling |

**Finding 5–7 is a gap in the helper, not in those servers.** Spec 077 mandates `netclaw_pip_install`
as the only sanctioned install path, and on this host that path cannot install new packages. Filed
as follow-up rather than fixed here — changing the repo's single install helper has its own blast
radius.

**None of the seven was silenced into `STARTUP_EXCEPTIONS`.** Doing so would defeat the check on the
day it was written.

---

## R5 — Fast enough for CI?

**Decision**: Yes, after tuning. **>10 minutes → 14 seconds.**

`TIMEOUT` 25→6 (a server that has not died in 6 s has imported successfully) plus
`ThreadPoolExecutor(8)`. A surface too slow for CI is a surface that gets disabled.

---

## R6 — Fail the build, or warn?

**Decision**: Warn — with a written exit condition.

Two of the seven need an SDK that is not publicly distributable, so **nobody can make this surface
green today**. `startup` goes in `ALWAYS_WARN`. The summary renders `PASS (with warnings)`, never a
bare `PASS` (FR-010) — a warning that looks like a pass is not a warning.

Exit condition, written into the code: remove `"startup"` from `ALWAYS_WARN` once the seven resolve.

---

## R7 — How is the checker itself tested?

**Decision**: Against fixtures with known startup behaviour, via `--config`.

9 new assertions cover: stdio-blocking is not a failure; a missing module fails and is named; an
absent entry point is distinguished; `--warn-only` exits 0; remote servers are skipped; and
`STARTUP_EXCEPTIONS` actually suppresses — **an untested suppression list is how a check quietly
stops checking**.

Every assertion captures the exit code **directly, never through a pipe**. That mistake misdiagnosed
spec 075's central premise.
