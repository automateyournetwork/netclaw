import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/foundation.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/ncfed/notification_deep_link.dart';
import 'package:netclaw_mobile/ncfed/push_registration.dart';

void main() {
  test('pushPlatformFor maps iOS to apns and everything else to fcm', () {
    expect(pushPlatformFor(TargetPlatform.iOS), 'apns');
    expect(pushPlatformFor(TargetPlatform.android), 'fcm');
    expect(pushPlatformFor(TargetPlatform.linux), 'fcm');
  });

  group('findMessageForNotificationData (T032)', () {
    final messages = [
      EdgeMessage(
        contentType: MessageContentType.text,
        content: 'first',
        designatedBy: 'agent',
        pushedAt: DateTime.utc(2026, 7, 22, 21, 40),
      ),
      EdgeMessage(
        contentType: MessageContentType.text,
        content: 'second',
        designatedBy: 'agent',
        pushedAt: DateTime.utc(2026, 7, 22, 22, 5),
      ),
    ];

    test('matches the message whose pushed_at equals the payload', () {
      final match = findMessageForNotificationData(messages, {
        'pushed_at': DateTime.utc(2026, 7, 22, 22, 5).toIso8601String(),
      });
      expect(match?.content, 'second');
    });

    test('returns null when no message matches', () {
      final match = findMessageForNotificationData(messages, {
        'pushed_at': DateTime.utc(2099, 1, 1).toIso8601String(),
      });
      expect(match, isNull);
    });

    test('returns null when the payload has no pushed_at at all', () {
      expect(findMessageForNotificationData(messages, {}), isNull);
    });
  });
}
