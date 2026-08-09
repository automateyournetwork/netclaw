# Contract: Notification Action Category (existing — documented for this spec's verification tasks)

This is not new interface surface — it documents the already-implemented contract Story 6's tasks verify against, so verification has a concrete spec to check rather than re-deriving it from source each time.

## Category

- **Identifier**: `approval` (`approvalCategoryId`, `local_notifications.dart:11`)
- **Actions**:
  - `approve` (`approveActionId`) — iOS: `DarwinNotificationActionOption.authenticationRequired`. Android: `AndroidNotificationAction('approve', 'Approve')`, no OS-level gate.
  - `deny` (`denyActionId`) — same shape, deny semantics.
- **Payload**: JSON `{"type": ..., "identifier": "<approvalId>"}` via `notificationPayload()`.

## Response handling contract

`_handleNotificationResponse` in `main.dart` MUST, for either action:

1. Parse `identifier` from the payload; a missing/unparseable identifier is a silent no-op (never crash, never guess an approval id).
2. Call `confirmAndResolve(client:, approvalId:, targetName:, action:)` — **never** call `ApprovalClient.resolve()` directly from a notification-response handler. This is the invariant Story 6 verification checks (research.md R1); any future change that adds a second resolution path bypassing `confirmAndResolve` is a regression against FR-015.
3. `confirmAndResolve` MUST perform a fresh `local_auth` challenge before resolving, MUST return `null` (no message) on success or cancellation/failure, and MUST return `'Already resolved'` when the approval was already resolved elsewhere (FR-016) — never silently double-resolve, never throw an unhandled error to the user.

## Extension point for Story 7 (Live Activity)

If the Live Activity itself exposes an actionable button (as opposed to display-only), it MUST invoke this same `confirmAndResolve` path via the same platform channel/plugin bridge pattern used for notification actions — not a new resolution entry point.
