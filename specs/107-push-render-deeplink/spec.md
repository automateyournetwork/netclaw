# Feature Specification: Notification tap opens the message it names

**Feature Branch**: `107-push-render-deeplink`
**Created**: 2026-08-13
**Status**: Draft
**Input**: User description: "Notification tap opens the message it names, and a pushed message renders without waiting for replay"

## Context

Spec 106 (merged 2026-08-13) fixed the reported empty-feed bug: the Border now
treats a platform push as a wake signal rather than a delivery, persisting every
undelivered push and replaying it on the device's next connect. Verified
end-to-end on real hardware — a message queued at 16:45:34 was replayed at
16:49:15 and rendered in the app.

That closed the data-loss half of the problem. Two **experience** gaps remain,
both on the device, and neither loses data:

1. **Tapping a notification does not open the message it names.** The tap
   handler searches the local store the instant the app opens, but a replayed
   message does not arrive until after channel authentication plus a deliberate
   3-second settle delay (measured: auth 16:49:12.513, replay 16:49:15.514). The
   search finds nothing, so no message opens — the operator lands on whatever
   screen the app happened to be on and has to find the item themselves.

2. **A pushed message is not visible until the device establishes a live
   connection.** The push already carries the full message content, but the app
   ignores it and waits for the message to arrive over the live channel instead.
   On a device with a poor or blocked connection, the notification is all the
   operator ever sees.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tapping a notification opens that message (Priority: P1)

An operator away from their desk gets a notification that their network agent has
finished something. They tap it. The app opens directly to that message, already
scrolled to it and marked read — not to the last screen they were on, and not to
a feed where they have to hunt for what the banner just told them about.

**Why this priority**: This is the entire point of a notification. It is also the
gap the operator actually notices — spec 106 made the content arrive, so the
remaining complaint is "I tapped it and it didn't take me there." Delivers value
on its own with no other work in this spec.

**Independent Test**: Send a message to a device with the app closed. Tap the
notification. The message opens. Fully testable without touching how pushed
content is stored.

**Acceptance Scenarios**:

1. **Given** the app is closed and a message has been pushed, **When** the
   operator taps the notification, **Then** the app opens and displays that
   specific message, even though the message arrives several seconds after the
   app launches.
2. **Given** the app is backgrounded and a message has been pushed, **When** the
   operator taps the notification, **Then** the app foregrounds and displays that
   specific message.
3. **Given** the operator taps a notification for a message that is already in
   the feed, **When** the app opens, **Then** it displays that message
   immediately with no waiting.
4. **Given** the operator taps a notification and the named message never
   arrives, **When** a reasonable wait elapses, **Then** the app stops waiting
   and shows the feed rather than a spinner that never resolves.
5. **Given** the operator dismisses the notification without tapping and opens
   the app normally, **When** the app loads, **Then** no message is force-opened
   and the operator sees their normal starting screen.

---

### User Story 2 - A pushed message appears without a live connection (Priority: P2)

An operator on a hotel network where the agent's port is blocked gets a
notification. They open the app. The message is there and readable, even though
the app cannot establish a live connection to the Border at all.

**Why this priority**: Strictly an improvement on P1's outcome — it removes the
several-second wait and the dependency on connectivity. Lower priority because
spec 106 already guarantees the message is never lost; it will render whenever a
connection is next established. This story is about immediacy and
poor-connectivity resilience, not correctness.

**Independent Test**: With the device unable to reach the Border, push a message
and open the app. The message is visible.

**Acceptance Scenarios**:

1. **Given** the device cannot reach the Border, **When** a message is pushed and
   the operator opens the app, **Then** the message is visible in the feed.
2. **Given** a message was made visible from its notification, **When** the
   device later establishes a live connection and the same message is replayed,
   **Then** the operator sees exactly one copy of it.
3. **Given** the app is in the foreground with a live connection, **When** a
   message arrives, **Then** the operator sees exactly one copy of it.

---

### User Story 3 - No duplicates, ever (Priority: P1)

The operator's feed shows each message exactly once, regardless of how many
delivery paths carried it.

**Why this priority**: P1 alongside Story 1, and a **hard prerequisite for
Story 2** — Story 2 introduces a second way for a message to enter the feed, and
without deduplication every message delivered that way would appear twice. A
duplicated audit feed is worse than a delayed one: it makes the operator doubt
whether the agent acted once or twice.

**Independent Test**: Deliver the same message by two different paths and confirm
one entry appears.

**Acceptance Scenarios**:

1. **Given** a message has already been recorded, **When** the identical message
   is delivered again by any path, **Then** the feed still shows one entry.
2. **Given** two genuinely different messages, **When** both are delivered,
   **Then** the feed shows two entries, even if they arrive close together.
3. **Given** a message already marked read, **When** the same message is
   delivered again, **Then** it does not revert to unread.

### Edge Cases

- A notification is tapped for a message the operator's device is no longer
  authorized to receive (the Border revoked it) — the app must not hang waiting
  for a message that will never come.
- Two notifications are tapped in quick succession — the app opens the most
  recently tapped message rather than racing between them.
- A message is delivered twice with identical content but genuinely distinct
  send times — these are different messages and both must appear.
- A malformed or truncated push payload — the app must not corrupt the feed or
  crash; falling back to the live-connection path is acceptable.
- An approval request delivered by notification — approvals are a live,
  time-sensitive list with no per-item history view, so tapping one opens the
  approvals view rather than a feed message.
- The operator taps a notification while the app is already open and showing a
  different message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tapping a notification MUST open the specific message that
  notification names, whether the app was closed, backgrounded, or already open.
- **FR-002**: The app MUST still open the named message when that message arrives
  after the app has launched, rather than only when it is already stored.
- **FR-003**: The app MUST stop waiting for a named message after a bounded
  interval and fall back to showing the feed, so a message that never arrives
  cannot leave the operator on a stalled screen.
- **FR-004**: The feed MUST contain at most one entry per distinct message,
  regardless of how many delivery paths carried it.
- **FR-005**: Deduplication MUST key on the message's send time as recorded by
  the sender, which is already the identifier notifications carry.
- **FR-006**: Re-delivery of an already-recorded message MUST NOT alter its
  existing read state.
- **FR-007**: The app MUST record a message's content from its notification, so
  the message is visible without a live connection to the Border.
- **FR-008**: FR-007 MUST NOT be enabled before FR-004 is in place.
- **FR-009**: A notification carrying an approval request MUST continue to route
  to the approvals view, not the message feed.
- **FR-010**: A malformed notification payload MUST NOT corrupt the stored feed
  or crash the app.
- **FR-011**: Opening the app without tapping a notification MUST NOT force any
  message open.
- **FR-012**: Behavior MUST be equivalent on both mobile platforms, allowing for
  each platform's own notification permission and background-execution rules.

### Key Entities

- **Message**: A single Border-to-operator communication. Carries content, a
  content type, the time the sender sent it, whether it was replayed from a
  backlog, and whether the operator has read it. Its send time is what makes it
  distinct from every other message.
- **Notification**: The operating system's banner for a message. Names exactly
  one message and carries enough of that message to record it.
- **Feed**: The operator's ordered history of messages, held on the device and
  surviving app restarts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tapping a notification opens the named message in at least 95% of
  attempts, from a closed, backgrounded, or open app.
- **SC-002**: The operator reaches the named message with zero manual navigation
  steps after the tap — no scrolling or tab switching.
- **SC-003**: A pushed message is readable within 2 seconds of the app becoming
  interactive, down from the current several-second wait for a live connection.
- **SC-004**: A pushed message is readable with no working connection to the
  Border at all.
- **SC-005**: Zero duplicate feed entries across 50 consecutive messages
  delivered by mixed paths.
- **SC-006**: No message delivered by the Border is absent from the feed — the
  guarantee spec 106 established is preserved, not traded away.
- **SC-007**: A notification whose message never arrives leaves the operator on a
  usable screen within 10 seconds, never a permanent loading state.

## Assumptions

- The push payload already carries the full message content, so no change to what
  the Border sends is required. Confirmed against the current sender.
- The message's send time is unique per message at the granularity recorded.
  Two distinct messages sharing an identical send time would be treated as one;
  judged acceptable given the sender stamps whole seconds and the Border sends
  operator-initiated messages, not high-rate streams. Worth revisiting if
  automated senders are ever added.
- Notification permission has already been granted. Re-prompting for it, and the
  behavior when it is denied, are out of scope.
- The existing on-device feed store is extended rather than replaced; no
  migration of stored history is required.
- Both stories ship on the app's own release cadence. The iOS build reaches
  testers through TestFlight, so this cannot be delivered by a server restart the
  way spec 106 was — it is gated on a build going out.
- No change to the Border is in scope. Spec 106 owns delivery; this spec owns what
  the device does with what it receives.
- Adding a new push transport is out of scope. The existing one is used as-is.

## Dependencies

- **Spec 106** (merged): establishes that every undelivered push is persisted and
  replayed. Story 1's waiting behavior assumes replay actually arrives.
- **Spec 103** (merged): establishes the single push transport both platforms use.
- **Spec 073** (merged): established locally-posted notifications and their own
  tap routing, which already deep-links correctly. The remote-notification path
  this spec fixes must end up consistent with it, not a second parallel mechanism.
