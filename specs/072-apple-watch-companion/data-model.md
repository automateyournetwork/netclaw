# Data Model: Apple Watch Companion App for NetClaw Mobile

No new persistent storage anywhere in this feature (research: Technical Context "Storage: N/A" —
the watch holds nothing, and the phone's existing `ApprovalClient`/`MessageFeedStore`/
`EdgeAskClient` in-memory/on-disk state is reused unchanged). The entities below are the shapes
that cross the watch↔phone boundary and the one additive Border-facing field — not new database
tables or files.

## Watch Approval

Mirrors `PendingApproval` (`lib/ncfed/approval_client.dart`) as sent to the watch:

| Field | Type | Notes |
|---|---|---|
| `approval_id` | int | Same identity as the phone's `PendingApproval.approvalId` |
| `target_type` | string | Passed through unchanged |
| `target_name` | string | Passed through unchanged |
| `requesting_agent` | string | Passed through unchanged |
| `risk_name` | string? | Passed through unchanged, optional |
| `pushed_at` | ISO 8601 string | Passed through unchanged |

Resolution request (watch → phone → Border), see contracts/watch-relay.md for the exact envelope:

| Field | Type | Notes |
|---|---|---|
| `approval_id` | int | Which approval |
| `action` | `"approve"` \| `"deny"` | Same vocabulary as the phone |
| *(implicit)* `confirmation_method` | `"watch_passcode"` | Set by the phone relay, not by the watch itself — the watch never claims its own attribution string; the phone-side relay stamps it, keeping the source-of-truth on the side that actually talks to the Border (research D4) |

## Watch Feed Message

Mirrors `EdgeMessage` (`lib/ncfed/message_feed.dart`) as sent to the watch:

| Field | Type | Notes |
|---|---|---|
| `content_type` | `"text"` \| `"image"` \| `"voice"` | Same vocabulary as `MessageContentType` |
| `content` | string | Plain text for `text`; for `image`/`voice` the watch does NOT need the full base64 payload (no useful way to render either on-screen per FR-007) — only enough to show a type indicator. The relay MAY omit or truncate `content` for non-text types to avoid an unnecessarily large WatchConnectivity payload; exact truncation behavior is a `/speckit.tasks` implementation detail, not a data-model change. |
| `designated_by` | string | Passed through unchanged |
| `pushed_at` | ISO 8601 string | Passed through unchanged |

## Watch Ask Turn

A lighter-weight mirror of `TaskUpdate`/`ConversationTurn` (`lib/ncfed/edge_ask_client.dart`,
`lib/ncfed/conversation_store.dart`), scoped to the watch's single-in-flight-question model
(spec Assumptions — no multi-turn history on the watch):

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | Same identity as the phone's `TaskUpdate.taskId` |
| `request_text` | string | The dictated text actually submitted |
| `state` | `"waiting"` \| `"answered"` \| `"failed"` | A narrowed projection of the phone's full `TaskState` enum (`pending`/`working` both collapse to `"waiting"` for the watch's UI; `completed` → `"answered"`; `failed`/`cancelled` → `"failed"`) |
| `answer_text` | string? | Present once `state == "answered"` |

Not persisted on the watch — held only in the running watch app's view state for the current
question; a new app launch or a new question replaces it, per the spec's single-turn Assumption.

## Relay Availability State

Not a wire entity — a client-side (watch app) enum derived from how a `sendMessage` call resolves:

| State | Derived from |
|---|---|
| `connected` | The most recent relay call to the phone succeeded |
| `phoneUnreachable` | `WCSession.isReachable == false`, or `sendMessage` failed with an unreachable/no-companion-app error |
| `notEnrolled` | The phone relay responded but reported no active enrollment (the phone app is running and reachable, but `HomeShell`'s enrolled-state clients aren't available) |

Surfaced identically across all three watch views (FR-012) — this is the same three-way
distinction the spec's Edge Cases section requires between "can't reach the phone at all" and
"reached the phone, but it has nothing to relay to yet."
