# Feature Specification: Push Notifications, Unread Tracking & Cross-Device Sync for NetClaw Mobile

**Feature Branch**: `073-push-notifications-sync`
**Created**: 2026-07-28
**Status**: Draft
**Input**: User description: "push notifications to watch and to phone FROM NetClaw - unread count etc like a normal app; also the CHAT HISTORY on the watch should make it into the chat history on the phone and on the chat history tab; we need a way to clear messages / responses / acknowledge them; distinguish unread messages; keeping the watch and phone in synch ... can the watch playback messages using voice or is it restricted to text?"

## Clarifications

### Session 2026-07-28

- Q: Should notification previews always show full content on a locked screen, or respect the device's own privacy setting? → A: Respect the OS's existing "Show Previews" setting (default: only when unlocked) — standard platform behavior, no app-side override in either direction.
- Q: During a burst of many arrivals in quick succession, should notifications stay one-per-item or collapse into a summary? → A: One notification per item, always — relies on the OS's own by-app notification stacking/grouping rather than any custom batching logic; every approval in particular always keeps its own individually-actionable banner.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get notified the moment the Border pushes something (Priority: P1)

An operator has NetClaw Mobile installed and paired with their Apple Watch, but isn't staring at either device. When the Border pushes a new Feed message, finishes answering a chat question, or raises a new approval request, the operator finds out about it the way they would with any other notification-worthy app — a banner appears, the app icon shows how many things are waiting for them, and (if they're wearing the watch and not actively looking at the phone) the same notification reaches their wrist automatically.

**Why this priority**: This is the headline ask ("like a normal app") and the one that makes the rest of the feature matter — without it, an operator still has to manually open the app and check each tab to discover anything happened.

**Independent Test**: With the app installed and running (foreground or backgrounded), trigger a Border-side Feed push, a completed chat answer, and a new approval in turn. Confirm a distinct, correctly-worded notification banner appears on the phone for each, the phone's home-screen icon badge count increases, and — with the watch paired and its screen not showing the NetClaw app — the same notification is mirrored to the watch.

**Acceptance Scenarios**:

1. **Given** the app is running in the background, **When** the Border pushes a new Feed message, **Then** a notification banner appears showing a one-line preview of the message content, and the app icon's badge count increases by one.
2. **Given** the app is running in the background, **When** a previously-submitted chat question receives its answer, **Then** a notification banner appears for that answer, and the app icon's badge count increases by one.
3. **Given** the app is running in the background, **When** the Border raises a new approval request, **Then** a notification banner appears with inline Approve/Deny buttons, and this notification does not affect the app icon's badge count.
4. **Given** the operator taps Approve or Deny directly on an approval notification banner, **When** the device prompts for on-device authentication (Face ID/passcode), **Then** the approval only resolves after that authentication succeeds — a dismissed or failed authentication leaves the approval untouched.
5. **Given** the operator taps a notification banner (Feed or Chat) instead of an action button, **When** the app opens, **Then** it lands directly on the specific message/answer that notification was about, not just the containing tab.
6. **Given** the watch is paired and its screen is not currently showing the NetClaw watch app, **When** any of the above notifications is generated on the phone, **Then** the same notification is mirrored to the watch (standard watchOS behavior — no separate watch-specific notification content is authored).
7. **Given** the phone app has been fully terminated (not just backgrounded) and no push credentials are configured for this deployment, **When** the Border pushes something, **Then** no notification is generated on either device — this is a known, documented limitation (see Assumptions), not a defect of this feature.

---

### User Story 2 - See at a glance what's new, and clear it when done (Priority: P2)

An operator opens the Feed or Chat tab (on phone or watch) and can immediately tell which items are new since they last dealt with them, without re-reading everything. Once they've dealt with something, they can mark it acknowledged (it stays in history, just no longer "new") or delete it outright — and whichever device they do this from, the other device and the app icon badge reflect it correctly the next time they look.

**Why this priority**: Directly extends User Story 1 — a badge count and a banner are only useful if the operator can also resolve/clear what they represent, and tell what's actually new versus already-seen.

**Independent Test**: Push several Feed messages and complete several chat questions. Confirm unread items are visually distinguished from read ones on both phone and watch. Acknowledge one item from the watch; confirm the phone's view of that item and the combined app badge count both reflect the change without any explicit "sync" step. Delete one item from the phone; confirm it disappears from the watch's next refresh too.

**Acceptance Scenarios**:

1. **Given** a new Feed message or chat answer has arrived and has not yet been acknowledged, **When** the operator views the Feed or Chat/History tab on either phone or watch, **Then** that item is visually distinguished from already-acknowledged items (e.g., a bold weight or unread marker).
2. **Given** an unacknowledged Feed message or chat answer, **When** the operator acknowledges it from either the phone or the watch, **Then** it immediately stops counting toward the app icon's badge and no longer shows as unread, but remains visible in the Feed/History list.
3. **Given** any Feed message or chat turn (acknowledged or not), **When** the operator deletes it from either the phone or the watch, **Then** it is permanently removed and disappears from both the phone's and the watch's views the next time each is refreshed.
4. **Given** the phone's app icon badge is showing a combined count, **When** the operator acknowledges items until none remain unacknowledged in Feed and Chat, **Then** the badge count reaches zero (never negative, never stuck above the true remaining count).
5. **Given** the watch cannot currently reach the phone, **When** the operator attempts to acknowledge or delete an item from the watch, **Then** the watch shows its existing "can't reach iPhone" state rather than silently failing or pretending the action succeeded.

---

### User Story 3 - A question asked from the watch shows up in chat history everywhere (Priority: P3)

An operator asks a quick question from their watch. Later, on their phone, they open the Chat tab expecting to see that question and its answer alongside everything else they've asked — today it's simply missing, because the watch's question never gets recorded into the phone's chat history at all.

**Why this priority**: A real, existing consistency defect (not a new capability) — narrower in scope than User Stories 1-2 but a correctness gap that undermines trust in the History tab the moment someone notices a question is missing.

**Independent Test**: Ask a question from the watch's Ask tab and wait for the answer. Confirm the same question-and-answer pair appears in the phone's Chat tab and in the watch's own History tab, indistinguishable in form from a question asked directly on the phone.

**Acceptance Scenarios**:

1. **Given** the operator submits a question from the watch, **When** the Border answers it, **Then** that question and answer appear in the phone's Chat/conversation history, in the same form as a phone-submitted question.
2. **Given** a question was submitted from the watch, **When** the operator views the watch's own History tab, **Then** that same question appears there too (it already should, but must be verified once it's actually being recorded rather than silently lost).

---

### User Story 4 - Have the watch read a message aloud (Priority: P4)

An operator whose hands are busy (working on hardware, standing at a rack) wants to hear a pushed message or a chat answer instead of squinting at a tiny screen. They tap an explicit "read aloud" control and the watch speaks it.

**Why this priority**: A genuine accessibility/hands-free convenience, but purely additive and lowest-risk — nothing else in this spec depends on it, and it was explicitly scoped to on-demand-only (never automatic) to avoid surprising or embarrassing the operator in a quiet room.

**Independent Test**: On the watch, open a Feed message or a completed chat answer and tap "read aloud." Confirm the watch speaks the text content. Confirm nothing is ever spoken without that explicit tap — not on push arrival, not on opening a tab.

**Acceptance Scenarios**:

1. **Given** a text Feed message or a completed chat answer is displayed on the watch, **When** the operator taps its "read aloud" control, **Then** the watch speaks the message/answer text aloud.
2. **Given** a Feed message whose content is a photo or voice recording (not text), **When** the operator taps "read aloud," **Then** the watch speaks a description of the content type (e.g., "photo message") rather than failing silently or reading nothing.
3. **Given** any new message, answer, or approval arrives, **When** it is delivered to the watch (via notification mirroring or the watch's own refresh), **Then** nothing is spoken automatically — "read aloud" only ever happens after an explicit tap.

---

### Edge Cases

- What happens if the operator has denied notification permission entirely? The app must continue to function normally for every other capability (Feed, Chat, Approvals, History) — only the banner/badge/mirroring behavior is unavailable, and this must be communicated clearly rather than silently doing nothing.
- What happens if an approval notification's Approve/Deny button is tapped after that approval has already been resolved from elsewhere (the app itself, or another device)? The action must fail gracefully with a clear "already resolved" outcome, never a crash or a confusing duplicate-resolution attempt.
- What happens if the same underlying event (e.g., a reconnect-triggered replay) could cause a duplicate notification for something already notified about? The operator must not see the same new-item notification twice for the same item.
- What happens to the badge count if a message is deleted while still unacknowledged? The badge count must decrease exactly as it would for an acknowledge — deleting an unread item must not leave it "stuck" contributing to the count forever.
- What happens if the operator acknowledges or deletes something from the watch while the phone is simultaneously showing that same item in its own list? The phone's view must reflect the change on its own next refresh (no crash, no stale duplicate, no silent overwrite of the watch's action).
- What happens when the phone app is fully terminated (see User Story 1's acceptance scenario 7) and the operator later reopens it? Any Feed pushes or chat answers that arrived while fully terminated and uncredentialed for remote push are simply not retroactively notified about — they appear in Feed/History as normal (already-existing) unread items once the app is running again, just without a banner for the time it was closed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The phone app MUST post a local notification when a new Feed message arrives while the app process is running (foreground or backgrounded), including a one-line preview of the message content — subject to the device's own notification-privacy setting (FR-021), never overriding it to force a preview on a locked screen.
- **FR-002**: The phone app MUST post a local notification when a previously-submitted chat question receives its answer while the app process is running.
- **FR-003**: The phone app MUST post a local notification when a new approval request arrives while the app process is running, and that notification MUST offer inline Approve and Deny actions.
- **FR-004**: Tapping an inline Approve or Deny action on an approval notification MUST require the same on-device authentication (Face ID/Touch ID/passcode) as resolving that approval from within the app before the approval is actually resolved — a dismissed or failed authentication MUST leave the approval unresolved.
- **FR-005**: An approval notification action that targets an approval already resolved elsewhere MUST fail gracefully with a clear "already resolved" outcome, not a crash or a silent no-op presented as success.
- **FR-006**: Tapping a Feed or Chat notification banner (not an action button) MUST open the app directly to the specific message/answer referenced, not merely the containing tab.
- **FR-007**: The system MUST NOT generate a duplicate notification for the same underlying Feed message, chat answer, or approval that has already been notified about.
- **FR-007a**: Each Feed message, chat answer, and approval MUST always receive its own individual notification, even when many arrive in quick succession (a burst) — the system MUST NOT collapse multiple items into a single summary notification; any visual grouping/stacking during a burst is left to the platform's standard by-app notification presentation, not custom app logic.
- **FR-008**: The phone's home-screen app icon MUST display a numeric badge equal to the combined count of unacknowledged Feed messages and unacknowledged chat answers; unresolved approvals MUST NOT contribute to this count.
- **FR-009**: The watch app icon MUST reflect the same badge count as the phone via standard watchOS badge-mirroring behavior, with no separate watch-side badge-setting logic required.
- **FR-010**: The watch MUST receive the same notifications as the phone via watchOS's standard automatic notification mirroring; this feature MUST NOT introduce any independent watch-side push/background-delivery path, preserving the existing WatchConnectivity `sendMessage`-only architecture (spec 072, research D2).
- **FR-011**: Every Feed message and every chat turn MUST have a distinguishable unread/acknowledged state, visible on both the phone's Feed/Chat views and the watch's Feed/History views.
- **FR-012**: The operator MUST be able to acknowledge an individual Feed message or chat turn (clearing its unread state and removing it from the badge count) from either the phone or the watch, independently of viewing/opening it — acknowledging is an explicit action, not an automatic side effect of merely viewing a tab.
- **FR-013**: The operator MUST be able to permanently delete an individual Feed message or chat turn from either the phone or the watch, in addition to the existing whole-history "clear all" action.
- **FR-014**: An acknowledge or delete action taken on one device (phone or watch) MUST be reflected on the other device the next time that device requests current state — no separate explicit "sync" action required, consistent with the watch's existing on-demand relay pattern (spec 072).
- **FR-015**: An acknowledge or delete action attempted from the watch while the phone is unreachable MUST surface the watch's existing "can't reach iPhone" state rather than silently failing or falsely reporting success.
- **FR-016**: Every question submitted from the watch's Ask tab MUST be recorded into the same conversation history store the phone's Chat tab and the watch's own History tab both read from, exactly as a phone-submitted question would be.
- **FR-017**: The watch's Feed and History tabs, and its display of a completed chat answer, MUST offer an explicit, per-item "read aloud" control that speaks the item's text content aloud on demand.
- **FR-018**: "Read aloud" MUST never trigger automatically — not on push/notification arrival, not on a tab becoming visible, not on any event other than the operator's explicit tap.
- **FR-019**: "Read aloud" on a non-text Feed message (photo or voice content) MUST speak a description of the content type rather than failing silently or producing no output.
- **FR-020**: If the operator has not granted notification permission, every other capability in this spec (Feed, Chat, Approvals, History, acknowledge, delete, read-aloud) MUST continue to work normally — only banner/badge/mirroring behavior is affected, and the app MUST make this limitation discoverable rather than failing silently.
- **FR-021**: Notification content previews (Feed message text, chat answer text) MUST be shown or hidden according to the device's own OS-level notification-privacy setting (e.g., "Show Previews: Always/When Unlocked/Never") — the app MUST NOT implement its own separate preview-hiding logic that overrides that platform setting in either direction.

### Key Entities

- **Unread State**: A per-item (per Feed message, per chat turn) flag distinguishing "new since last acknowledged" from "acknowledged." Lives only in the phone's existing message/conversation stores — the watch holds no unread state of its own, matching its existing no-persistent-state design (spec 072, FR-011).
- **Notification**: A locally-posted, user-visible alert tied to one Feed message, one chat answer, or one approval request. Carries enough identifying information to deep-link back to that specific item and, for approvals, to carry inline Approve/Deny actions gated by device authentication.
- **Badge Count**: The combined number of currently-unacknowledged Feed messages and chat answers, shown on the phone's app icon and mirrored to the watch's app icon via standard OS behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator who is not actively looking at either device becomes aware of a new Feed push, chat answer, or approval within a few seconds of it occurring, via a banner on whichever device (phone or watch) they're near.
- **SC-002**: An operator can resolve a routine approval entirely from a notification banner — including the required on-device authentication step — without ever opening the app.
- **SC-003**: An operator can tell, at a glance, exactly how many things are new versus already-handled, on either device, without having to re-read items they've already dealt with.
- **SC-004**: A question asked from the watch is indistinguishable, in the phone's chat history, from one asked on the phone — zero watch-originated questions are ever missing from that history.
- **SC-005**: An acknowledge or delete action taken on either device is correctly reflected on the other device the next time it's checked, with no manual "refresh"/"sync" step the operator has to remember to perform.
- **SC-006**: An operator with their hands occupied can have any text message or answer read aloud on the watch with a single deliberate tap, and is never surprised by unprompted spoken output.

## Assumptions

- **Local vs. remote push boundary**: this feature covers notifications generated while the phone app's process is alive (foreground or backgrounded) via the existing live EdgeClient WebSocket connection. True remote push for a fully-terminated app remains the existing, separately-tracked feature-066 capability, which stays non-functional until real Firebase/Apple Developer push credentials are configured (an operator-side prerequisite, out of scope here per the existing README caveat). This is a known, accepted limitation, not a defect this feature is expected to close.
- **Notification-permission default**: standard OS notification-permission prompting/handling applies (the app requests permission once, respects the operator's choice, and degrades gracefully if denied) — no custom re-prompting or nagging behavior beyond what the platform provides by default.
- **Approvals excluded from unread/badge tracking**: approvals already render as a live, always-visible pending list on both phone and watch (spec 072), so they get notification banners with inline actions (User Story 1) but do not participate in the unread/acknowledge/badge-count system in User Story 2 — a pending approval is not "unread," it's simply "pending" and already has its own always-visible affordance.
- **Delete is permanent, no undo**: consistent with the existing global "clear all" delete behavior (recent prior work), per-item delete introduced here is likewise immediate and permanent, with no trash/recovery step.
- **Viewing a tab does not implicitly acknowledge its contents**: opening the Feed or Chat/History tab lets the operator see what's unread, but does not itself clear any item's unread state — acknowledging remains a deliberate, explicit action per FR-012, so the operator can look at something now and deal with it later without losing track of the fact it's still "new."
- **Watch badge mirroring is standard OS behavior, not custom code**: this spec assumes (and requires verification of, per FR-009) that watchOS mirrors the paired iPhone's app badge automatically once the phone's badge is set via the standard platform API — no separate watch-side badge-setting relay method is expected to be necessary.
