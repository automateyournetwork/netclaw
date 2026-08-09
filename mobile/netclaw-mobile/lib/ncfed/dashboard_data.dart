import 'approval_client.dart';
import 'conversation_store.dart';
import 'enrollment_store.dart';
import 'message_feed.dart';

/// This device's standing within its NCFED federation, as far as the phone
/// app already knows it (099/FR-012) -- built from the same `StoredEnrollment`
/// `reconnectInPlace` already uses, not a new Border query. `StoredEnrollment`
/// carries no risk/member-scope field today (066/068 never needed one), so
/// this only surfaces what's genuinely available rather than inventing a new
/// Border-side data surface for it (research.md R9).
class FederationIdentitySnapshot {
  final bool enrolled;
  final String memberId;
  final String clawDomain;

  const FederationIdentitySnapshot({
    required this.enrolled,
    required this.memberId,
    required this.clawDomain,
  });

  factory FederationIdentitySnapshot.notEnrolled() =>
      const FederationIdentitySnapshot(enrolled: false, memberId: '', clawDomain: '');

  factory FederationIdentitySnapshot.fromStored(StoredEnrollment stored) =>
      FederationIdentitySnapshot(
        enrolled: true,
        memberId: stored.memberId,
        clawDomain: stored.clawDomain,
      );
}

/// The reconciled unread/pending counts every surface this spec touches
/// (badge, Dashboard, watch complication, Lock Screen Live Activity) is
/// meant to agree on (099/FR-012, Key Entities: Unread/Pending Count).
class UnreadPendingSnapshot {
  final int unreadFeed;
  final int unreadChat;
  final int pendingApprovals;

  const UnreadPendingSnapshot({
    required this.unreadFeed,
    required this.unreadChat,
    required this.pendingApprovals,
  });

  int get totalUnread => unreadFeed + unreadChat;
}

/// Everything the Dashboard (099/FR-012) shows, assembled purely from state
/// `_HomeShellState` already holds for other screens -- no new network call.
class DashboardSnapshot {
  final bool connected;
  final FederationIdentitySnapshot identity;
  final UnreadPendingSnapshot unreadPending;

  const DashboardSnapshot({
    required this.connected,
    required this.identity,
    required this.unreadPending,
  });
}

DashboardSnapshot buildDashboardSnapshot({
  required bool connected,
  required StoredEnrollment? stored,
  required MessageFeedStore? feedStore,
  required ConversationStore? conversationStore,
  required ApprovalClient? approvalClient,
}) {
  return DashboardSnapshot(
    connected: connected,
    identity: stored == null
        ? FederationIdentitySnapshot.notEnrolled()
        : FederationIdentitySnapshot.fromStored(stored),
    unreadPending: UnreadPendingSnapshot(
      unreadFeed: feedStore?.unreadCount ?? 0,
      unreadChat: conversationStore?.unreadCount ?? 0,
      pendingApprovals: approvalClient?.currentPending.length ?? 0,
    ),
  );
}
