# Phase 0 Research — Redfish BMC out-of-band visibility (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md`, the delivered server and its tests.

---

## R1 — Adopt or build?

**Decision**: **Build.** Both candidates are unvendorable.

| Candidate | Licence | Verdict |
|---|---|---|
| `carlosedp/redfish-mcp-server` | **none at all** | cannot vendor code with no licence |
| `fredriksknese/mcp-redfish` | `NOASSERTION` | not a recognised OSS licence |

Spec 082 rejected an upstream on exactly this ground. Redfish is a **stable, self-describing DMTF
standard**, so the client is a thin HTTP layer rather than a vendor SDK — building was cheaper than
resolving a licence question, and carries no ongoing licence risk.

---

## R2 — What is the actual failure mode this must prevent?

**Decision**: It is **symmetric**, and both directions are different wrong answers.

The natural mistake: the tool is reached for *in order to answer* "is the host down?", so an
unreachable BMC feels like a "yes". It is not. **A BMC has its own NIC, its own network path and its
own credentials, all separate from the host's** — a BMC timeout is a statement about the BMC path
and establishes **nothing** about the host.

The other direction matters too: `PowerState: On` establishes the host has **power**, not that the
OS is up or the box is healthy.

Only one reading is a fact about the host: **BMC reachable + `PowerState: Off` ⇒ the host is off.**

---

## R3 — How do you stop a skill inferring the wrong thing from raw JSON?

**Decision**: Make the verdict mandatory and enforce it in code, not documentation.

- `verdict.host_verdict()` **raises** if asked to derive a host state from an unreachable BMC.
- `verdict.emit()` **raises** if a response would carry a host claim with no verdict behind it.

There is no code path that emits a reading without the qualifier. Same shape as nsm-mcp's posture
(091), document-mcp's `emit()` (082), catc-mcp's `_envelope()` (087) — this repo's standard answer
to "how do we stop someone forgetting".

---

## R4 — Is an auth rejection an unreachable BMC?

**Decision**: **No — it is a live BMC.**

HTTP 401/403 proves the BMC answered. Collapsing it into "unreachable" would nudge a reader toward
"the host is down", which is the exact error the feature exists to prevent. Reported as a credential
problem explicitly (FR-004).

Spec 087 hit this same shape with `httpx.HTTPStatusError`.

---

## R5 — Should power control be implemented?

**Decision**: **No, and not as a limitation to lift later.**

Redfish exposes `#ComputerSystem.Reset` as a POST action on every system. A power cycle on the wrong
box is an outage. Under Principle III such a write would need ITSM gating — but the safer answer is
not to build it: a reset is an operator action through the BMC UI under change control.

Enforced at the transport: `client.py` implements **`get()` and nothing else**, asserted by tests
that scan the source for `.post(`/`.put(`/`.patch(`/`.delete(` and for any reset action path.

---

## R6 — Can this be verified without hardware?

**Decision**: Yes — the **DMTF Redfish mockup** (Redfish 1.15.0).

Read a Contoso 3500: `PowerState: On`, health `OK`, 2 processors / 8 cores each, 96 GiB, 3
temperature sensors, 2 fans, 344 W of an 800 W capacity — with `verdict: POWERED_ON` attached.
Pointing the same tool at a dead port returned `host_state: UNKNOWN`, `bmc_reachable: false`.

**Limitation stated rather than hidden**: the mockup is a faithful implementation of the standard,
but it is not a Dell or HPE BMC. Vendor quirks — partial subsets, non-standard thresholds, slow SEL
reads — are unverified, and the skill says so.

---

## R7 — Other "empty is not good news" cases

**Decision**: Three of them, each a coverage gap rather than a clean bill of health (FR-007).

- an empty SEL
- an empty firmware inventory
- an absent Thermal/Power subresource

Same class as 091's inert Suricata and 092's `0 datasets`.

---

## R8 — Endpoint discovery

**Decision**: **Never guess.** An unset `REDFISH_URL` refuses, because probing an unknown BMC risks
querying **someone else's hardware** (FR-005).

---

## R9 — A real bug found during verification

`httpx` logs every request at INFO, and those lines were being emitted during tool calls. **On a
stdio transport that can corrupt the JSON-RPC stream.** Silenced at the logger and asserted clean
(FR-008).

Worth recording because it is invisible until something downstream fails to parse.
