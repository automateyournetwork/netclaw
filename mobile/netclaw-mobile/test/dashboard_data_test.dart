import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/ncfed/dashboard_data.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';

void main() {
  group('buildDashboardSnapshot', () {
    test('not enrolled: no stored enrollment', () {
      final snapshot = buildDashboardSnapshot(
        connected: false,
        stored: null,
        feedStore: null,
        conversationStore: null,
        approvalClient: null,
      );

      expect(snapshot.identity.enrolled, isFalse);
      expect(snapshot.unreadPending.totalUnread, 0);
      expect(snapshot.unreadPending.pendingApprovals, 0);
    });

    test('enrolled and connected surfaces identity from StoredEnrollment', () {
      final stored = const StoredEnrollment(
        memberId: 'member-123',
        keyFingerprint: 'fp',
        borderHost: '192.168.1.50',
        borderPort: 8443,
        clawDomain: 'border.home.arpa',
      );

      final snapshot = buildDashboardSnapshot(
        connected: true,
        stored: stored,
        feedStore: null,
        conversationStore: null,
        approvalClient: null,
      );

      expect(snapshot.connected, isTrue);
      expect(snapshot.identity.enrolled, isTrue);
      expect(snapshot.identity.memberId, 'member-123');
      expect(snapshot.identity.clawDomain, 'border.home.arpa');
    });

    test('enrolled but disconnected still surfaces identity, connected is false', () {
      final stored = const StoredEnrollment(
        memberId: 'member-123',
        keyFingerprint: 'fp',
        borderHost: '192.168.1.50',
        borderPort: 8443,
        clawDomain: 'border.home.arpa',
      );

      final snapshot = buildDashboardSnapshot(
        connected: false,
        stored: stored,
        feedStore: null,
        conversationStore: null,
        approvalClient: null,
      );

      // FR-013: a disconnected state must be surfaced as such, not hidden
      // behind whatever identity/enrollment data is still on disk.
      expect(snapshot.connected, isFalse);
      expect(snapshot.identity.enrolled, isTrue);
    });
  });

  group('UnreadPendingSnapshot', () {
    test('totalUnread combines feed and chat, excludes approvals', () {
      const snapshot = UnreadPendingSnapshot(unreadFeed: 3, unreadChat: 2, pendingApprovals: 5);
      expect(snapshot.totalUnread, 5);
      expect(snapshot.pendingApprovals, 5);
    });
  });
}
