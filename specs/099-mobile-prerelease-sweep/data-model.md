# Data Model: Mobile Pre-Release Hardening & Expansion Sweep

No new persistent storage is introduced (see research.md R9, plan.md Storage). These are the shapes new/modified code passes around in memory, derived entirely from spec.md's Key Entities section.

## UnreadPendingSnapshot

Computed on demand, never persisted, feeds the phone badge (Story 1), the Dashboard (Story 5), the Lock Screen Live Activity (Story 7), and the watch complication (Story 8) — one source of truth, four presentations.

| Field | Type | Notes |
|---|---|---|
| `unreadFeedCount` | int | from existing `FeedStore.unreadCount` |
| `unreadChatCount` | int | from existing `ConversationStore.unreadCount` |
| `pendingApprovalCount` | int | from existing `ApprovalClient.currentPending.length` |
| `computedAt` | timestamp | when this snapshot was assembled — used to detect staleness on the Dashboard (FR-013) |

Badge value (existing `combinedBadgeCount`) = `unreadFeedCount + unreadChatCount` (approvals intentionally excluded from the badge per existing spec-073 Assumptions — unchanged by this spec). Dashboard/Live Activity/complication display `pendingApprovalCount` alongside the combined unread count.

## ApprovalResolution

Not a new type — this documents the existing `confirmAndResolve`/`ApprovalClient.resolve` contract (research.md R1) that Stories 6/7/8 all route through unchanged.

| Field | Type | Notes |
|---|---|---|
| `approvalId` | int | existing |
| `action` | `'approve' \| 'deny'` | existing |
| `confirmationMethod` | string, default `'biometric'` | existing |
| resolution surface | in-app button / notification action / (new) Live Activity action | in-app and notification-action already share one code path (R1); a Live Activity action button (Story 7, if implemented as an actionable Live Activity rather than a display-only one) MUST also route through this same function — no new resolution path is created |

## FederationIdentitySnapshot (Dashboard, Story 5)

| Field | Type | Notes |
|---|---|---|
| `deviceIdentity` | string/struct | from the existing persisted enrollment store used by `reconnectInPlace` (`stored.memberId`, `stored.keyFingerprint`) |
| `riskName` / `memberScope` | string | from existing enrollment/member data already available post-enrollment |
| `borderConnectionState` | `connected \| degraded \| disconnected` | derived from the existing `ReconnectSupervisor`/edge-client connection state already driving `_wireReconnect` |
| `lastSeenAt` | timestamp \| null | last successful heartbeat/message exchange, if already tracked; if not currently tracked anywhere, this is the one field research.md R9 flags as a possible small addition to the existing heartbeat client rather than a new subsystem |
| `enrollmentStatus` | `enrolled \| not_enrolled` | `not_enrolled` drives the Dashboard's explicit "not yet enrolled" empty state (Edge Cases, spec.md) |

## LiveActivityState (Story 7)

Native `ActivityAttributes`/`ContentState` pair, mirrored 1:1 from `UnreadPendingSnapshot`'s `pendingApprovalCount` and the specific approval that triggered the activity — no independent state machine:

| Field | Type | Notes |
|---|---|---|
| `approvalId` | int | which pending approval this activity represents |
| `targetName` | string | display-only, matches what the notification/in-app screen already shows |
| `status` | `pending \| resolved` | activity ends (dismissed) shortly after transitioning to `resolved` |

Content shown on the Lock Screen is limited to "a pending approval exists" plus the non-sensitive `targetName` — no approval payload details, per FR-017's "without exposing sensitive approval content" requirement.

## WatchComplicationEntry (Story 8)

| Field | Type | Notes |
|---|---|---|
| `pendingApprovalCount` | int | same value as `UnreadPendingSnapshot.pendingApprovalCount`, delivered to the watch via the existing `WatchConnectivitySession`/`WatchDataStore` plumbing (072) |
| `lastUpdated` | timestamp | complication timeline entry date |

## ReleaseBuildConfiguration (Story 2/3 — configuration, not runtime data)

Documents the two build shapes this spec produces, not a data structure the app manipulates at runtime:

| Field | Free/Personal team (today) | Paid team (once active) |
|---|---|---|
| `CODE_SIGN_ENTITLEMENTS` | unset (push disconnected, current behavior preserved per FR-007) | set, `aps-environment` signed |
| `UIBackgroundModes` | absent | `remote-notification` present |
| Distribution export | N/A | via `ExportOptions.plist` + `scripts/mobile-release-archive.sh` |
