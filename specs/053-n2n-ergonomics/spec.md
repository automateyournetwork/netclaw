# Feature Specification: N2N Federation Ergonomics & Reliability

**Feature Branch**: `053-n2n-ergonomics`
**Created**: 2026-07-11
**Status**: Draft
**Input**: Harden the working NCFED protocol (spec 052) so it survives real-world
operation across independently-run claws without constant manual intervention.

## Overview

Spec 052 delivered NetClaw-to-NetClaw (N2N) federation — the NCFED protocol —
and it is **proven working end-to-end** on a live three-claw mesh (John AS65001,
Nick AS65007, Byrn AS65099): consent, capability exchange, and claw-to-claw
chat/skill invocation returning real data (Nick's CML lab list, Byrn's Nautobot
query). Getting there, however, exposed that the protocol *works* but the
*operational envelope* is fragile. Nearly every working session was preceded by
a failure caused by one of: a long remote operation dropping mid-flight, a dead
channel after a peer restart, an ngrok endpoint that moved on restart, a version
difference between claws, or a timeout mismatch swallowing a completed answer.

This feature hardens that envelope so federation **self-heals** and long tasks
**complete reliably**, without touching the proven core. Explicitly unchanged:
the NCFED wire framing, the mutual-consent trust model, default-deny
authorization, and the no-secrets inventory guard — all validated in 052 and
frozen here.

## Clarifications

### Session 2026-07-11

- Q: Should this feature change the NCFED wire framing, consent, or security
  model? → A: No. 053 is reliability/ergonomics only; the 052 core is frozen.
- Q: Are the internal-clutch (iN2N) model and installer topology flags in scope?
  → A: No — deferred to a separate future spec. 053 covers external federation
  (eN2N) reliability only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Long remote operations complete reliably (async delegation) (Priority: P1)

An operator asks their claw to have a peer perform a multi-minute operation —
e.g. "have Nick's claw recreate my 10-node/12-link CML lab." Today this fails:
the request is a single synchronous call that runs the entire build before
returning, so it exceeds timeouts and the long-lived channel is reset mid-build
("Connection lost"). With async delegation, submitting the task returns
immediately with a task id; the peer runs it in the background; the operator's
claw reports progress and delivers the result when it completes — no single
call long enough to be dropped.

**Why this priority**: This is the headline failure that blocked the flagship
demo (cloning a CML lab across the mesh). It is the single most valuable fix.

**Independent Test**: Delegate an operation that takes several minutes on a
peer; verify submit returns a task id in seconds, status is pollable, progress
is visible, and the final result is delivered intact even though the total time
far exceeds any single-call timeout or channel idle limit.

**Acceptance Scenarios**:

1. **Given** a federated peer with a granted long-running skill, **When** the
   operator delegates it, **Then** submission returns a task id within a few
   seconds and the operation continues on the peer regardless of channel resets.
2. **Given** a running delegated task, **When** the operator (or their claw)
   checks status, **Then** it reports a state (submitted/working/completed/
   failed) and progress detail, each check being a short call.
3. **Given** a delegated task completes, **When** the result is fetched, **Then**
   the full result is delivered even if total elapsed time exceeded prior
   single-call timeouts.
4. **Given** a delegated task is still running, **When** the operator cancels it,
   **Then** the peer stops work and reports cancelled.
5. **Given** the channel drops and reconnects mid-task, **When** the operator
   polls after reconnect, **Then** the task is still tracked and its result is
   retrievable (task state survives transient channel loss).

---

### User Story 2 - Federation self-heals across peer restarts (channel auto-reconnect) (Priority: P1)

A peer restarts its daemon (to deploy an update, or after a crash). Its NCFED
channel dies. Today the local side keeps a dead channel object and every
subsequent request fails ("chat/open timed out", "Connection lost") until an
operator manually re-dials. With auto-reconnect, the local side detects the dead
channel and re-establishes it automatically, re-federating from persisted
consent — with no operator action.

**Why this priority**: Peer restarts happened constantly during the 052 shakeout
and each one silently wedged federation until a human intervened.

**Independent Test**: Federate two claws, restart one peer's daemon, and verify
the other side detects the drop and re-establishes the channel automatically
within a bounded time, after which queries succeed — with no manual re-dial.

**Acceptance Scenarios**:

1. **Given** an established federation, **When** a peer restarts its daemon,
   **Then** the local side detects the dead channel (missed heartbeats or a
   failed send) rather than reusing it.
2. **Given** a detected dead channel, **When** reconnection is attempted, **Then**
   a fresh channel replaces the stale one and federation is restored from
   persisted consent without re-running the consent flow.
3. **Given** repeated reconnection failures, **When** the peer is unreachable,
   **Then** the local side backs off and surfaces a clear "peer unreachable"
   state rather than spinning silently or wedging.
4. **Given** a request arrives for a peer whose channel just died, **When** it is
   sent, **Then** the system reconnects first (or fails fast with a clear reason)
   rather than timing out on the dead channel.

---

### User Story 3 - Endpoints update themselves across restarts (auto-re-announce) (Priority: P2)

When an operator's daemon restarts, its public (ngrok) endpoint changes. Today
every federated peer must be told the new host:port by hand and manually re-dial
— this happened roughly five times in a single session. With auto-re-announce, a
restarted claw advertises its new endpoint to already-federated peers over the
still-up mesh session, and peers update and re-dial automatically.

**Why this priority**: Endpoint churn was the most frequent single cause of
manual toil; eliminating it removes most of the operational friction.

**Independent Test**: Federate two claws, restart one so its public endpoint
changes, and verify the peer learns the new endpoint and re-establishes the N2N
channel without any human exchanging host:port.

**Acceptance Scenarios**:

1. **Given** two federated claws, **When** one restarts with a new public
   endpoint, **Then** it announces the new endpoint to the peer over the existing
   mesh session.
2. **Given** a peer receives an endpoint update, **When** it processes it, **Then**
   it updates its record and re-dials the N2N channel to the new endpoint
   automatically.
3. **Given** the announcing side is the higher-AS (non-initiating) party, **When**
   it changes endpoint, **Then** the lower-AS side still re-initiates correctly to
   the new endpoint (the initiate/accept roles are preserved).

---

### User Story 4 - Claws on different builds interoperate (capability negotiation) (Priority: P2)

Federated operators run different OpenClaw builds. Today this breaks silently:
one peer's agent CLI accepts a flag another's does not; agent replies come back
in different shapes on different builds; timeouts differ. Each mismatch produced
a cryptic failure that took live debugging to trace. With negotiation, peers
exchange a lightweight capability/version descriptor and each side adapts to what
the other actually supports, and the responder probes its own local environment
rather than assuming.

**Why this priority**: Version drift caused several of the hardest-to-diagnose
failures; negotiation converts silent breakage into predictable, self-adapting
behavior.

**Independent Test**: Federate two claws simulating different builds (differing
agent-invocation options and reply shapes) and verify delegated chat/skill calls
succeed on both, with each side adapting to the other's advertised capabilities.

**Acceptance Scenarios**:

1. **Given** two claws on different builds, **When** they federate, **Then** each
   learns the other's protocol/capability version and adapts behavior accordingly.
2. **Given** a responder on a build whose agent interface differs, **When** it
   runs a delegated turn, **Then** it adapts to its own local interface (probing
   rather than assuming) and returns a valid result.
3. **Given** a reply arrives in a build-specific shape, **When** it is parsed,
   **Then** the clean answer is extracted regardless of which shape the peer used.
4. **Given** two claws whose versions are incompatible for a given capability,
   **When** that capability is used, **Then** the operator gets a clear
   "unsupported by peer version" message rather than a silent failure.

---

### User Story 5 - No silent failures from robustness gaps (Priority: P3)

Several defects were hot-patched live during the 052 shakeout: a client giving
up before the server finished (so a completed answer never arrived), reply
parsing broken by a trailing log line, partial HTTP body reads dropping request
fields, and bare errors surfacing as cryptic strings. This story consolidates
those into first-class, regression-tested requirements so they cannot silently
regress.

**Why this priority**: These are correctness cleanups over behavior already
working; important for durability but lower risk than P1/P2.

**Independent Test**: Exercise each hardened path (long operation vs. client
timeout, reply with trailing non-payload text, chunked/segmented request body,
malformed/missing fields) and verify correct results and clear typed errors,
covered by automated tests.

**Acceptance Scenarios**:

1. **Given** an operation that runs to the server's full allowed duration,
   **When** the client waits, **Then** the client outlasts the server so a
   completed answer is always delivered, never dropped by a premature client
   timeout.
2. **Given** a reply that includes non-payload trailing content, **When** it is
   parsed, **Then** the clean answer is still extracted.
3. **Given** a request whose body arrives in multiple network segments, **When**
   it is read, **Then** the full body is parsed and no fields are dropped.
4. **Given** a request missing a required field, **When** it is handled, **Then**
   a clear typed error names the missing field instead of a cryptic failure.

---

### User Story 6 - Operators can see and manage federation health easily (Priority: P3)

Operators today piece together federation health from multiple low-level calls,
and setting up a peer is a multi-step dance (add peer, consent, host/port,
enable chat, grant). This story provides a minimal connect/trust flow and clear
health visibility (channel up/down, last-seen, endpoint freshness, in-flight
tasks) in the HUD and via a single status surface, including progress for
long-running delegated tasks.

**Why this priority**: Quality-of-life over already-working capability; it makes
the system pleasant and observable but isn't required for correctness.

**Independent Test**: From a clean state, connect to and trust a peer through the
minimal flow, and confirm the HUD/status surface shows accurate live health and
task progress throughout.

**Acceptance Scenarios**:

1. **Given** a mesh peer, **When** the operator runs the minimal connect/trust
   flow, **Then** federation is established without manually chaining several
   separate commands.
2. **Given** active federations, **When** the operator views health, **Then**
   each peer shows channel state, last-seen, endpoint freshness, and any
   in-flight delegated tasks with progress.
3. **Given** a long delegated task, **When** it is running, **Then** the HUD and
   status surface show live progress, not just a spinner.

### Edge Cases

- **Both peers restart simultaneously** — both endpoints move; the mesh session
  itself must recover first, then endpoints re-announce and N2N re-dials.
- **Endpoint announcement while a task is running** — a task in flight when the
  channel reconnects must survive and remain retrievable (ties US1↔US2↔US3).
- **Reconnect storm** — a flapping peer must trigger bounded backoff, not a tight
  reconnect loop that burns budget or CPU.
- **Task result outlives the channel** — a delegated task completes while the
  channel is down; the result is held and delivered when the requester next polls.
- **Version too old to negotiate** — a pre-053 peer that doesn't understand
  negotiation must still federate at 052 behavior (graceful degrade), not break.
- **Endpoint update spoofing** — an endpoint re-announce must be trusted only over
  the authenticated mesh session for an already-federated identity, never from an
  unverified source (preserves the 052 trust model).
- **Duplicate/stale task ids** — polling a completed/expired/unknown task id
  returns a clear terminal status, not a hang.

## Requirements *(mandatory)*

### Functional Requirements

**Async Task Delegation (US1)**

- **FR-001**: Remote skill/long-operation delegation MUST be asynchronous:
  submission MUST return a task identifier promptly (target: within seconds)
  without waiting for the operation to complete.
- **FR-002**: The system MUST support querying a delegated task's status
  (at least: submitted, working, completed, failed, cancelled) and progress
  detail, each query being a short-lived call.
- **FR-003**: The system MUST support fetching a completed task's full result,
  and MUST allow cancelling an in-flight task.
- **FR-004**: Delegated task state and results MUST survive transient channel
  loss and reconnection for a bounded retention window, so an operator can
  retrieve results after a drop.
- **FR-005**: No individual call in the delegation lifecycle may require a
  duration long enough to be dropped by the transport's idle/reset behavior.

**Channel Health & Auto-Reconnect (US2)**

- **FR-006**: The system MUST detect a dead/stale N2N channel (via missed
  heartbeats and/or failed sends) rather than reusing it.
- **FR-007**: On detecting a dead channel to a still-consented peer, the system
  MUST automatically re-establish it and restore federation from persisted
  consent, with no operator action and no re-running of the consent flow.
- **FR-008**: Reconnection attempts MUST use bounded backoff and MUST surface a
  clear "peer unreachable" state after repeated failures rather than looping
  silently.
- **FR-009**: A request targeting a peer whose channel has died MUST trigger a
  reconnect (or fail fast with a clear reason), never hang on the dead channel.

**Endpoint Auto-Re-Announce (US3)**

- **FR-010**: When a claw's public endpoint changes (e.g. after restart), it MUST
  announce the new endpoint to already-federated peers over the existing
  authenticated mesh session.
- **FR-011**: A peer receiving an endpoint update for an already-federated
  identity MUST update its record and re-establish the N2N channel to the new
  endpoint automatically, preserving initiate/accept roles.
- **FR-012**: Endpoint updates MUST be accepted only over the authenticated mesh
  session for an already-federated identity (no new trust path introduced).

**Capability & Version Negotiation (US4)**

- **FR-013**: Peers MUST exchange a lightweight capability/version descriptor at
  federation time and on reconnect.
- **FR-014**: Each side MUST adapt its behavior to the peer's advertised
  capabilities/version; the responder MUST probe/adapt to its own local
  environment (agent interface, reply shape) rather than assume a fixed form.
- **FR-015**: Reply extraction MUST correctly yield the clean answer across the
  known differing agent-output shapes.
- **FR-016**: When a requested capability is unsupported by the peer's version,
  the operator MUST receive a clear "unsupported by peer" message, and a
  pre-053 peer MUST still federate at 052 behavior (graceful degrade).

**Robustness Hardening (US5)**

- **FR-017**: Client-side timeouts MUST outlast the corresponding server-side
  operation timeouts so a completed result is never dropped by a premature
  client give-up.
- **FR-018**: Reply parsing MUST tolerate trailing non-payload content after the
  structured response.
- **FR-019**: Request handling MUST read the complete request body regardless of
  network segmentation, and MUST return clear typed errors (naming the missing
  field/condition) rather than cryptic failures.

**Operator Ergonomics & Visibility (US6)**

- **FR-020**: The system MUST provide a minimal connect/trust flow that
  establishes federation without the operator chaining multiple separate
  low-level steps.
- **FR-021**: The system MUST surface per-peer federation health — channel state,
  last-seen, endpoint freshness, and in-flight delegated tasks with progress —
  in the HUD and via a single status surface.

**Non-Regression (applies throughout)**

- **FR-022**: This feature MUST NOT change the NCFED wire framing, the
  mutual-consent trust model, default-deny authorization, or the no-secrets
  inventory guard established and proven in spec 052.

### Key Entities

- **Delegated Task**: a unit of long-running remote work — id, state, progress,
  result, submitting peer, target capability, timestamps, retention window.
- **Channel Health Record**: per-peer liveness — last heartbeat, consecutive
  misses, reconnect attempts/backoff, current state (up / reconnecting /
  unreachable).
- **Peer Endpoint Record**: an already-federated peer's current public endpoint,
  updated by authenticated re-announce; carries freshness/last-updated.
- **Peer Capability Descriptor**: a peer's advertised protocol/capability version
  and the behavioral options needed to interoperate (reply shape, supported
  operations), exchanged at federation and reconnect.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A remote operation that takes several minutes on a peer (e.g.
  recreating a 10-node/12-link CML lab) completes and its result is delivered,
  with zero mid-operation drops, across at least 10 consecutive runs.
- **SC-002**: After a peer restarts its daemon, federation is automatically
  restored (channel re-established, queries succeed) within 60 seconds, with no
  operator action.
- **SC-003**: After an operator's public endpoint changes on restart, federated
  peers re-establish the N2N channel with zero manual host:port exchange, in
  100% of restarts during testing.
- **SC-004**: Two claws on deliberately different builds (differing agent options
  and reply shapes) complete delegated chat and skill calls successfully with no
  manual intervention.
- **SC-005**: A completed remote answer is never lost to a client/server timeout
  mismatch — 100% of completed operations reach the requesting operator.
- **SC-006**: An operator can establish federation with a new peer through the
  minimal connect/trust flow in under 2 minutes and see accurate live health
  afterward.
- **SC-007**: The three-claw mesh (AS 65001/65007/65099) runs for 24 hours
  including at least 3 peer restarts and endpoint changes, with federation
  self-healing each time and no manual re-dial.
- **SC-008**: All robustness fixes carry automated regression tests that fail
  against the pre-053 behavior and pass after.

## Assumptions

- Builds on the deployed, proven 052 implementation (branch history through
  `052-n2n-fixes`); the NCFED channel, consent DB, inventory exchange, grants,
  and audit are in place and unchanged.
- Endpoints are learned/carried by the existing mesh directory mechanism; the
  authenticated mesh (BGP) session between peers is the trusted carrier for
  endpoint re-announce and capability descriptors.
- Persisted consent (from 052) is authoritative across restarts, enabling
  auto-re-federation without re-consent.
- "Different builds" refers to differing OpenClaw agent CLI options and agent
  reply shapes observed live (e.g. session-flag naming, visible-text vs payload
  fields); negotiation targets these concrete differences, not arbitrary forks.
- Task retention window and backoff/heartbeat intervals will be set at plan time
  as operator-configurable defaults.
- Out of scope, deferred to a future spec: the iN2N internal-clutch model and
  installer topology flags (standalone vs clutch, gateway vs member claw),
  multi-hop federation, and extracting N2N into its own repository.
