# Feature Specification: NCFED Mobile Command Channel

**Feature Branch**: `067-ncfed-mobile-command-channel`
**Created**: 2026-07-22
**Status**: Draft
**Input**: User description: "NCFED Mobile Command Channel (Direction 2 of 3): the phone-to-Border request channel for NetClaw Mobile, building on spec 066's protocol foundation and depending on it directly."

## Overview

This is **Direction 2 of 3** in the NetClaw Mobile initiative. Spec 066 gets a phone enrolled
and connected to a Border, and lets the Border push content to the phone. This spec adds the
other direction: the operator asking the Border to do something, from the phone, exactly as
they would from Slack or the CLI today.

A phone-originated request is not a second-class request. Like Slack, CLI, and TUI, the phone
is one of the operator's own interfaces into their own risk — it inherits the operator's
existing local trust rather than needing its own per-device grant, and its requests may be
answered directly by the Border, delegated to an iN2N member within the operator's own risk
(a pyATS claw, a NetBox claw), or routed out over eN2N to a different operator's Border
entirely, subject to that external peer's own existing reachability grant exactly as any other
source's eN2N-crossing request already is. Nothing about arriving from a phone grants
elevated trust or imposes reduced trust.

This spec depends on 066 (an edge node must already be enrolled and connected) and does not
depend on 068 (biometrics/capture) — it covers text and voice requests only, with no camera,
no biometric gating, and no Border-initiated capability invocation.

## Clarifications

### Session 2026-07-22

- Q: Is a phone-originated request authorized as if the enrolled device were a peer/member
  (needing its own explicit grants), or as an extension of the operator's own existing trust
  (the same unchecked local access Slack/CLI/TUI already have)? → A: Operator-extension model
  — a phone-originated request for in-risk work inherits the operator's own local trust, the
  same as Slack/CLI/TUI; no per-device grant is needed for the operator's own enrolled phone
  to use their own risk. This does not change eN2N reachability (FR-004): reaching an
  external peer is still gated by that peer's own existing grant, exactly as it already is
  for a Slack- or CLI-originated request — that grant axis is about which external target is
  reachable at all, not about authenticating the internal requester.
- Q: If the operator has multiple enrolled devices, do they share one conversation with the
  Border, or does each device have its own independent history? → A: Independent per-device
  history — no cross-device sync in this spec; each enrolled edge node's conversation is its
  own, distinct from any other device's, including another of the operator's own devices.
- Q: Can an in-progress phone-originated request be cancelled from the phone? → A: Yes,
  reusing the existing task-cancellation mechanism as-is — no new cancel machinery is
  introduced.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask the Border a question from the phone (Priority: P1)

The operator types a request in the Chat screen — "check every core router for BGP
problems" — and the Border answers, using whatever it would normally use to answer the same
question from any other source.

**Why this priority**: This is the entire point of a command channel — without it, the phone
is still just a notification pane from spec 066, not a real interface into the risk.

**Independent Test**: With an enrolled, connected phone (per spec 066) and a Border capable
of answering directly (no delegation needed), submit a text request and confirm a real,
composed answer returns to the same conversation.

**Acceptance Scenarios**:

1. **Given** an enrolled, connected phone, **When** the operator submits a text request,
   **Then** it reaches the Border over the existing NCFED connection and the answer appears
   in the phone's conversation view.
2. **Given** a request that requires an authorization the operator does not hold, **When** it
   is submitted from the phone, **Then** it is refused exactly as the equivalent non-mobile
   request would be — no elevated trust for arriving from a phone.
3. **Given** the Chat screen's conversation history, **When** the operator scrolls back,
   **Then** prior requests and answers from this device are preserved across app restarts
   (not lost on backgrounding or relaunch).

---

### User Story 2 - The Border delegates a phone request to an iN2N member (Priority: P1)

The operator's question requires expertise only a specific member of their risk has — "why is
the pyATS claw reporting interface errors on Toronto-R1?" — and the Border delegates the
request to that member, using the exact same delegation mechanism it already uses for
Slack/CLI-originated requests, returning the composed result to the phone with clear
attribution of which member actually answered.

**Why this priority**: Most real operational value in a risk comes from its specialist
members, not the Border alone — a command channel that can't reach them is a toy.

**Independent Test**: From the phone, submit a request that only a specific iN2N member can
fulfill; confirm the Border delegates to that member (reusing the existing task-submission
mechanism) and the phone's answer clearly attributes the result to that member, not the
Border.

**Acceptance Scenarios**:

1. **Given** a phone request requiring a specific member's capability, **When** the Border
   delegates it, **Then** the delegation uses the same mechanism (task submission, status,
   result) any other delegation source already uses — no parallel request path is introduced.
2. **Given** a delegated request that takes longer than an immediate response, **When** the
   operator is waiting, **Then** the phone shows the request as in-progress rather than
   appearing to hang or fail silently.
3. **Given** a completed delegated answer, **When** it reaches the phone, **Then** the
   conversation clearly shows which member produced it, not just "the Border."
4. **Given** an in-progress delegated or federated request, **When** the operator cancels it
   from the phone, **Then** the request is cancelled using the existing task-cancellation
   mechanism and the conversation reflects it as cancelled, not as a failure or a lingering
   pending state.

---

### User Story 3 - The Border reaches an external claw on the operator's behalf (Priority: P2)

The operator's request needs something only a federated peer's risk can answer — "ask Byrn's
claw if their branch is having the same issue" — and the Border reaches out over eN2N to that
peer's Border, subject to the exact same per-peer authorization/grant/audit model any other
eN2N-crossing request already goes through, returning the answer to the phone attributed to
the external peer.

**Why this priority**: This is real, novel value (a phone reaching the whole federation, not
just one risk) but depends on User Stories 1-2 already working and on the operator actually
having federated peers configured — a smaller audience than the core in-risk case.

**Independent Test**: From the phone, submit a request that requires an eN2N-authorized peer
to answer; confirm it is refused if no grant exists (exactly as a non-mobile request would
be), and succeeds with correct peer attribution when a grant does exist.

**Acceptance Scenarios**:

1. **Given** a phone request that would require reaching an eN2N peer the operator has not
   authorized, **When** it is submitted, **Then** it is refused and audited exactly as the
   equivalent non-mobile eN2N-crossing request would be.
2. **Given** an authorized eN2N peer, **When** the phone's request requires that peer,
   **Then** the Border reaches out to it using the existing eN2N invocation path, and the
   phone's answer is attributed to that external peer, distinct from an in-risk member answer
   or a direct Border answer.

---

### User Story 4 - Ask a question by voice (Priority: P2)

Instead of typing, the operator records a short voice message in the app and sends it; it
reaches the Border and is treated as a normal request, following the same
answer/delegation/attribution behavior as Stories 1-3.

**Why this priority**: A real convenience improvement for hands-busy field scenarios, but not
architecturally novel — it's the same command channel with a different input method, so it
naturally follows once text requests work.

**Independent Test**: Record and send a voice message that would trigger delegation if typed;
confirm the resulting answer and attribution behave identically to the text-request case.

**Acceptance Scenarios**:

1. **Given** a recorded voice message, **When** it is sent, **Then** it reaches the Border as
   part of a request exactly like a typed message — whether transcription happens on-device
   or server-side is not observable to the operator as a behavioral difference.
2. **Given** a voice request that requires delegation or eN2N routing, **When** it is
   answered, **Then** the same attribution guarantees from Stories 2-3 apply unchanged.

---

### User Story 5 - Scan equipment to jump straight to its status (Priority: P2)

Physical equipment carries a QR code (or the operator opens a `netclaw://device/<id>` link
from anywhere else it's been shared). Scanning or opening it sends a device-status request
to the Border immediately, without the operator typing anything, and the answer appears in
the conversation exactly as any other request's would.

**Why this priority**: A genuinely convenient shortcut for field work ("point at the switch,
get its status") called out explicitly in the original vision for this initiative — but it's
a shortcut for submitting a request, not a new request mechanism, so it naturally sits on top
of Stories 1-2 rather than being foundational to them.

**Independent Test**: Generate a QR code (or deep link) encoding a known device identifier;
scan/open it from the app and confirm a device-status request is submitted automatically and
answered in the conversation, with no typing required.

**Acceptance Scenarios**:

1. **Given** a QR code or deep link encoding a known device identifier, **When** it is
   scanned or opened, **Then** the app submits a device-status request for that identifier to
   the Border automatically — no manual typing required.
2. **Given** that request, **When** it is answered, **Then** it behaves exactly like any other
   phone-originated request from Stories 1-3 — it may be answered directly, delegated to an
   in-risk member, or routed over eN2N, with the same attribution guarantees (FR-005).
3. **Given** a QR code or deep link encoding a device identifier the Border does not
   recognize, **When** it is scanned/opened, **Then** the resulting request fails explicitly
   ("unknown device") rather than silently doing nothing or crashing the app.

### Edge Cases

- What happens if the phone submits a request while its connection is mid-reconnect (per
  spec 066's reconnect supervisor)? The request queues locally and sends once the connection
  re-establishes, or fails explicitly with a clear "not connected" state — it never appears to
  succeed while actually undelivered.
- What happens if two requests are submitted from the phone before the first one's answer
  returns? Both are tracked independently in the conversation view; an answer is never
  misattributed to the wrong request.
- What happens if a delegated member becomes unreachable mid-request? The phone receives the
  same failure the Border itself would receive from that member — not a silent hang.
- What happens if an eN2N peer required by a request is unreachable or has revoked the grant
  since it was last used? The request is refused/fails with the same reason a non-mobile
  request would surface, and the failure is audited the same way.
- What happens to in-flight requests if the app is killed (not just backgrounded)? On next
  launch, the conversation history (already-completed requests/answers) is intact; a request
  that was in-flight at kill time is not silently resurrected as if still pending — the
  operator can resubmit if needed.
- What happens if the operator submits a request the exact same wording of which was already
  answered earlier in the conversation? It is treated as a new, independent request — no
  caching/reuse of a prior answer is assumed.
- What happens if a QR code or deep link is scanned/opened while the phone is disconnected?
  It behaves like any other request submitted while disconnected (see the reconnect-related
  edge case above) — queued or explicitly failed, never silently dropped.
- What happens if the operator has two enrolled devices and submits related requests from
  both? Each device's conversation is independent — an answer on one device's history never
  appears on the other's, and there is no expectation that either device is aware of the
  other's in-flight or completed requests.
- What happens if the operator cancels a request that completes (answer arrives) at almost
  the same moment the cancel is sent? Whichever reaches the Border first wins — either the
  request is cancelled before completing, or it completes and the cancel is a no-op on an
  already-finished request; the phone never shows both a cancelled state and a completed
  answer for the same request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An enrolled, connected edge node MUST be able to submit a request to its Border
  over its existing NCFED connection (established per spec 066), with no new connection or
  enrollment step required.
- **FR-002**: A phone-originated request for in-risk work MUST inherit the operator's own
  existing local trust — the same unchecked access Slack/CLI/TUI already have as the
  operator's own interfaces — rather than being treated as a separate peer/member requiring
  its own explicit per-device grant; enrolling a new phone MUST NOT require re-granting
  in-risk capabilities from scratch before it is useful.
- **FR-003**: The Border MUST be able to delegate a phone-originated request to an iN2N member
  within the operator's own risk, reusing the existing delegation/task mechanism as-is (no
  parallel request path introduced for edge-originated requests).
- **FR-004**: The Border MUST be able to route a phone-originated request to an external eN2N
  peer, subject to the exact same per-peer authorization/grant/audit model any other
  eN2N-crossing request already goes through — this MUST NOT be restricted or specially
  gated merely because the request originated from a phone.
- **FR-005**: Every answer returned to the phone MUST carry clear attribution of its actual
  source — the Border directly, a specific in-risk member, or a specific external eN2N peer —
  so the operator is never left assuming the Border itself produced an answer it merely
  relayed.
- **FR-006**: The mobile app MUST provide a Chat-style screen showing request/answer history,
  including in-progress state for requests still awaiting a delegated or federated answer.
- **FR-007**: Conversation history MUST be independent per enrolled edge node, with no
  cross-device sync — and MUST persist, on each device, across app backgrounding and restart;
  it MUST NOT be lost merely because the app was closed or the phone rebooted.
- **FR-008**: The mobile app MUST support recording and sending a voice message as a request;
  the request MUST reach the Border and receive the same answer/delegation/attribution
  behavior as a typed request, regardless of whether transcription happens on-device or
  server-side.
- **FR-009**: A request submitted from the phone MUST NOT be automatically mirrored into any
  other channel (Slack, TUI, HUD) — consistent with spec 066's explicit-push-only philosophy
  for the reverse direction; if the operator wants a request visible elsewhere, that is a
  separate, explicit action outside this spec's scope.
- **FR-010**: A request that fails (unauthorized, member unreachable, peer unreachable/
  ungranted) MUST surface an explicit failure to the phone — no request may silently hang
  indefinitely.
- **FR-012**: An in-progress phone-originated request (delegated or eN2N-routed) MUST be
  cancellable from the phone, reusing the existing task-cancellation mechanism as-is; a
  cancelled request MUST be reflected in the conversation as cancelled, distinct from a
  failure or a still-pending state.
- **FR-011**: The mobile app MUST support scanning a QR code or opening a device deep link
  (e.g. `netclaw://device/<id>`) that automatically submits a device-status request for that
  identifier, with no manual typing required; an unrecognized identifier MUST fail explicitly
  ("unknown device") rather than silently doing nothing.

### Key Entities *(include if feature involves data)*

- **Phone-Originated Request**: A request submitted by an operator from an enrolled edge node,
  authorized identically to any other request source, tracked independently in the phone's
  conversation view from submission through to answer or explicit failure.
- **Answer Attribution**: Metadata on a returned answer identifying its actual source (Border,
  specific in-risk member, or specific external eN2N peer) — always present, never ambiguous
  between "the Border answered" and "the Border relayed someone else's answer."
- **Device Deep Link**: A QR code or `netclaw://device/<id>`-style link encoding a device
  identifier, resolved into an automatically-submitted device-status request — a shortcut for
  request submission, not a new request type or a separate mechanism.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A text request submitted from an enrolled phone receives a correctly attributed
  answer whether it was answered directly by the Border, delegated to an in-risk member, or
  routed to an external eN2N peer — 100% of the time in testing, with 0% misattribution.
- **SC-002**: An unauthorized phone-originated request (missing grant, in-risk or eN2N) is
  refused and audited 100% of the time, with no observable difference in enforcement compared
  to the equivalent non-mobile request.
- **SC-003**: A voice-recorded request produces the same answer a text request with equivalent
  wording would, in blind comparison testing.
- **SC-004**: Conversation history survives an app restart and a phone reboot with 0% loss of
  previously completed requests/answers.
- **SC-005**: No phone-originated request is ever left in an indefinite pending state without
  either an answer or an explicit failure reaching the operator within the same timeout budget
  the equivalent non-mobile request already has.
- **SC-006**: Scanning a device QR code or opening a device deep link produces an answered
  (or explicitly failed) device-status request with zero manual typing, 100% of the time in
  testing.

## Assumptions

- A device deep link (`netclaw://device/<id>`) resolves against identifiers the Border
  already knows from its existing source-of-truth integrations (e.g. NetBox, inventory);
  this spec does not introduce a new device-identity registry of its own.
- Answers return to the phone as a complete, staged response (reusing the existing
  task-status/result polling shape already used for delegated tasks) rather than a live
  token-by-token stream; streaming is a reasonable future enhancement but not required here.
- Voice transcription (on-device vs. server-side) is an implementation choice made during
  planning, not a behavioral requirement — the operator experience is identical either way.
- The existing per-peer rate-limit and daily-budget model (feature 053) applies to
  edge-node-originated requests unchanged; no edge-specific quota is introduced.
- This spec builds on the same Flutter codebase (`mobile/netclaw-mobile/`) spec 066
  establishes, adding a Chat screen and voice-recording input rather than a separate app.
- Camera/photo/video capture, biometric-gated approvals, and Border-initiated capability
  requests are explicitly out of scope here and covered by spec 068.

## Dependencies

- Spec 066 (NCFED Edge Node Foundation + Push Channel) — the enrollment, connection, and
  `node_type=edge` model this spec's request channel runs over; this spec cannot be built or
  tested without an already-enrolled, connected edge node.
- The existing iN2N delegation mechanism (`n2n/tasks/submit` and related status/result
  methods) — reused as-is for in-risk delegation.
- The existing eN2N peer-invocation and authorization/grant/audit model — reused as-is for
  external federation reachability from the phone.
