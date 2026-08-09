# Implementation Plan: Redfish BMC out-of-band visibility (R15)

**Branch**: `094-redfish-bmc` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)
**Roadmap**: R15 — Redfish / BMC out-of-band

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, the delivered server and tests, and the git
> history. No `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096
> drift.

## Summary

`redfish-mcp`: **6 tools, ~728 tokens**, read-only out-of-band hardware visibility over the DMTF
Redfish API — power state, component health, thermal/fan/PSU, BMC firmware, host firmware inventory,
SEL logs. Works against iDRAC, iLO, XClarity and Supermicro.

R15 exists for one question NetClaw could not answer at all: **"is the box dead, or is it the
network?"** A BMC is the only vantage point that can tell them apart, because it answers when the
operating system cannot.

**Verified end to end against the DMTF Redfish mockup, so no hardware was required.**

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `httpx` (thin HTTP client — Redfish is a self-describing DMTF standard, so
no vendor SDK is needed)
**Storage**: None — stateless
**Testing**: `bash tests/redfish/run-tests.sh` — **15 assertions**. Verdict and read-only assertions
are pure stdlib and always run; live ones skip without `httpx` and the mockup container, so it is
CI-safe (spec 075 SC-013)
**Target Platform**: Linux
**Project Type**: MCP integration — **built**, not adopted
**Performance Goals**: Manifest ≤ 5,000 (achieved ~728)
**Constraints**: Read-only, enforced at the transport. TLS verification defaults off but must be
disclosed
**Scale/Scope**: 6 tools

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **I. Safety-First (NON-NEGOTIABLE)** | A power cycle on the wrong box is an outage | **PASS** — power control is not implemented at all |
| **II. Read-Before-Write** | No writes | **PASS** — `client.py` implements `get()` and nothing else |
| **III. ITSM-Gated Changes** | Any write would need CR gating | **PASS by omission** — the safer answer is not to build it; a reset is an operator action through the BMC UI under change control |
| **IX. Security by Default** | No silent TLS downgrade; no endpoint guessing | **PASS** — FR-005, FR-006 |
| **XI. Artifact Coherence** | All touchpoints | **PASS** — counts 160→161 MCP, 218→219 skills |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## The design centre: a symmetric distinction, enforced by a chokepoint

| Reading | Establishes | Must never be reported as |
|---|---|---|
| BMC **unreachable** | **nothing about the host** | "the host is down" |
| BMC reachable, `PowerState: Off` | the host **is** off — a *fact* | — |
| BMC reachable, `PowerState: On` | the host has **power** | "the host is healthy" / "the OS is up" |
| BMC reachable, health `Critical` | a **hardware** fault | anything about the OS |

The first row is the important one. **A BMC has its own NIC, its own network path and its own
credentials, all separate from the host's.** A BMC timeout is a statement about the BMC path.
Reporting "host down" from it is precisely the mistake out-of-band access exists to prevent — and
the most natural mistake to make, because the tool was reached for in order to answer "is the host
down?".

So the verdict is a **mandatory, first-class field**, not something a skill infers from raw JSON:

- `verdict.host_verdict()` **raises** if asked to derive a host state from an unreachable BMC.
- `verdict.emit()` **raises** if a response would carry a host claim with no verdict behind it.

Same chokepoint shape as nsm-mcp's posture (091), document-mcp's `emit()` (082) and catc-mcp's
`_envelope()` (087).

**An auth rejection is a live BMC.** HTTP 401/403 proves it answered, so it is reported as a
credential problem rather than collapsed into "unreachable" — which would nudge a reader toward
"the host is down".

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a recurrence gate |
| **Built rather than adopted** | Both roadmap candidates are **unvendorable**: `carlosedp/redfish-mcp-server` has **no licence at all**; `fredriksknese/mcp-redfish` is `NOASSERTION` | Spec 082 rejected an upstream on exactly this ground. Redfish is a stable, self-describing standard, so the client is a thin HTTP layer — building was cheaper than resolving a licence question |
| **TLS verification defaults off** | BMCs ship self-signed certificates; defaulting on would make the tool unusable out of the box | A **silent** downgrade would be unacceptable, so it is disclosed in every response. A visible downgrade is workable; an invisible one is not |
