# Phase 1 Data Model: Notification tap opens the message it names

**Feature**: 107-push-render-deeplink
**Date**: 2026-08-13

Two of the three entities already exist; this feature gives one of them an
explicit identity rule and the other an invariant it has been missing. Only
`PendingOpenIntent` is new, and it is in-memory only.

---

## Message

An existing entity (`EdgeMessage`). No new fields.

| Field | Meaning | Notes |
|---|---|---|
| `pushedAt` | When the sender sent it | **Identity.** See the identity rule below. |
| `content` | The message body | Arrives stringified over the push path (R4) |
| `contentType` | `text` / `voice` / `image` / `approval` | `approval` never enters the Feed (FR-009) |
| `replayed` | Whether it came from the Border's backlog | Renders as history rather than new |
| `read` | Whether the operator has seen it | **Must survive re-delivery** (FR-006) |

### Identity rule

Two Messages are the same Message when their `pushedAt` values are equal.

**This is a real constraint, not a formality.** The Border stamps `pushed_at` at
whole-second granularity (`%Y-%m-%dT%H:%M:%SZ`), so two genuinely distinct
messages sent inside the same second collapse into one feed entry. Accepted
because this path carries operator- and agent-initiated pushes, not a high-rate
stream. If that ever stops being true, the fix is a sender-assigned unique id —
a Border change, therefore a different spec. Do not paper over it client-side by
adding a second local identifier, which would break cross-path dedup (R2).

### Validation

- A Message with an unparseable `pushedAt` is **rejected, not defaulted**.
  Defaulting to "now" would mint a new identity on every delivery attempt and
  defeat dedup entirely — the one failure mode that would silently reintroduce
  duplicates. Rejection is safe: spec 106 guarantees replay will deliver it again
  over the live path.
- Unknown `contentType` is ignored rather than stored, consistent with how the
  live handler already treats it.

---

## Feed

An existing entity (`MessageFeedStore`), gaining one invariant.

### Invariant

**At most one entry per distinct Message**, enforced inside the store's append
path — not at its call sites (R3).

This must hold across *every* writer. As of this feature there are two (the live
channel handler and the push ingest path), and the enforcement point is
deliberately the one place both must pass through, so a future third writer
inherits it without knowing it exists.

### Behavior on duplicate

Declining the write is the whole behavior: the existing entry is left exactly as
it is, including its `read` state (FR-006). Nothing is merged, updated, or
re-ordered.

> **Dedup is not an audit gap.** The Border records every delivery in its own
> trail, including replays (`edge_push/queue_replay`). The device declining a
> duplicate *local write* erases nothing and must not be "corrected" by
> suppressing the Border-side record. Constitution Principle IV concerns the
> audit trail, which lives on the Border and is untouched here.

### Ordering

Unchanged — by `pushedAt`. A duplicate cannot reorder the feed because it is
never written.

---

## PendingOpenIntent

**New**, and in-memory only.

Represents "the operator tapped a notification naming a message we may not have
yet."

| Field | Meaning |
|---|---|
| `identifier` | The `pushedAt` of the message the notification named |
| `createdAt` | When the tap happened, for expiry |

### Lifecycle

```
                    ┌──────────────────────────────┐
   notification     │                              │
   tapped     ──────▶  pending(identifier)         │
                    │                              │
                    └──────┬──────────────┬────────┘
                           │              │
        message present    │              │  bounded wait elapses
        or arrives         │              │
                           ▼              ▼
                      resolved       expired
                   (open message)  (show feed)
```

- **At most one intent at a time.** A second tap replaces the first, so the
  operator lands on what they most recently tapped rather than the app racing
  between two (an Edge Case in the spec).
- **Resolves immediately** when the named message is already stored — the common
  case once Story 2 ships, and the reason the timeout path is rarely reached.
- **Expires** after a bounded wait (10s outer bound, SC-007), then the app shows
  the feed. Never a permanent loading state.
- **Does not survive an app restart.** Deliberate: no persistence, per the open
  item in R7. A tap whose app is killed before resolution loses only the
  navigation, never the message — spec 106 still delivers it to the feed.

### Why in-memory

It describes a navigation intent within one app session, not durable state.
Persisting it would mean a stale intent could hijack navigation on a later launch
for a reason the operator no longer remembers.
