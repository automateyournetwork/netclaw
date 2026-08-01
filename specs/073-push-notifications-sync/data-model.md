# Data Model: Push Notifications, Unread Tracking & Cross-Device Sync

All entities below are extensions of existing classes (`lib/ncfed/message_feed.dart`, `lib/ncfed/conversation_store.dart`) — no new top-level store is introduced. Both stores remain phone-local; the watch continues to hold no persistent state of its own (spec 072, FR-011).

## EdgeMessage (extended)

Existing fields (unchanged): `contentType` (text/voice/image), `content`, `designatedBy`, `pushedAt`.

- **`acknowledged`** (bool, new): whether the operator has explicitly acknowledged this message. Defaults to `false` for newly-appended messages.
  - `toJson()` gains `'acknowledged': acknowledged`.
  - `fromJson()` MUST default a missing `acknowledged` key to `true` — see research.md D5. This is the one load-bearing migration rule in this feature; getting the default backwards makes every pre-existing message appear unread on first launch after upgrade.

**Identity for deep-linking/dedup**: `pushedAt` (already the natural per-message identity used by `NotificationDeepLink` today) continues to serve as the identifier carried in a notification's payload and in `watch/feed/acknowledge`/`watch/feed/delete`'s request.

## MessageFeedStore (extended)

Existing behavior (unchanged): append-only JSON-Lines persistence, `load()`, `append()`, `clear()`.

- **`acknowledge(DateTime pushedAt)`** (new): marks the matching message's `acknowledged` field `true` and persists.
- **`delete(DateTime pushedAt)`** (new): permanently removes the matching message and persists — the store stops being purely append-only as of this feature (delete is now a legitimate, if separately-triggered, mutation alongside the existing whole-file `clear()`).
- **`unreadCount`** (new, derived): count of messages where `acknowledged == false`. Feeds into the combined app badge (D3).

## ConversationTurn (extended)

Existing fields (unchanged): `taskId`, `requestText`, `answerText`, `state`, `submittedAt`, `photoPath`.

- **`acknowledged`** (bool, new): same semantics as `EdgeMessage.acknowledged`. Defaults to `false` for newly-created turns, defaults a missing key to `true` on load (same migration rule, D5).
- **`origin`** (string, new, `"phone"` | `"watch"`): records which surface submitted this turn. Purely informational (no requirement reads it back for behavior) — added because User Story 3 explicitly makes watch-originated turns first-class citizens of this store, and having a durable record of where a question came from is a natural, nearly-free byproduct of fixing that gap. Defaults to `"phone"` for turns created before this field existed (a missing key is never watch-originated, since the watch had no way to write into this store at all before FR-016).

**Identity for deep-linking/dedup**: `taskId` (already the natural per-turn identity) continues to serve as the identifier carried in a notification's payload and in `watch/history/acknowledge`/`watch/history/delete`'s request.

## ConversationStore (extended)

Existing behavior (unchanged): whole-file JSON persistence, `load()`, `addPending()`, `updateState()`, `hasInProgressTurns`, `clear()`.

- **`acknowledge(String taskId)`** (new): marks the matching turn's `acknowledged` field `true` and persists.
- **`delete(String taskId)`** (new): permanently removes the matching turn and persists.
- **`unreadCount`** (new, derived): count of turns where `state` is terminal (`completed`/`failed`/`cancelled` — an in-progress turn has nothing to acknowledge yet) AND `acknowledged == false`. Feeds into the combined app badge (D3).

## Notification (new, ephemeral — not persisted)

A locally-posted alert, one per Feed message / chat answer / approval (FR-007a: never batched). Not a stored entity — described here for its payload shape, which IS load-bearing for FR-006's deep-link requirement.

| Field | Type | Purpose |
|---|---|---|
| `type` | `"feed"` \| `"chat"` \| `"approval"` | Which capability this notification is about — determines both its content shape and where a tap deep-links to. |
| `identifier` | string | `EdgeMessage.pushedAt` (ISO string) for `feed`, `ConversationTurn.taskId` for `chat`, `approval_id` for `approval`. |
| `preview` | string, optional | One-line content preview (feed/chat only; subject to the OS's own "Show Previews" setting per FR-021 — the app never overrides that). |
| `actions` | list, approval only | `["approve", "deny"]`, each requiring on-device authentication before it takes effect (FR-004, D2). |

## Approval Resolve Response (extended, Border-side wire shape)

`n2n/edge/approval_resolve`'s existing response gains one additive field:

- **`already_resolved`** (bool, new): `true` if this call found the approval already resolved (a same-approval retry / race with another device or the in-app flow) and therefore had no effect; `false` if this call is what actually resolved it. Existing callers that ignore this field see identical behavior to today (D6) — this is purely additive, no existing field changes meaning.
