# Feature Specification: Arista ANTA — structured network-state validation

**Feature Branch**: `098-arista-anta-validation`
**Created**: 2026-08-05
**Status**: Draft
**Roadmap**: R25 — created by [R24's triage](../097-open-territory-triage/TRIAGE.md), which selected
it as the one open-territory candidate worth building

## Overview

NetClaw has many ways to read network state and no way to **assert** on it.

| Existing capability | Answers |
|---|---|
| pyATS, multivendor CLI driver, `gnmi-mcp` | *what is the state* |
| `arista-cvp-mcp` | *what does the manager say* |
| `suzieq-mcp`, `zabbix-mcp` | *what was the state over time* |
| `nsm-mcp`, `analysis-mcp` | *what happened in this capture* |
| **nothing** | ***does the state match what it should be*** |

Today, answering "is this device healthy?" means reading output and judging it in prose. The judgement
lives in the conversation, is not repeatable, and leaves no artifact. Asked the same question twice,
NetClaw can reasonably give two different answers, and nobody can tell which was right.

ANTA (Arista Network Test Automation) is a declarative test framework: a catalogue of network-state
tests that produce structured **pass / fail / skipped** results against an explicit expectation.

**This feature adds the assertion layer.** Read-only — ANTA runs tests, it does not change devices.

## Clarifications

### Session 2026-08-05

- Q: How should ANTA's large test catalogue be exposed without breaching the manifest ceiling?
  → A: **Dispatcher plus discovery** (the 087 Catalyst Center pattern), decided in the R24 triage
  and carried here as FR-002. One tool per test is out of the question.
- Q: Where does ANTA run, given it wants to move `cryptography` from 46.0.5 to 50.0.0? → A: **A
  dedicated virtualenv**, the spec 083 pattern. See FR-011.
- Q: How should ANTA know which devices to test? → A: **Per-call device address, credentials from the
  environment.** No inventory file, no coupling to another server's inventory. See FR-013. An
  inventory concept may follow once there is real usage to judge it by; a third place devices are
  defined is the drift `docs/ADDING-AN-MCP.md` warns about, and is not worth adopting speculatively.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Is this device actually healthy? (Priority: P1)

An operator asks whether a switch is healthy. Today they get prose assembled from several `show`
commands. They want a verdict they can act on, with the failures named.

**Why this priority**: This is the capability gap. Everything else is refinement.

**Independent test**: Run the health tests against the lab vEOS node and confirm a structured
result naming each test, its verdict, and the reason for any failure.

**Acceptance scenarios**:

1. **Given** a reachable device, **when** the operator asks for a health check, **then** they receive
   per-test results with explicit `pass` / `fail` / `skipped` verdicts and a reason for each failure.
2. **Given** a device with a genuine fault, **when** tests run, **then** the failing test names the
   observed value **and** the expected value — not merely "failed".
3. **Given** a test that cannot run (unsupported platform, missing feature), **when** results are
   returned, **then** it is reported as `skipped` and **never** counted as a pass.

### User Story 2 — Did my change break anything? (Priority: P1)

An operator makes a change and wants to know whether previously-good state is still good.

**Independent test**: Run the same catalogue twice against the lab device and confirm the results are
comparable and stable between runs.

**Acceptance scenarios**:

1. **Given** a catalogue run before and after a change, **when** both complete, **then** the results
   are directly comparable — same test identity, same shape.
2. **Given** a device that has become unreachable since the earlier run, **when** tests run, **then**
   the outcome is reported as an **error**, never as a set of failures — unreachable is not
   "everything is broken".

### User Story 3 — What can I even test? (Priority: P2)

An operator does not know ANTA's catalogue and needs to find the relevant tests without reading
upstream documentation.

**Independent test**: Ask what tests exist for a topic (BGP, interfaces, software version) and get a
usable list with the inputs each requires.

**Acceptance scenarios**:

1. **Given** a topic, **when** the operator searches the catalogue, **then** they get matching tests
   with descriptions and required inputs.
2. **Given** a chosen test, **when** the operator asks how to run it, **then** they get its input
   schema without executing anything against a device.

### Edge Cases

- **A device is unreachable.** Reported as an error against that device. It MUST NOT be rendered as
  failing tests — that is the R15 box-vs-network distinction in a new place.
- **A test is skipped because the platform lacks the feature.** Reported as `skipped`, never folded
  into either pass or fail. A run of 40 tests where 30 skipped is not "75% healthy".
- **Zero tests match a selection.** Reported as "no tests selected", never as an all-pass result.
  An empty test run is not a healthy device.
- **A test needs inputs the operator did not supply** (expected BGP peers, expected version). Report
  what is required rather than inventing a default and silently testing the wrong thing.
- **Credentials are wrong.** Reported as an authentication failure against a reachable device —
  distinct from unreachable, and distinct from failing tests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** Run ANTA tests against one or more Arista EOS devices over eAPI and return structured
  per-test results: test name, device, verdict (`pass` / `fail` / `skipped` / `error`), and for
  failures the observed and expected values.
- **FR-002** The tool manifest MUST use **dispatcher plus discovery**, not one tool per test.
  Measured total MUST be **≤ 5,000 tokens**, and MUST be **counted, not estimated**.
- **FR-003** Read-only. The server MUST NOT be able to change device configuration. ANTA's own
  posture is test-only; NetClaw MUST NOT add any configuration path around it.
- **FR-004** `skipped` MUST be a first-class verdict, never merged into `pass` or `fail`. Any summary
  count MUST state skips separately.
- **FR-005** An unreachable device MUST yield an **error** for that device, and MUST NOT be
  convertible into test failures.
- **FR-006** An empty selection (no tests matched) MUST be reported as such and MUST NOT be
  presented as a passing run.
- **FR-007** A test requiring inputs the operator has not supplied MUST report the required inputs
  rather than substituting a default.
- **FR-008** Catalogue discovery MUST work **without contacting a device**, so an operator can
  explore what is testable before connecting to anything.
- **FR-009** Device credentials MUST come from the environment, never from tool arguments, and MUST
  NOT appear in results or logs.
- **FR-010** The boundary against existing servers MUST be explicit: `arista-cvp-mcp` is the
  management plane, the multivendor CLI driver and pyATS are the device-CLI plane, and this is the
  **validation** plane. It MUST NOT duplicate either.
- **FR-011** ANTA MUST run from a **dedicated virtualenv**. A system-interpreter install moves
  `cryptography` from 46.0.5 to 50.0.0, which four installed distributions depend on — including
  NetClaw's own federation TLS stack — none with an upper bound.
- **FR-012** Results MUST identify which device answered and when, so a verdict is attributable.
- **FR-013** Device targets are supplied **per call** as an address. There is no inventory file and
  no dependency on another server's inventory. Credentials come from the environment (FR-009), so a
  target is an address plus whatever the environment already holds.

### Key Entities

- **Test** — a catalogue entry: name, category, description, input schema, and the platforms it
  applies to.
- **Test result** — one test against one device: verdict, observed value, expected value, and for
  failures a human-readable reason.
- **Run** — a set of test results with a summary that counts passes, failures, skips and errors
  **separately**.
- **Device target** — an EOS device reachable over eAPI, identified by an **address supplied per
  call**, with credentials supplied by the environment. Not persisted, not inventoried.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** An operator gets a structured verdict for a device in a single request, with each
  failure naming observed and expected values.
- **SC-002** Manifest cost is **≤ 5,000 tokens**, counted with a token counter and recorded.
- **SC-003** Every result set distinguishes four outcomes — pass, fail, skipped, error — and no
  summary merges them.
- **SC-004** An unreachable device produces an error, verified live by pointing the tool at a dead
  address.
- **SC-005** Catalogue discovery returns useful results with **no device configured at all**.
- **SC-006** No credential appears in any tool output, verified by inspection.
- **SC-007** Verified live against a real EOS device — not a mock, not a fixture.
- **SC-008** Installing this feature does not change the version of any package another NetClaw
  component depends on, verified before and after.

## Assumptions

- **A live EOS device is available.** `clab-mandible-veos1` (vEOS-lab 4.36.1F) is running in
  containerlab with eAPI reachable at `172.20.20.4:443`. This was verified during R24's triage and
  again before this spec was written, and it is why R25 was selectable when the other 21 candidates
  were not.
- **eAPI is the transport.** ANTA supports it natively and the lab device now serves it. SSH-only
  operation is not pursued.
- **The catalogue is large and mostly Arista-specific.** ANTA targets EOS. This feature does not
  claim multivendor validation; that boundary is stated rather than implied.
- **`skipped` will be common.** A lab device does not run every feature the catalogue tests, which is
  precisely why FR-004 exists.

## Out of Scope

- **Writing or changing device configuration.** ANTA tests; it does not remediate.
- **Authoring new tests.** The upstream catalogue is used as shipped. A custom-test authoring surface
  is a separate feature with its own risks.
- **Multivendor validation.** ANTA is EOS-specific. Extending the assertion layer to other platforms
  is a future item, not this one.
- **CloudVision integration.** ANTA can source inventory from CVP; that overlaps `arista-cvp-mcp` and
  is deliberately left alone (FR-010).
- **Scheduled or continuous validation.** This provides on-demand validation. Turning it into a
  monitoring loop is a different feature.
