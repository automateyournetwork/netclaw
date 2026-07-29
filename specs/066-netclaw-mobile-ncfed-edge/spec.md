# Feature Specification: NCFED Edge Node Foundation + Border-to-Phone Push Channel

**Feature Branch**: `066-netclaw-mobile-ncfed-edge`
**Created**: 2026-07-22
**Status**: Draft
**Input**: User description: "NetClaw Mobile + NCFED Edge Node: a full native-feeling mobile app (one Flutter codebase producing both iOS and Android) that turns a phone into a bidirectional NCFED client of a NetClaw Border, plus the protocol-level generalization needed to support it."

## Overview

This is **Direction 1 of 3** in the NetClaw Mobile initiative (split into three specs during
clarification, see below). This spec covers only: the protocol foundation that lets a phone
join a risk at all, and the **Border-to-phone push channel** — heartbeats, explicitly
important messages, and messages relayed from Slack/TUI/HUD, in text, voice, and image form.
Two sibling specs build on top of this foundation and are intentionally out of scope here:

- **Spec 067** (Direction 2 — phone-to-Border command channel): the phone submitting requests
  that trigger Border-side delegation to iN2N members.
- **Spec 068** (Direction 3 — advanced/capture): biometric (Face ID) gating, camera/video/
  microphone access, and Border-initiated capability requests (Border asks the phone to
  capture something).

Today, an iN2N "member" is assumed to be another NetClaw — a process running an agent
runtime with skills, MCP servers, and an LLM, joined to a risk behind a Border Claw. This
spec introduces a second kind of member: an **edge node** — a capability-bearing device with
no agent runtime and no LLM of its own — and gets the first edge node connected, enrolled,
and receiving pushed messages, as a real mobile app (NetClaw Mobile, one Flutter codebase for
iOS and Android, under `mobile/netclaw-mobile/`).

This builds on real, existing infrastructure rather than a parallel protocol: iN2N's
enrollment-token mechanism, feature 060's domain-verified certificate model, and the
already-symmetric channel dispatch layer (a Border already calls out to a connected member
today, not just replies to one). What's genuinely new in this spec: (1) a `node_type`
discriminator so a member can be `edge` (capability-only) rather than `agent`, (2) a
WebSocket transport binding for edge connections plus real member-side reconnect
supervision (mobile networks change IP, sleep, and get push-woken in ways a persistent raw
socket and today's thinner reconnect logic handle badly), and (3) an explicit-push messaging
mechanism from Slack/TUI/HUD/the agent to a connected phone, with platform push notifications
so it reaches the operator even when the app is backgrounded.

## Clarifications

### Session 2026-07-22 (first pass, protocol design)

- Q: Every member today must ship the full `BASE_FLOOR` skill set (heartbeat, self-status,
  audit-report skills/tools) so the Border can trust and monitor it — a skill-less phone
  can't satisfy this literally. Should edge nodes be exempt from `BASE_FLOOR` entirely, or
  must they implement a lightweight protocol-level equivalent? → A: A lightweight equivalent
  — an edge node MUST still provide heartbeat and self-status semantics (so the Border's
  trust/monitoring model isn't weakened for this node type), but via built-in NCFED
  methods every edge client implements natively, not by running OpenClaw skills.
- Q: Investigation found member-side reconnect-on-drop supervision (a member redialing the
  Border after a connection loss) is thinner today than assumed — it exists for eN2N peers,
  not clearly for iN2N members. Mobile networks will stress this far harder than a stable
  server member does. Should this feature build out proper member-side reconnect
  supervision as a general iN2N improvement, or rely on the mobile app's own client-side
  retry loop only? → A: Build proper member-side reconnect supervision as part of this
  feature — it's a real gap that would make every edge node flaky in practice, and it
  benefits existing server-based members too, not just mobile.

### Session 2026-07-22 (second pass, scope split)

- Q: Should the whole NetClaw Mobile initiative stay one spec, or split into three? → A:
  Three distinct specs, one per direction (this spec = Direction 1; 067 = Direction 2;
  068 = Direction 3), each independently planned/tasked/implemented, sharing the protocol
  foundation this spec establishes.
- Q: Should the phone verify the Border via feature 060's existing domain-verified public
  certificate (e.g. `netclaw.automateyournetwork.ca`), or an independent trust model? → A:
  Reuse feature 060 exactly, asymmetrically: the phone verifies the Border's domain-verified
  certificate (real public CA trust, works regardless of which ephemeral tunnel endpoint the
  Border is reachable at); the Border still pins the phone's self-generated key via TOFU,
  since a phone has no DNS domain of its own — the same asymmetric pattern feature 060
  already documents for a domain-less peer.
- Q: Is "messages of importance" pushed to the phone a full mirror of every Slack/TUI/HUD
  message, or an explicit "this is phone-worthy" designation? → A: Explicit push only — the
  agent's reasoning or the operator (via Slack/TUI/HUD) marks a specific message for phone
  delivery; routine channel chatter is never automatically mirrored.
- Q: Where does "Border asks the phone to capture something" (photo/location/etc., as
  opposed to the Border merely sending existing content to the phone) belong? → A: Spec 068,
  together with phone-initiated capture — both directions of capture share the same camera/
  mic/biometric machinery and should be built once, there. This spec (066) only covers the
  Border pushing content it already has; it never requests a new capture from the phone.
- Q: Should phone-originated requests (spec 067) be able to reach external federation
  (eN2N, other operators' Borders), or stay scoped to the operator's own risk? → A: No
  restriction — eN2N reachability from the phone is in scope for spec 067 from day one,
  under the same authorization/grant model every other request source already uses. (Recorded
  here because it was resolved in this session; the actual command-channel requirements live
  in spec 067, not this one.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enroll a phone into a risk by scanning a QR code (Priority: P1)

An operator opens NetClaw Mobile for the first time, taps "Scan Border QR Code," and points
the camera at a QR code their Border Claw is displaying. The phone verifies the Border's
domain-verified certificate, generates its own key material in the device's secure hardware,
completes enrollment, and the app shows the risk's topology with the phone itself marked as
the current device.

**Why this priority**: Nothing else in this feature — or in specs 067/068 — is reachable
without a phone that has successfully joined a risk. This is the front door for the entire
NetClaw Mobile initiative.

**Independent Test**: On a Border with no QR generator or edge-enrollment support yet
missing entirely, confirm enrollment is impossible; after this story ships, generate a QR
code from the Border, scan it from the app, and confirm the phone appears in the risk's
member list as an `edge` node with a pinned key — no plaintext token or key ever leaves the
device unencrypted, and the app refuses to complete enrollment if the Border's certificate
doesn't verify against public trust as the declared domain.

**Acceptance Scenarios**:

1. **Given** a Border operator running `netclaw risk add` (or equivalent) for a new edge
   member, **When** they choose to enroll via QR instead of pasting a token, **Then** the
   Border renders a QR code encoding a single-use enrollment token, the Border's endpoint,
   and its domain-verified certificate's identity (e.g. `netclaw.automateyournetwork.ca`).
2. **Given** the app scans that QR code, **When** it connects, **Then** it verifies the
   Border's certificate against public trust and confirms the certified name matches the
   domain encoded in the QR code before proceeding — refusing enrollment outright on any
   mismatch.
3. **Given** a verified Border, **When** enrollment completes, **Then** the phone's private
   key was generated in and never leaves the platform's secure hardware (iOS Secure Enclave /
   Android Keystore), and the Border has pinned the phone's public key via TOFU exactly as it
   pins any domain-less peer today.
4. **Given** the same enrollment token, **When** a second device attempts to scan and enroll
   with it, **Then** enrollment is refused (the token is single-use, consistent with existing
   member enrollment).
5. **Given** a successful enrollment, **When** the app finishes, **Then** it displays the
   risk's topology (Border + existing members) with the phone labeled as the current device.

---

### User Story 2 - The Border pushes an important message to the phone (Priority: P1)

An operator (or the agent's own reasoning) marks a message as worth surfacing on the phone —
an outage alert composed in the TUI, something said in Slack, or a heartbeat-driven health
note — and it reaches the connected phone as a new item in its message feed, in text, voice
(an audio clip), or image form. This is one-way: the Border already has content and pushes
it; it never asks the phone to go create new content (that's spec 068).

**Why this priority**: This is the entire value of Direction 1 — turning the phone into a
place the Border can actually reach the operator, not just a passive display the operator
has to remember to check.

**Independent Test**: With a phone enrolled and connected, explicitly push a text message,
then a voice clip, then an image from a non-mobile surface (CLI, Slack, or the TUI) and
confirm each arrives in the phone's message feed intact; separately, send a normal
(non-designated) message through the same surface and confirm it does *not* appear on the
phone.

**Acceptance Scenarios**:

1. **Given** a connected, enrolled phone, **When** an operator or the agent explicitly
   designates a message for phone delivery (via Slack, TUI, HUD, or agent reasoning), **Then**
   the message reaches the phone's feed over its existing connection.
2. **Given** the same setup, **When** a message is sent through any of those surfaces without
   being explicitly designated for phone delivery, **Then** it does NOT appear on the phone —
   there is no blanket mirroring of channel traffic.
3. **Given** a pushed message that is text, voice (audio), or an image, **When** it arrives,
   **Then** the phone renders it appropriately for its type (readable text, playable audio,
   viewable image).
4. **Given** a phone that is not currently connected, **When** a message is pushed, **Then**
   it is queued/delivered via the push-notification path (Story 3) rather than silently lost.
5. **Given** the Border's own heartbeat/health signal for a connected edge node, **When** it
   is evaluated, **Then** the Border can distinguish a healthy, connected phone from a
   disconnected or unhealthy one — the same trust/monitoring guarantee `BASE_FLOOR` gives
   every other member, via the edge node's built-in heartbeat method instead of a skill.

---

### User Story 3 - Reach the operator even when the app is backgrounded (Priority: P1)

The phone is asleep or the app isn't open when the Border pushes a message or the connection
needs re-establishing after a network change; the operator still gets a platform push
notification and, on tap, lands in the app with the relevant content already loaded, and the
underlying NCFED connection recovers automatically without any manual reconnect step.

**Why this priority**: A push channel that only works while the app happens to be open in the
foreground isn't a push channel — this is what makes Story 2 actually reliable in practice.

**Independent Test**: Background the app (or lock the phone), push a message from a
non-mobile surface, and confirm a platform notification (APNs/FCM) arrives and opens directly
to that message; separately, toggle airplane mode on and off and confirm the connection
re-establishes on its own with exponential backoff, without the operator re-enrolling.

**Acceptance Scenarios**:

1. **Given** the app is backgrounded, **When** the Border pushes a message, **Then** a
   platform push notification is delivered and opens the app directly to that message on tap.
2. **Given** a dropped connection (network change, backgrounding, brief outage), **When**
   connectivity returns, **Then** the app reconnects automatically using backoff-based
   member-side reconnect supervision, with no operator action required.
3. **Given** repeated rapid connect/disconnect cycles (e.g. walking in and out of WiFi range),
   **When** this happens, **Then** the reconnect supervisor does not spam the Border with
   connection attempts — backoff increases on repeated failure, consistent with the existing
   eN2N reconnect pattern this feature extends to iN2N members.

### Edge Cases

- What happens if the phone loses connectivity mid-push (message sent while phone is
  transitioning networks)? The message is not lost — it is delivered via the push-notification
  path and/or replayed once the connection re-establishes, not silently dropped.
- What happens if two of the operator's own devices (phone + tablet, or two colleagues' phones)
  are enrolled in the same risk simultaneously? Each is its own member with its own identity
  and pinned key; nothing in this feature limits a risk to one edge node, and a pushed message
  can reach one, several, or all connected edge nodes depending on how it was targeted.
- What happens when a phone is lost or stolen? The operator (or Border admin) removes/quarantines
  that member exactly as any other compromised member is removed today, revoking its pinned
  key; this feature does not add a remote-wipe capability for the app's own local data — that's
  a mobile-platform concern outside NCFED's reach.
- What happens if the Border's domain-verified certificate itself expires or rotates? The
  phone's verification behaves exactly as any other client verifying that certificate would —
  no edge-node-specific handling is introduced; feature 060's rotation/overlap guarantees apply
  unchanged.
- What happens if an operator designates a message for phone delivery but no edge node is
  currently enrolled at all? The designation is a no-op — there is no error, since there is
  nothing to notify; this is not a failure condition.
- What happens if the app itself is compromised or a phone is jailbroken/rooted in a way that
  defeats platform secure-hardware guarantees? Out of scope for this feature to detect —
  NCFED's existing default-deny/audit model is the backstop (a compromised member's blast
  radius is bounded by its own grants, same as any other member).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a `node_type` on every member — `agent` (today's
  default, an existing NetClaw), `service`, or `edge` (a capability-bearing device with no
  agent runtime) — advertised during enrollment and visible in the risk's member listing.
- **FR-002**: An edge node MUST be able to join a risk via a single-use enrollment token
  delivered as a scannable QR code (in addition to the existing plain-text token flow, which
  MUST continue to work for non-edge members).
- **FR-003**: Enrollment MUST verify identity in both directions, by two different
  mechanisms: the edge node MUST verify the Border's public, domain-verified certificate
  (feature 060) against the domain encoded in the QR code before proceeding; the Border's
  verification of the edge node is the edge node's proof of possessing the single-use
  enrollment token also encoded in that same QR code (a token that only exists because it
  was displayed on the Border's own screen) — this token-possession check is the actual
  trust decision, not a bare unauthenticated first-connect. Only after that initial verified
  exchange does the Border pin the edge node's key via TOFU, so that key (not just the
  now-spent token) is what protects every subsequent connection.
- **FR-004**: An edge node's private key material MUST be generated on-device using the
  platform's secure hardware (iOS Secure Enclave / Android Keystore equivalent) and MUST
  NOT be exportable or written to disk in plaintext.
- **FR-005**: An edge node MUST NOT satisfy `BASE_FLOOR` by running OpenClaw skills (it has no
  agent runtime); it MUST instead provide the equivalent heartbeat and self-status semantics
  via built-in NCFED methods every edge client implements natively, so the Border's
  trust/monitoring model is not weakened for this node type.
- **FR-006**: The connection between an edge node and its Border MUST be established over
  WebSocket-over-TLS, outbound-initiated by the edge node only (the Border never dials an
  edge node) — consistent with the existing iN2N direction-of-dial convention, just on a
  transport suited to intermittent mobile connectivity.
- **FR-007**: The system MUST implement member-side reconnect supervision for a dropped
  connection (exponential backoff, resuming automatically on network recovery), as a general
  iN2N capability that benefits any member, not an edge-node-only patch.
- **FR-008**: The system MUST provide a way for an operator (via Slack, TUI, or HUD) or the
  agent's own reasoning to explicitly designate a specific message for delivery to a
  connected edge node; messages not so designated MUST NOT be forwarded — there is no blanket
  mirroring of channel traffic.
- **FR-009**: A message designated for phone delivery MUST support at least three content
  forms: plain text, a voice/audio clip, and an image — delivered to and rendered
  appropriately by the connected edge node.
- **FR-010**: The Border-to-phone push described in FR-008/FR-009 MUST be a delivery of
  content the Border already has; it MUST NOT request the edge node to newly capture
  anything (photo, audio, location) — Border-initiated capture requests are explicitly
  out of scope for this spec (see spec 068).
- **FR-011**: NetClaw Mobile MUST support platform push notifications (APNs on iOS, FCM on
  Android) so a pushed message reaches the operator while the app is backgrounded or the
  device is asleep, not only while an active connection is open, and opens directly to the
  relevant content on tap.
- **FR-012**: An edge node MUST NOT receive BGP participation or eN2N mesh topology visibility
  of any kind; it MUST know only about its own Border, identical to how any iN2N member is
  scoped today.
- **FR-013**: Removing or quarantining an edge-node member MUST use the exact same mechanism
  already used for any other member (revoking its pinned key), with no edge-specific removal
  path required.
- **FR-014**: The mobile application (NetClaw Mobile) MUST be a single codebase producing both
  an iOS and an Android build, MUST contain no local LLM or agent-reasoning logic, and — for
  this spec's scope — MUST provide at minimum an enrollment flow and a message feed rendering
  pushed content; the Chat, Network, and Approvals surfaces are introduced by specs 067/068.

### Key Entities *(include if feature involves data)*

- **Edge Node**: A member (in the existing `member` table sense) whose `node_type` is `edge`
  — no agent runtime, no LLM, connects over WebSocket, authenticated asymmetrically (it
  verifies the Border's domain-verified cert; the Border pins its TOFU key). One row per
  enrolled device; a risk may have any number.
- **Pushed Message**: A Border-to-phone delivery of existing content (text, voice, or image),
  explicitly designated for phone delivery by an operator or the agent — never a request for
  the phone to create new content.
- **NetClaw Mobile App**: The Flutter (iOS + Android) client implementing the edge-node
  protocol client role, enrollment UX, and the message feed for this spec's scope. A thin
  renderer — holds no independent intelligence; specs 067/068 extend the same app.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can go from "Border displays a QR code" to "phone appears in the
  risk's topology as an enrolled edge node" in under two minutes, with zero manual token
  copy-pasting and zero successful enrollments against an unverified/mismatched Border
  certificate.
- **SC-002**: 100% of messages explicitly designated for phone delivery reach a connected
  phone's feed; 0% of non-designated channel traffic ever appears there.
- **SC-003**: After a simulated connectivity loss (e.g. airplane-mode toggle), the phone
  automatically reconnects and resumes normal message delivery without the operator
  re-enrolling or manually reconnecting.
- **SC-004**: A Border-pushed message reaches a backgrounded app via push notification and
  opens directly to that message on tap, 100% of the time in testing.
- **SC-005**: A lost/stolen phone's access can be fully revoked (pinned key removed, no
  further message delivery possible) using the exact same operator action already used to
  remove any other member.
- **SC-006**: The Border can distinguish a healthy, connected edge node from a disconnected
  one via heartbeat, with the same reliability the existing `BASE_FLOOR` heartbeat gives an
  `agent` member.

## Assumptions

- The operator has access to a Mac (a separate machine from wherever this repo's daemon-side
  work is developed, but the same git repository/branches) for building and testing the iOS
  side of the Flutter app; this spec's protocol/daemon work and the Android build are
  developable and testable without macOS, but iOS build/signing requires it.
- Push notification credentials (an Apple Developer account/APNs key, a Firebase project/FCM
  key) are operator-provided, following the same pattern this repo already uses for every
  other third-party credential (env-var configured, documented in `.env.example`) — obtaining
  those accounts is an operational prerequisite outside this feature's engineering scope.
- Feature 060's domain-verified certificate (`netclaw.automateyournetwork.ca`) is already
  operational for this operator's Border; this spec consumes it as-is and does not modify
  feature 060's ACME/rotation machinery.
- A risk may have zero, one, or many enrolled edge nodes; nothing in this feature caps the
  count or assumes exactly one "the operator's phone."
- The existing per-member `runtime_kind`/`transport_binding` columns and the risk-CA
  hub-attestation mechanism are reused as-is; this feature adds a `node_type` alongside them,
  not a parallel identity model.
- Remote wipe of the app's own local data on a lost device is explicitly out of scope — NCFED
  key revocation prevents further federation access, but does not reach into the device itself.
- Capability advertisement (the phone telling the Border what it can do — camera, location,
  biometric approval) is introduced in spec 068, not this spec; this spec's edge node has no
  invocable capabilities of its own beyond built-in heartbeat/self-status.

## Dependencies

- Features 056/057 (iN2N internal federation, production enforcement) — the enrollment-token
  mechanism, member table, and audit trail this feature extends rather than replaces.
- Feature 060 (claw certificate security) — the domain-verified certificate model this spec
  reuses asymmetrically for phone-verifies-Border trust.
- The existing channel dispatch layer (`channel.py`/`service.py`) — already bidirectional at
  the transport level; this feature adds a WebSocket binding and the reconnect supervisor, not
  a new dispatch model.
- Specs 067 (command channel) and 068 (biometrics/capture) both depend on this spec's
  enrollment and connection foundation; this spec depends on neither of them.
