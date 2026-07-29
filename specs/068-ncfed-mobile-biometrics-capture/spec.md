# Feature Specification: NCFED Mobile Biometrics and Capture

**Feature Branch**: `068-ncfed-mobile-biometrics-capture`
**Created**: 2026-07-22
**Status**: Draft
**Input**: User description: "NCFED Mobile Biometrics and Capture (Direction 3 of 3): advanced capability layer for NetClaw Mobile, building on spec 066's protocol foundation and spec 067's command channel, and depending on both directly."

## Overview

This is **Direction 3 of 3**, the final spec in the NetClaw Mobile initiative. Spec 066
establishes the connection; spec 067 lets the operator ask the Border things. This spec adds
the advanced capability layer that shares one underlying ingredient — device camera,
microphone, and platform biometric authentication — used in two related ways: gating
sensitive approvals with Face ID / Android biometrics, and capturing photos, video, or audio
in both directions (the operator proactively sending a capture, and the Border requesting one).

This is the first real implementation behind `notify_approval` — a hook that exists in the
code today but has never been wired to any delivery mechanism (no chat platform, no push,
nothing). The existing CLI/HTTP approval path (`n2n_approve`/`n2n_deny`) is untouched; the
phone becomes an additional fulfillment path, never a replacement.

Biometric authentication in this spec gates a *decision* (approve/deny), never the underlying
cryptographic identity spec 066 established — successfully authenticating with Face ID must
never provide a way to extract, export, or otherwise bypass the secure-hardware-held
enrollment key. Those are two separate security properties: the enrollment key proves *which
device* this is; biometrics prove *who is holding it right now*.

This spec depends on both 066 (connection, enrollment) and 067 (the request channel a capture
can be attached to) and does not introduce QR/barcode scanning of its own — 066 already owns
enrollment QR scanning, and 067 owns scanning a QR code or deep link on physical equipment to
trigger a device-status lookup. This spec also does not introduce any new image-understanding
component on the Border side (067 already established that the Border's existing reasoning
model handles interpreting whatever arrives).

## Clarifications

### Session 2026-07-22

- Q: The NCFED channel has a hard aggregate message cap (16 MB) — a video clip or a longer
  voice note can exceed that easily. Should captures travel over the same NCFED channel
  (capped tightly enough to always fit), or over a separate transfer path with no such limit?
  → A: Same channel — captures are capped (duration/resolution/bitrate) tightly enough to
  always fit under the existing message bound; no new transport is introduced. A capture that
  would exceed the cap is refused/truncated at capture time on the device, not attempted and
  failed after the fact.
- Q: Should the operator be able to opt out of specific Border-requested capture types (e.g.,
  disable Border-requested audio while allowing Border-requested photo), or is it
  all-or-nothing per device? → A: Per-type opt-out — the operator can disable specific
  capture types independently; a disabled type is simply not advertised in the edge node's
  inventory, so the Border cannot request it at all (not "requested and refused," but never
  offered as a possibility in the first place).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Approve or deny a change with Face ID (Priority: P1)

A change requiring human approval fires (an existing `requires_approval` grant), and instead
of the operator having to remember to check `n2n_approvals` or a CLI, it's pushed to their
enrolled phone as a prompt showing the proposed device, change, reason, requesting agent, and
risk. The operator approves or denies using Face ID / the Android equivalent; the biometric
authentication happens locally, and only the authenticated result reaches the Border.

**Why this priority**: This is the feature's signature moment — "AI proposes, a human
authorizes from their pocket, everything audited" — and the first real delivery mechanism
behind an approval hook that has existed, unused, since before this initiative began.

**Independent Test**: Configure a `requires_approval=true` grant, trigger an invocation
against it, confirm the pending approval reaches the enrolled phone as a prompt (not just
visible via CLI polling), approve it with a real or simulated biometric success, and confirm
the audit trail records the resolution method as biometric.

**Acceptance Scenarios**:

1. **Given** a pending approval and a connected, enrolled phone, **When** the approval is
   created, **Then** the phone is notified (foreground prompt if active, push notification
   per spec 066's delivery mechanism if backgrounded) without the operator having to poll.
2. **Given** the approval prompt on the phone, **When** the operator taps approve, **Then**
   the platform biometric prompt runs first, and the "approved" result is transmitted to the
   Border only after that authentication succeeds locally — never before.
3. **Given** a resolved approval via the phone, **When** the audit trail is inspected, **Then**
   the resolution method is recorded as biometric, alongside the same peer/target/timestamp
   fields every other approval resolution already records.
4. **Given** a failed or cancelled biometric prompt (wrong face, operator cancels, biometric
   hardware unavailable), **When** this happens, **Then** no result is sent to the Border at
   all — the approval remains pending, exactly as if the phone had never received it.
5. **Given** the same pending approval, **When** the operator instead resolves it via the
   existing CLI/HTTP path, **Then** that continues to work exactly as today — the phone
   prompt, if still pending, should reflect the approval as resolved rather than remaining
   actionable.

---

### User Story 2 - Send a photo, video, or voice note to the Border (Priority: P1)

Standing in front of a rack, a whiteboard, or a console showing an error, the operator takes
a photo or records a short video/voice note in the app and sends it — either attached to a
typed request ("what am I looking at?") or as a standalone capture with no text — and it
reaches the Border as part of a spec-067 request.

**Why this priority**: This is the rich-media half of "point, ask, operate" — turning the
phone's camera and microphone into real operational input, not just a chat client.

**Independent Test**: With an enrolled, connected phone, capture a photo and send it attached
to a text request; separately, send a bare photo with no text; confirm both reach the Border
and produce a response that reflects having seen the image.

**Acceptance Scenarios**:

1. **Given** a captured photo attached to a text request, **When** it is sent, **Then** the
   image reaches the Border as part of that request, using the same request/answer/attribution
   mechanism spec 067 already established.
2. **Given** a bare capture (photo, video, or voice note) with no accompanying text, **When**
   it is sent, **Then** it still reaches the Border as a valid request — the Border's
   reasoning model infers intent from the media alone.
3. **Given** the operator declines the OS-level camera or microphone permission prompt,
   **When** this happens, **Then** the capture attempt fails explicitly within the app — it
   never silently produces an empty attachment or appears to hang.
4. **Given** the operator cancels a capture in progress (backs out of the camera/recorder
   UI), **When** this happens, **Then** no partial or empty capture is sent — cancelling is a
   true no-op, not a failed send.

---

### User Story 3 - The Border asks the phone to capture something (Priority: P1)

While fulfilling a request, the Border determines it needs a photo, video clip, or the
phone's current state and requests that capture from the connected edge node — the phone's
native camera/mic UI activates, the operator captures what's asked for (or declines), and the
result flows back to the Border as a normal result, attributed to the phone exactly as any
other member-provided capability result would be.

**Why this priority**: This is the other bidirectional half of "point, ask, operate" and the
feature's most novel capability — the phone isn't just where the operator asks from, it's
something the Border can actively call on, symmetric with how it already delegates to any
other connected member.

**Independent Test**: Submit a request (via any source) that requires a phone-advertised
capture capability the enrolled phone provides; confirm the Border discovers and invokes it,
the phone's native capture UI fires, and the result (or an explicit decline) flows back to
the original requester.

**Acceptance Scenarios**:

1. **Given** an enrolled phone advertising a capture capability (e.g. photo capture) in its
   inventory, **When** a request needs it, **Then** the Border invokes it over the existing
   connection (no new outbound dial to the phone) and receives a result.
2. **Given** a Border-requested capture, **When** the operator declines the OS permission
   prompt or cancels the capture, **Then** the Border receives an explicit failure/decline —
   never a silent empty result or an indefinite wait.
3. **Given** a phone that is not currently connected, **When** the Border needs one of its
   capture capabilities, **Then** the request fails cleanly (capability unavailable) rather
   than hanging, consistent with how an unreachable member is handled elsewhere in this
   initiative.
4. **Given** a successful Border-requested capture, **When** the result reaches the original
   requester, **Then** it is attributed to the phone as its source, using the same
   attribution model spec 067 established for delegated/federated answers.
5. **Given** the operator has disabled a specific capture type (e.g., audio) in the app's
   settings, **When** the Border's inventory of the phone's capabilities is checked, **Then**
   that type does not appear at all — it is not offered as an invocable capability, so the
   Border cannot request it, rather than the request being made and refused.

### Edge Cases

- What happens if biometric authentication is not set up on the device at all (no Face ID
  enrolled, no fingerprint configured)? The platform's own fallback (device passcode/PIN)
  applies — this spec does not invent a separate fallback; approval is still gated by *some*
  local authentication, never bypassed entirely.
- What happens if the operator's face/fingerprint changes enough that biometric
  authentication starts failing (injury, aging, etc.)? The platform's own biometric
  re-enrollment/fallback flow applies; this is a device-OS concern, not something this
  feature manages.
- What happens to a capture (photo/video/audio) that fails to upload mid-transfer due to a
  dropped connection? It is retried once the connection re-establishes (per spec 066's
  reconnect supervisor) rather than silently lost; the operator sees it as pending, not sent.
- What happens if the Border requests a capture capability the phone does not actually
  advertise (a stale or mismatched inventory)? The request fails explicitly as
  "capability not available," not as a hang or a fabricated result.
- What happens if two approval prompts arrive on the phone at the same time? Each is tracked
  and resolvable independently; resolving one must not affect the other.
- What happens if the operator resolves an approval via the phone (biometric) and, in the
  same moment, someone else resolves it via CLI? The first resolution to land wins (matching
  today's existing approval-resolution behavior); the second attempt is told it's already
  resolved rather than double-applying the grant.
- What happens if the operator tries to record a video or voice note long enough that it
  would exceed the channel's message bound? The app enforces the duration/quality cap at
  capture time (e.g., stopping the recording or warning before it goes too long) — the
  operator never gets to "finish" a capture only to have it fail on send.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A pending approval (an existing `requires_approval` grant firing) MUST be
  deliverable to a connected, enrolled edge node as a prompt, using spec 066's existing push
  delivery mechanism (foreground and backgrounded/push-notification cases both covered).
- **FR-002**: Approving or denying via the phone MUST require the platform's biometric
  authentication (or its platform fallback, e.g. device passcode) to succeed locally before
  any result is transmitted to the Border; a failed, cancelled, or unavailable biometric
  attempt MUST leave the approval pending — not resolved, not denied by default.
- **FR-003**: Biometric authentication on the phone MUST gate the approval decision only; it
  MUST NOT provide any means to extract, export, or bypass the secure-hardware-held
  enrollment key spec 066 established — these are independent security properties.
- **FR-004**: The audit trail for an approval resolved via the phone MUST record the
  resolution method as biometric, distinct from and alongside the existing CLI/HTTP-oriented
  value(s), without altering the meaning or availability of the existing values or the
  existing CLI/HTTP approval path (`n2n_approve`/`n2n_deny`), which MUST continue to work
  unchanged.
- **FR-005**: The mobile app MUST support capturing a photo, a video clip, and a voice/audio
  recording, and sending any of these either attached to a typed request or as a standalone
  capture with no accompanying text.
- **FR-005a**: Video and audio captures MUST be constrained (duration, resolution, or bitrate)
  so that every capture fits within the existing NCFED channel's aggregate message bound; a
  capture that would exceed it MUST be refused or truncated at capture time on the device,
  never attempted and failed partway through transfer.
- **FR-006**: A phone-initiated capture MUST reach the Border as part of a request using the
  exact request/answer/attribution mechanism spec 067 already established — no parallel
  attachment path is introduced.
- **FR-007**: An edge node MUST be able to advertise capture-related capabilities (at minimum
  photo capture, video capture, audio recording) in its inventory, addressable by the Border
  exactly as any other member-provided capability is addressable.
- **FR-007a**: The operator MUST be able to independently disable specific Border-requested
  capture types (e.g., audio, without also disabling photo); a disabled type MUST NOT appear
  in the edge node's advertised inventory at all — the Border must have no way to even
  discover it as a possibility, not merely have a request for it refused.
- **FR-008**: The Border MUST be able to invoke an edge node's advertised capture capability
  over the existing connection (no new outbound dial to the phone), receiving either a
  successful capture result or an explicit failure/decline — never an indefinite wait or a
  silently empty result.
- **FR-009**: A Border-requested capture that the operator declines (OS permission refusal)
  or cancels (backs out of the capture UI) MUST surface as an explicit decline/failure to the
  Border, distinguishable from a successful capture.
- **FR-010**: A Border-requested capture's result, once it reaches the original requester,
  MUST be attributed to the phone as its source, using the same attribution model spec 067
  established for delegated and federated answers.
- **FR-011**: The mobile app MUST provide an Approvals screen (distinct from spec 067's Chat
  screen) presenting pending approvals with the proposed device, change, reason, requesting
  agent, and risk, and the biometric approve/deny action.

### Key Entities *(include if feature involves data)*

- **Biometric Approval Resolution**: An approval resolved via the phone, carrying the same
  fields any approval resolution already carries (peer, target, timestamp) plus a resolution
  method of biometric, distinct from the existing CLI/HTTP-oriented value(s).
- **Capture**: A photo, video, or audio artifact produced on the phone, either sent
  proactively (attached to or standing alone as a phone-initiated request) or produced in
  response to a Border-requested capture invocation — same artifact shape either way.
- **Capture Capability**: An advertised, invocable device-native tool (photo capture, video
  capture, audio recording) in an edge node's inventory — extends spec 066's capability
  advertisement concept with the actual entries this spec introduces. Each type is
  independently toggleable by the operator; a disabled type is omitted from the inventory
  entirely rather than advertised-but-refused.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of approvals resolved via the phone record biometric authentication as the
  resolution method in the audit trail, and the existing CLI/HTTP resolution path continues
  to work unchanged for every existing grant type.
- **SC-002**: 0% of failed, cancelled, or unavailable biometric attempts result in an approval
  being resolved (approved or denied) without a successful local authentication having
  occurred.
- **SC-003**: A phone-initiated capture (with or without accompanying text) reaches the Border
  and produces a response reflecting the captured content, 100% of the time in testing when
  the underlying connection is healthy.
- **SC-004**: A Border-requested capture reaches the phone and returns either a successful
  result or an explicit decline/failure — 0% of invocations silently hang.
- **SC-005**: No successful biometric authentication ever exposes, exports, or otherwise makes
  the secure-hardware-held enrollment key retrievable — verified as part of security testing,
  not merely assumed from platform documentation.
- **SC-006**: A declined OS-level camera/microphone permission, in either capture direction,
  produces an explicit failure state within the same interaction, never an indefinite spinner
  or a silently empty result.
- **SC-007**: 100% of captures sent over NCFED fit within the channel's existing aggregate
  message bound — 0% of captures fail partway through transfer due to exceeding it, because
  the cap is enforced at capture time, not discovered at send time.
- **SC-008**: A capture type the operator has disabled never appears in the Border's view of
  the phone's inventory — 0% of disabled types are discoverable or requestable, verified by
  inspecting the advertised inventory directly, not merely by observing a request failing.

## Assumptions

- Biometric authentication uses each platform's standard framework (iOS Face ID via
  LocalAuthentication, Android BiometricPrompt) and its built-in fallback behavior (device
  passcode/PIN when biometrics are unavailable or not enrolled) rather than a custom
  authentication scheme.
- Capture size/duration limits and compression are implementation details decided during
  planning; the governing constraint is fitting within the existing NCFED channel's aggregate
  message bound, not an independently-chosen policy — the exact duration/resolution numbers
  are a planning decision, not a behavioral requirement of this spec.
- Border-requested captures are authorized implicitly by the edge node's existing membership
  in the operator's own risk (the same trust level any other iN2N member's capability already
  has) — no additional per-capability grant is introduced beyond what spec 066's enrollment
  already establishes.
- This spec builds on the same Flutter codebase (`mobile/netclaw-mobile/`) specs 066 and 067
  establish, adding an Approvals screen and camera/video/audio capture UI rather than a
  separate app.
- NFC is out of scope for this spec and for the initiative's current three specs — it was
  never committed to by any of them. QR/barcode scanning itself is very much in scope for the
  initiative (066 uses it for enrollment; 067 uses it for device-status lookup); it is only
  out of scope *for this spec specifically*, since 068 is about capture and biometrics, not
  scanning.

## Dependencies

- Spec 066 (NCFED Edge Node Foundation + Push Channel) — enrollment, connection, the
  `notify_approval` hook this spec is the first real implementation behind, and the
  capability-advertisement concept this spec adds real entries to.
- Spec 067 (NCFED Mobile Command Channel) — the request/answer/attribution mechanism
  phone-initiated captures attach to.
- The existing `approval_request` table, `authorization.py` grant/audit model, and
  `n2n_approve`/`n2n_deny` CLI/HTTP path — reused as-is; this spec adds a delivery and
  resolution-method value, not a parallel approval system.
