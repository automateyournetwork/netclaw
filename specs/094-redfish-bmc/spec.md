# Spec 094 — Redfish BMC out-of-band visibility (R15)

**Status**: implemented
**Branch**: `094-redfish-bmc`
**Date**: 2026-08-04
**Roadmap**: R15 — Redfish / BMC out-of-band

## Summary

`redfish-mcp`: **6 tools, ~728 tokens**, read-only out-of-band hardware visibility over the DMTF
Redfish API — power state, component health, thermal/fan/PSU readings, BMC firmware, host
firmware inventory, and SEL event logs. Works against iDRAC, iLO, XClarity and Supermicro, which
all implement Redfish.

R15's stated purpose is one question NetClaw could not answer at all: **"is the box dead, or is
it the network?"** A BMC is the only vantage point that can tell them apart, because it answers
when the operating system cannot.

**Verified end to end against the DMTF Redfish mockup server**, so no hardware was required.

## The distinction, and why it is the whole spec

The trap is **symmetric**, and each direction is a different wrong answer:

| Reading | Establishes | Must never be reported as |
|---|---|---|
| BMC **unreachable** | **nothing about the host** | "the host is down" |
| BMC reachable, `PowerState: Off` | the host **is** off — a *fact* | — |
| BMC reachable, `PowerState: On` | the host has **power** | "the host is healthy" / "the OS is up" |
| BMC reachable, health `Critical` | a **hardware** fault | anything about the OS |

The first row is the important one. **A BMC has its own NIC, its own network path and its own
credentials, all separate from the host's.** A BMC timeout is a statement about the BMC path —
reporting "host down" from it is precisely the mistake out-of-band access exists to prevent, and
it is the most natural mistake to make, because the tool was reached for in order to answer
"is the host down?".

So the host verdict is a **mandatory, first-class field**, not something a skill infers from raw
JSON:

- `verdict.host_verdict()` **raises** if asked to derive a host state from an unreachable BMC.
- `verdict.emit()` **raises** if a response would carry a host claim with no verdict behind it.

There is no code path that emits a reading without the qualifier. Same chokepoint shape as
nsm-mcp's posture (091), document-mcp's `emit()` (082) and catc-mcp's `_envelope()` (087).

**An auth rejection is a live BMC.** HTTP 401/403 proves it answered, so it is reported as a
credential problem explicitly rather than collapsed into "unreachable" — which would nudge a
reader toward "the host is down". Spec 087 hit this exact shape with `httpx.HTTPStatusError`.

## Built, not adopted — and why

Both roadmap candidates are **unvendorable**:

| Candidate | Licence | Verdict |
|---|---|---|
| `carlosedp/redfish-mcp-server` | **none at all** | cannot vendor code with no licence |
| `fredriksknese/mcp-redfish` | `NOASSERTION` | not a recognised OSS licence |

Spec 082 rejected an upstream on exactly this ground. Redfish is a stable, self-describing DMTF
standard, so the client is a thin HTTP layer rather than a vendor SDK — building was cheaper than
resolving a licence question.

## Read-only, enforced at the transport

`client.py` implements **`get()` and nothing else**. Redfish exposes `#ComputerSystem.Reset` as a
POST action on every system, and a power cycle on the wrong box is an outage.

Under Principle III that write would need ITSM gating. The safer answer is not to build it: a
reset is an operator action through the BMC UI under change control. Asserted by tests that scan
the source for `.post(`/`.put(`/`.patch(`/`.delete(` and for any reset action path.

## Requirements

- **FR-001** Read-only. No power control, no virtual media, no firmware push.
- **FR-002** Every response mentioning host power or health MUST carry a verdict; emitting one
  without it MUST raise.
- **FR-003** An unreachable BMC MUST yield `host_state: UNKNOWN` and name the conclusion not to
  draw. It MUST NOT be convertible into a host state.
- **FR-004** An auth rejection MUST be reported as a reachable BMC with a credential problem.
- **FR-005** The endpoint MUST never be guessed — an unset `REDFISH_URL` refuses, because
  probing an unknown BMC risks querying someone else's hardware.
- **FR-006** TLS verification defaults **off** (BMCs ship self-signed certs) but MUST be
  disclosed in every response. A silent downgrade is unacceptable; a visible one is workable.
- **FR-007 (empty ≠ good news)** An empty SEL, an empty firmware inventory, and an absent
  Thermal/Power subresource MUST each be reported as a coverage gap, never as "no problem".
- **FR-008** No log output on stdout. This is a stdio server and stray logging corrupts the
  JSON-RPC stream.

## Verification

`bash tests/redfish/run-tests.sh` — **15 assertions, 0 failures**. Verdict and read-only
assertions are pure stdlib and always run; the live ones skip without `httpx` and the mockup
container, so this is CI-safe (spec 075 SC-013).

The assertions that carry the spec:

- an unreachable BMC yields `UNKNOWN` and names `do_not_conclude: host is down`
- `Off` is reported as a **fact**; `On` carries the "OS may be hung" caveat
- an unrecognised `PowerState` becomes `POWER_STATE_UNREPORTED` rather than being guessed
- a hardware fault is reported as **independent of OS state**
- **deriving a host state from an unreachable BMC is refused**
- **emitting a host claim without a verdict is refused**
- the client contains no verb but GET, and no reset path anywhere
- an unset endpoint refuses rather than guessing
- TLS-off is disclosed

Live against the **DMTF mockup** (Redfish 1.15.0): read a Contoso 3500 with `PowerState: On`,
health `OK`, 2 processors / 8 cores each, 96 GiB, 3 temperature sensors, 2 fans and 344 W
consumed of an 800 W capacity — with `verdict: POWERED_ON` attached. Pointing the same tool at a
dead port returned `host_state: UNKNOWN`, `bmc_reachable: false`.

**One real bug found and fixed during verification:** `httpx` logs every request at INFO, and
those lines were being emitted during tool calls. On a stdio transport that can corrupt the
protocol stream. Silenced at the logger, and asserted clean.

Reconciliation: **PASS on all seven surfaces.** Counts 160→161 MCP, 218→219 skills.

## Out of scope

- **Power control of any kind.** Not a limitation to lift later — see above.
- **Vendor OEM extensions.** iDRAC, iLO and XClarity each add proprietary `Oem` subtrees. The
  standard Redfish surface is read here; OEM-specific data is **not** parsed, and `redfish_status`
  reports which `Oem` keys a service advertises so an operator can see what is being left on the
  table.
- **Verification against real hardware.** The DMTF mockup is a faithful implementation of the
  standard, but it is not a Dell or HPE BMC. Vendor quirks — partial subsets, non-standard
  thresholds, slow SEL reads — are unverified and the skill says so.
- **BMC credential storage.** The skill points at Vault; wiring it is a separate concern.
- **Cisco UCS/Intersight (R7).** The roadmap suggests folding it here. Intersight is a cloud API,
  not Redfish, so it stays its own item.
