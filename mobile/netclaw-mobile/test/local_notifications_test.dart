import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/local_notifications.dart';

void main() {
  group('combinedBadgeCount', () {
    test('sums unread Feed and unread Chat counts', () {
      expect(combinedBadgeCount(unreadFeed: 3, unreadChat: 2), 5);
    });

    test('zero when both are zero', () {
      expect(combinedBadgeCount(unreadFeed: 0, unreadChat: 0), 0);
    });
  });

  group('NotificationDedup', () {
    test('the first call for an identifier returns true; every repeat returns false (FR-007)', () {
      final dedup = NotificationDedup();
      expect(dedup.shouldPost('feed:2026-07-27T13:58:02Z'), isTrue);
      expect(dedup.shouldPost('feed:2026-07-27T13:58:02Z'), isFalse);
      expect(dedup.shouldPost('feed:2026-07-27T13:58:02Z'), isFalse);
    });

    test('distinct identifiers are tracked independently', () {
      final dedup = NotificationDedup();
      expect(dedup.shouldPost('chat:task-1'), isTrue);
      expect(dedup.shouldPost('approval:42'), isTrue);
      expect(dedup.shouldPost('chat:task-1'), isFalse);
      expect(dedup.shouldPost('approval:42'), isFalse);
    });
  });

  group('notificationPayload', () {
    test('encodes type and identifier, distinguishing them by type even with the same identifier',
        () {
      final feed = notificationPayload(type: 'feed', identifier: 'shared-id');
      final chat = notificationPayload(type: 'chat', identifier: 'shared-id');
      expect(feed, isNot(equals(chat)));
    });
  });
}
