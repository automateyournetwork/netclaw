# Phase 0 Research: Notification tap opens the message it names

**Feature**: 107-push-render-deeplink
**Date**: 2026-08-13

Most of this feature's unknowns were resolved during the production investigation
that produced spec 106 rather than by fresh research, so several decisions below
cite direct observation of a running system. Where that is the case it is stated,
because an observed fact and a design preference deserve different confidence.

---

## R1 — How should the tap handler wait for a message that has not arrived yet?

**Decision**: Record the tapped identifier as a *pending intent*, then resolve it
either immediately (message already stored) or when the store next gains a
matching message, with a bounded timeout after which the intent is discarded and
the feed shown.

**Rationale**: The tap and the message's arrival are genuinely concurrent events
with no guaranteed order, so any fix that only reads the store once will keep
losing the race. Measured in production: channel auth completed at 16:49:12.513
and the replayed message landed at 16:49:15.514 — a 3.0s gap, matching the
Border's deliberate `N2N_EDGE_REPLAY_SETTLE_S`. App launch from a cold tap is
well under that, so the current single read is *guaranteed* to miss on a
cold-start tap, not merely likely to.

An intent also composes with Story 2: once the FCM payload is persisted on
receipt, the same intent resolves instantly from the store with no waiting, and
the timeout path becomes dead code in the common case rather than needing
separate handling.

**Alternatives considered**:

- *Poll the store on a timer* — simplest, but picks an arbitrary interval and
  either wastes wakeups or adds latency. The store already has a change signal
  (`wireMessageFeed`'s `onMessage` callback fires after every append), so polling
  would ignore an existing mechanism.
- *Delay the deep-link check by a fixed 3.5s* — couples the app to a Border-side
  constant it cannot see, and breaks silently if that constant is retuned. Worse,
  it adds 3.5s to the already-fast case where the message is present.
- *Have the Border withhold the notification until after replay* — a Border
  change, explicitly out of scope, and it would delay the banner (the thing that
  works well today) to fix the tap.

**Timeout value**: 10s outer bound, from SC-007. Long enough to cover auth plus
the 3s settle plus retry margin on a slow network; short enough that a revoked
device does not sit on a stalled screen.

---

## R2 — What identifies a message for deduplication?

**Decision**: `pushed_at`, the sender's send timestamp.

**Rationale**: It is already the de facto identifier throughout the app and
requires no Border change. `EdgeMessage.fromWire` parses it; the local-notification
tap path (`handleLocalNotificationTap`, spec 073) already matches on
`{'pushed_at': identifier}`; and `findMessageForNotificationData` already searches
by it. Adding a second identifier would mean two competing notions of message
identity.

**Known limitation, escalated from the spec's Assumptions**: the Border stamps
`pushed_at` with whole-second granularity
(`time.strftime("%Y-%m-%dT%H:%M:%SZ")`). Two genuinely distinct messages sent
inside the same second would collapse into one feed entry. Judged acceptable
because this route only carries operator- and agent-initiated pushes, not a
high-rate stream — but it is a real correctness limit, not a theoretical one, and
it is recorded in `data-model.md` as a constraint rather than buried here.

**If that limitation ever becomes unacceptable**, the fix is a sender-assigned
unique message id — which is a Border change and therefore a *different spec*.
Deliberately not smuggled into this one.

**Alternatives considered**:

- *Content hash* — collapses two legitimately identical messages (e.g. the same
  status pushed twice, deliberately). Wrong semantics.
- *Client-assigned id on receipt* — cannot dedup across delivery paths, since each
  path would mint its own id. Defeats the purpose.
- *(pushed_at, content_type) composite* — marginal gain over `pushed_at` alone,
  since a same-second collision with differing content types is vanishingly rare,
  and it complicates every comparison site. Rejected as unearned complexity.

---

## R3 — Where does deduplication belong?

**Decision**: Inside the feed store's append path, not at the call sites.

**Rationale**: Story 2 adds a second writer. Dedup at the call sites would mean
two implementations that must agree forever, which is precisely the drift pattern
this repo has been bitten by before (the `member_liveness` inline-computation
drift has its own regression test guarding it). One chokepoint in the store makes
the invariant structural: it cannot be bypassed by a future third writer.

`FR-006` (re-delivery must not reset read state) falls out naturally from a store
that treats an existing `pushed_at` as "already have it, ignore".

**Alternatives considered**:

- *Dedup in `wireMessageFeed`'s handler* — leaves the FCM path to reimplement it.
- *Dedup at render time* — hides duplicates rather than preventing them; the
  stored file still grows with junk, and the badge/unread counts would still
  double-count.

---

## R4 — How is the FCM data payload consumed, given every value arrives as a string?

**Decision**: Reconstruct through the existing wire parser, tolerating stringified
values, and route by `content_type` exactly as the live path does.

**Rationale**: The Border already sends the full content as a data payload
(`send_fcm`: a `notification` block for the banner plus
`data: {k: str(v) for k, v in content.items()}`). Two consequences observed
directly in that code:

1. **Every value is stringified**, including any non-string field. The client must
   not assume types survive the trip. This is the single most likely source of a
   silent parse failure, and is why FR-010 (malformed payload must not corrupt the
   feed) exists.
2. **`content_type` is present in the data payload**, so approval routing (FR-009)
   can be honored on this path with the same discriminator the live path uses —
   `'approval'` goes to the approvals view, never the feed.

Reusing the existing parser rather than writing a second one keeps a single
definition of what a message is.

**Alternatives considered**:

- *A separate lightweight parser for FCM* — two parsers, guaranteed to drift.
- *Ask the Border to send a JSON blob in one data key* — a Border change, out of
  scope, and unnecessary since the current shape is already sufficient.

---

## R5 — Foreground, background, and terminated: which handlers are needed?

**Decision**: Handle the foreground-message and background-message cases for
persistence, and keep the existing tap entry points for navigation. Treat the
terminated-app case as covered by the launch-time tap path plus replay, not by a
background handler guarantee.

**Rationale**: Background execution for a data-carrying push is subject to OS
discretion on both platforms — it is not a delivery guarantee, and building the
feature as though it were would reintroduce a silent-loss path of exactly the kind
spec 106 just removed. Spec 106's queue-and-replay is the guarantee; this feature
is an *acceleration* of it. That framing is what keeps SC-006 (no message
absent from the feed) true even when the OS declines to run the handler.

**Consequence for testing**: whether the OS actually runs a background handler for
a given push is not determinable in the Dart test suite. Flagged in R7.

**Alternatives considered**:

- *Rely solely on a background handler* — would make correctness depend on OS
  scheduling. Rejected on the same grounds spec 106 was written.
- *Foreground-only persistence* — leaves the common case (app closed, tap the
  banner) still waiting for replay, which is most of the value of Story 2.

---

## R6 — Must the remote and local notification tap paths converge?

**Decision**: Yes — both resolve through one shared intent mechanism.

**Rationale**: `handleLocalNotificationTap` (spec 073) already deep-links
correctly, because a locally-posted notification is only ever posted for a message
the app has *already* stored, so its single store read always succeeds. The remote
path has the same job and a different outcome purely because of arrival timing.
Two mechanisms for one behavior would mean the next change has to be made twice;
the local path's existing correctness is a reason to converge on it, not to leave
it alone.

**Constraint to preserve**: `EdgeClient.on()` keeps only the **last** handler
registered per method, so `wireMessageFeed` must remain the single registration
site for `n2n/edge/message`. Any new store writer must not register a second
handler for that method — it would silently displace the first. This is a real
footgun already documented in that function's own comment.

---

## R7 — What can the existing Dart test suite verify, and what needs hardware?

**Decision**: Cover identity/dedup, intent resolution ordering, payload parsing,
and approval routing in the existing suite. Accept device verification only for
OS-scheduling behavior.

**Coverable in `test/`** (the suite already has close analogues —
`message_feed_test.dart`, `notification_deep_link_test.dart`,
`notification_response_routing_test.dart`, `feed_screen_highlight_test.dart`,
`badge_lifecycle_test.dart`):

- dedup by `pushed_at`, including the read-state-preservation case
- intent resolves when the message arrives *after* the tap (the actual bug)
- intent resolves immediately when the message is already stored
- intent times out and falls back to the feed
- stringified payload reconstructs correctly; malformed payload is rejected
  without corrupting the store
- `content_type: 'approval'` routes to approvals, not the feed
- exactly one `n2n/edge/message` registration site remains

**Requires real hardware, and cannot be faked**:

- whether the OS runs the background handler for a given push
- end-to-end tap→open from a genuinely terminated app
- iOS specifically, since the build is TestFlight-gated

**Rationale for calling this out prominently**: device verification on iOS costs a
TestFlight round trip. Anything that *can* be pinned in the Dart suite should be,
so a device session is spent only on what genuinely needs one. Spec 106's own
lesson applies — its route tiering had no coverage at all, which is exactly why
the bug shipped.

---

## Open items carried into planning

| Item | Why not resolved here |
|---|---|
| Exact timeout constant (within the 10s bound of SC-007) | Implementation tuning; no user-visible difference across plausible values |
| Whether the pending intent survives an app restart | Needs a product call — a tap whose app is killed before resolution is an edge case with no observed frequency data. Defaulting to "does not survive" (simpler, no persistence) unless planning finds otherwise |
