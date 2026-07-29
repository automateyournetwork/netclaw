# Feature Specification: Apple Watch Companion App for NetClaw Mobile

**Feature Branch**: `072-apple-watch-companion`
**Created**: 2026-07-27
**Status**: Draft
**Input**: User description: "Apple Watch companion app for NetClaw Mobile. Native watchOS app added to the existing iOS Xcode project (Flutter has no watchOS support), relaying everything through the paired, already-enrolled iPhone app over WatchConnectivity rather than connecting to the Border independently. Scope: Approvals (approve/deny from the wrist, with watch-appropriate on-device confirmation replacing Face ID/Touch ID), Feed (read-only scrollable view of pushed messages), and Quick Voice Ask (dictate a question, see the answer). Enrollment, capture, and Settings remain iPhone-only."

## Clarifications

### Session 2026-07-27

- Q: FR-003/FR-004 — what exactly should the watch require before resolving an approval, given it has no Face ID/Touch ID sensor? → A: An explicit device-passcode re-check on every single approve/deny action (not just relying on the watch already being unlocked/on-wrist) — closest match to the phone's "confirm this specific action" behavior, even though the modality is passcode rather than biometric.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Approve or deny a pending request from the wrist (Priority: P1)

An operator wearing their Apple Watch feels it tap with a pending approval the Border needs a decision on (e.g., a risky configuration change). Without taking out their phone, they glance at the watch, see who/what is asking, confirm their identity with their watch's passcode, and approve or deny it.

**Why this priority**: This is the entire reason a watch companion is worth building — approvals are exactly the kind of fast, glanceable, "I don't want to dig my phone out" interaction a watch exists for. Every other capability is secondary to this one.

**Independent Test**: With the phone reachable and a pending approval already pushed to it, open the watch app's Approvals view, resolve the approval, and confirm the same outcome (approved/denied) is visible on the phone and recorded by the Border — without ever touching the phone.

**Acceptance Scenarios**:

1. **Given** the Border has pushed a pending approval to the enrolled phone, **When** the operator opens the watch app, **Then** the same approval (requester, target, reason) appears on the watch.
2. **Given** a pending approval is shown on the watch, **When** the operator chooses to approve it, **Then** the watch requires an on-device confirmation step (equivalent in spirit to the phone's Face ID/Touch ID gate, using whatever confirmation the watch itself supports) before the decision is sent.
3. **Given** the operator successfully confirms on the watch, **When** the approval is resolved, **Then** the Border and the phone both reflect the decision, and the record of how it was confirmed accurately shows it came from the watch via passcode-style confirmation — never mislabeled as a biometric confirmation.
4. **Given** the operator cancels or fails the on-device confirmation, **When** they back out, **Then** the approval remains pending and unresolved — no decision is sent.
5. **Given** the same approval is resolved from the phone (or another channel) while still showing as pending on the watch, **When** the watch next checks in, **Then** the watch no longer offers to act on that approval.

---

### User Story 2 - Read pushed messages without unlocking the phone (Priority: P2)

An operator's Border pushes a status update while they're away from their desk. They glance at their watch's Feed view and read it — no need to find and unlock the phone.

**Why this priority**: Valuable and genuinely watch-native (glanceable, read-only), but less urgent than Approvals since a missed Feed message has no time-sensitive consequence the way an unresolved approval might.

**Independent Test**: With one or more messages already pushed to and stored on the phone, open the watch app's Feed view and confirm the same messages appear, scrollable, without any action needed on the phone.

**Acceptance Scenarios**:

1. **Given** the Border has pushed a text message to the enrolled phone, **When** the operator opens the watch's Feed view, **Then** the message text and who/what sent it are visible on the watch.
2. **Given** the Border has pushed an image or a voice message, **When** shown on the watch, **Then** the watch clearly indicates the message type even if it cannot fully render the media itself on the watch's small screen.
3. **Given** several messages exist, **When** the operator scrolls the watch's Feed view, **Then** they can move through the full history the phone already has, oldest to newest.

---

### User Story 3 - Ask a quick question by voice (Priority: P3)

An operator wants a fast answer to a simple question ("is R2 still flapping?") without typing on a phone. They raise their wrist, dictate the question to the watch, and see the answer appear once the Border responds.

**Why this priority**: Useful, but the least watch-native of the three — dictation accuracy and small-screen answer display are real constraints, and this duplicates iPhone chat functionality rather than offering something uniquely suited to the watch the way Approvals does.

**Independent Test**: With the phone reachable, dictate a question on the watch, confirm it is submitted through the phone exactly as a typed phone chat message would be, and confirm the resulting answer (or a clear failure) appears on the watch.

**Acceptance Scenarios**:

1. **Given** the phone is reachable, **When** the operator dictates a question on the watch and confirms it, **Then** the request is submitted to the Border through the phone and the watch shows a "waiting for an answer" state.
2. **Given** the Border returns an answer, **When** it arrives, **Then** the watch displays it, replacing the waiting state.
3. **Given** dictation produces no usable text (silence, cancelled, recognition failure), **When** the operator finishes, **Then** the watch clearly reports that nothing was heard and does not submit an empty request.
4. **Given** a submitted question fails or times out, **When** that happens, **Then** the watch shows a clear failure state (not an indefinite spinner).

---

### Edge Cases

- What happens when the watch app is opened but the paired iPhone is out of Bluetooth/WiFi range, powered off, or has the NetClaw Mobile app force-quit? Every capability (Approvals, Feed, Ask) must show an explicit "not connected to your phone" state rather than an empty list, a silent failure, or an indefinite spinner.
- What happens when the phone is reachable but the app on it has never been enrolled (fresh install, or revoked and returned to the enrollment gate)? The watch must show that there is nothing to relay to yet, distinctly from a pure connectivity failure, since the fix (enroll the phone) is different from the fix for "phone unreachable" (bring it back in range).
- What happens if the operator raises their wrist to approve something and their watch is currently locked (not on their wrist, or removed)? The on-device confirmation step must not be bypassable while the watch is in that state — resolving an approval must require the watch to actually be unlocked/on-wrist at confirmation time.
- What happens if two approvals arrive close together? Each must be independently resolvable without one action accidentally affecting the other.
- What happens to an in-flight "quick ask" if the operator lowers their wrist or the watch app is backgrounded before an answer arrives? The answer must still be recoverable when they check again (matching the phone's own "reconcile on reconnect" behavior), not lost.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The watch app MUST display pending Border-triggered approvals, sourced through the paired iPhone app — the watch has no independent connection to the Border.
- **FR-002**: The watch app MUST let the operator approve or deny a pending approval directly from the watch.
- **FR-003**: Before any approval is resolved from the watch, the watch app MUST require a fresh, explicit device-passcode confirmation for that specific action — re-checked on every approve/deny, not satisfied merely by the watch already being unlocked and on-wrist. A failed, cancelled, or skipped confirmation MUST NOT resolve the approval.
- **FR-004**: The record of how a watch-originated approval was confirmed MUST accurately reflect that it came from the watch's own confirmation mechanism — it MUST NOT be recorded or displayed as a biometric (Face ID/Touch ID) confirmation, since no such sensor exists on the watch.
- **FR-005**: An approval resolved through any other channel (phone, CLI, another session) while still shown as pending on the watch MUST stop being actionable on the watch once the watch next checks in — the operator must never be able to act on an already-resolved approval.
- **FR-006**: The watch app MUST display messages the Border has pushed (text, image, and voice) in a read-only, scrollable list, sourced through the paired iPhone app's already-stored message history.
- **FR-007**: For message types the watch cannot fully render on its screen (image, voice), the watch MUST still clearly indicate the message exists and what type it is, rather than omitting it or showing nothing.
- **FR-008**: The watch app MUST let the operator dictate a question and submit it to the Border through the phone, using the same request semantics as a typed question from the iPhone's chat feature.
- **FR-009**: The watch app MUST show a distinct "waiting for an answer" state for a submitted question until an answer, failure, or timeout is available, and MUST show the outcome once it is.
- **FR-010**: A dictation attempt that yields no usable text MUST be reported to the operator as such and MUST NOT result in an empty or meaningless request being submitted.
- **FR-011**: The watch app MUST rely entirely on the paired iPhone for connectivity to the Border — it MUST NOT implement its own device identity, its own enrollment flow, or its own direct network connection to the Border.
- **FR-012**: When the paired iPhone is unreachable, the NetClaw Mobile app on it is not currently enrolled, or the phone-side app is not available to relay, the watch app MUST show an explicit, distinguishable "not connected" state for every capability rather than an empty list or an indefinite loading state.
- **FR-013**: The watch app MUST NOT provide enrollment/QR scanning, photo/video capture, or capability/settings management — those remain exclusively on the iPhone app.
- **FR-014**: The watch app MUST be added as a new, separate native target within the existing iOS app project, since the existing Flutter-based phone app has no path to running on watchOS at all.

### Key Entities

- **Watch Approval**: The watch-side view of a pending approval — requester, target, reason, and (once resolved) the outcome and how it was confirmed. Mirrors the phone's existing pending-approval concept; not a separate record on the Border.
- **Watch Feed Message**: The watch-side view of a Border-pushed message — its type (text/image/voice), sender/designation, and timestamp. Mirrors the phone's existing stored message history; the watch does not maintain its own independent copy beyond what's needed to display the current list.
- **Watch Ask Turn**: The watch-side view of one submitted quick-ask question and its outcome (waiting / answered / failed) — a lighter-weight version of the phone's full conversation history, scoped to what's actionable on a watch-sized screen.
- **Relay Availability State**: Whether the paired phone is currently reachable and able to service watch requests — connected, phone unreachable, or phone not enrolled — surfaced consistently across all three capabilities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can resolve a pending approval entirely from the watch — no phone interaction required — from the moment they open the watch app to a confirmed decision, in under 15 seconds under normal conditions.
- **SC-002**: 100% of approvals resolved from the watch carry an accurate confirmation-method record; none are ever recorded or displayed as a biometric confirmation.
- **SC-003**: An operator can read the full text of a newly pushed text message on the watch without touching or unlocking the phone.
- **SC-004**: Every quick-ask question submitted from the watch reaches a visible terminal state (answered or failed) — no submission is left showing "waiting" indefinitely once the underlying request has actually finished or failed.
- **SC-005**: When the phone is unreachable or unenrolled, 100% of attempts to use any watch capability show an explicit, understandable "not connected" message within a few seconds — never a silent failure or a spinner that never resolves.
- **SC-006**: A reviewer checking the shipped watch app confirms zero reachable path to enrollment, capture, or settings functionality from the watch — those remain exclusively reachable from the phone.

## Assumptions

- A physical Apple Watch paired to the same iPhone used for this repo's existing iOS work is available for real-device verification, in addition to the watchOS Simulators already installed on this Mac; if the physical watch turns out not to be reachable as a build/run destination, Simulator-based verification is an acceptable fallback for this feature's initial delivery, with real-hardware verification tracked as a follow-up (mirroring how spec 071 handled the same class of environment uncertainty).
- The paired iPhone already has NetClaw Mobile installed and enrolled against a Border (the state left by specs 066/067/068/071) — this feature builds a companion surface on top of an already-working phone app, not a fresh install.
- watchOS's own device-passcode confirmation (the strongest device-owner-presence check the watch platform offers, since no biometric sensor exists) is an acceptable, deliberately-documented substitute for the phone's Face ID/Touch ID gate, scoped only to watch-originated approvals — this is a conscious, narrow deviation from the phone app's biometric-only requirement, not a general weakening of it.
- The phone app must be reachable (foreground, or backgrounded with an active companion session) for any watch capability to function; the watch is not expected to work when the phone app has been fully force-quit. Achieving resilience beyond what the platform's standard phone-watch background communication already provides is out of scope.
- The watch's quick-ask feature is single-turn from the watch's own perspective (one in-flight question and its outcome at a time) — it does not need to maintain or display a scrollable multi-question conversation history the way the phone's chat feature does, since the phone remains the full historical record.
- A watch-face complication (a glanceable widget outside the app itself) is a nice-to-have only if it falls out naturally once the three core capabilities work, and its absence does not block this feature's completion.
