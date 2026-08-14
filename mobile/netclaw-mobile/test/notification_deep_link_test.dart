import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/foundation.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
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

  group('parseLocalNotificationPayload (073/research D4)', () {
    test('parses a valid feed payload', () {
      final parsed = parseLocalNotificationPayload('{"type":"feed","identifier":"abc"}');
      expect(parsed, {'type': 'feed', 'identifier': 'abc'});
    });

    test('parses a valid chat payload', () {
      final parsed = parseLocalNotificationPayload('{"type":"chat","identifier":"task-1"}');
      expect(parsed, {'type': 'chat', 'identifier': 'task-1'});
    });

    test('returns null for a null payload', () {
      expect(parseLocalNotificationPayload(null), isNull);
    });

    test('returns null for malformed JSON', () {
      expect(parseLocalNotificationPayload('not json'), isNull);
    });

    test('returns null when type or identifier is missing', () {
      expect(parseLocalNotificationPayload('{"type":"feed"}'), isNull);
      expect(parseLocalNotificationPayload('{"identifier":"abc"}'), isNull);
    });
  });

  group('findTurnForIdentifier', () {
    final turns = [
      ConversationTurn(taskId: 'task-1', requestText: 'first', submittedAt: DateTime.utc(2026, 7, 27)),
      ConversationTurn(taskId: 'task-2', requestText: 'second', submittedAt: DateTime.utc(2026, 7, 27)),
    ];

    test('matches the turn whose taskId equals the identifier', () {
      final match = findTurnForIdentifier(turns, 'task-2');
      expect(match?.requestText, 'second');
    });

    test('returns null when no turn matches', () {
      expect(findTurnForIdentifier(turns, 'task-99'), isNull);
    });
  });

  group('NotificationDeepLink.handleLocalNotificationTap (073, generalized dispatcher)', () {
    late Directory dir;
    setUp(() async => dir = await Directory.systemTemp.createTemp('ncfed_deep_link_test_'));
    tearDown(() => dir.delete(recursive: true));

    test('a feed payload opens the matching message', () async {
      final feedStore = MessageFeedStore(dir);
      final pushedAt = DateTime.utc(2026, 7, 27, 13, 58, 2);
      await feedStore.append(EdgeMessage(
        contentType: MessageContentType.text,
        content: 'R2 flapping session cleared.',
        designatedBy: 'agent',
        pushedAt: pushedAt,
      ));
      EdgeMessage? opened;
      final deepLink = NotificationDeepLink(store: feedStore, openMessage: (m) => opened = m);

      await deepLink.handleLocalNotificationTap(
          '{"type":"feed","identifier":"${pushedAt.toIso8601String()}"}');

      expect(opened?.content, 'R2 flapping session cleared.');
    });

    test('a chat payload opens the matching turn', () async {
      final feedStore = MessageFeedStore(dir);
      final conversationStore = ConversationStore(dir);
      await conversationStore.addPending('task-1', 'is R2 still flapping');
      ConversationTurn? opened;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (_) {},
        conversationStore: conversationStore,
        openChatTurn: (t) => opened = t,
      );

      await deepLink.handleLocalNotificationTap('{"type":"chat","identifier":"task-1"}');

      expect(opened?.requestText, 'is R2 still flapping');
    });

    test('an approval payload opens nothing (no per-item deep-link target)', () async {
      final feedStore = MessageFeedStore(dir);
      bool messageOpened = false;
      final deepLink =
          NotificationDeepLink(store: feedStore, openMessage: (_) => messageOpened = true);

      await deepLink.handleLocalNotificationTap('{"type":"approval","identifier":"42"}');

      expect(messageOpened, isFalse);
    });

    test('a malformed payload is a no-op, not a crash', () async {
      final feedStore = MessageFeedStore(dir);
      final deepLink = NotificationDeepLink(store: feedStore, openMessage: (_) {});
      await deepLink.handleLocalNotificationTap('garbage');
      await deepLink.handleLocalNotificationTap(null);
    });
  });

  group('a tap whose message has not arrived yet (spec 107/US1)', () {
    late Directory dir;
    setUp(() async => dir = await Directory.systemTemp.createTemp('ncfed_intent_dl_test_'));
    tearDown(() => dir.delete(recursive: true));

    EdgeMessage msg(DateTime at) => EdgeMessage(
          contentType: MessageContentType.text,
          content: 'Replayed from the Border backlog.',
          designatedBy: 'agent',
          pushedAt: at,
        );

    test('resolves when the message arrives AFTER the tap (FR-002)', () async {
      // THE production bug. Measured against a real Border: channel auth at
      // 16:49:12.513, replay at 16:49:15.514. A cold app launch from a tap
      // finishes well inside that 3s gap, so the old single read of the store at
      // tap time could never match, and the tap opened nothing.
      final feedStore = MessageFeedStore(dir);
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      EdgeMessage? opened;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (m) => opened = m,
      );

      await deepLink.recordTap(at.toIso8601String());
      expect(opened, isNull, reason: 'nothing to open yet — but must keep waiting');
      expect(deepLink.intent.isPending, isTrue);

      // Replay lands seconds later.
      await feedStore.append(msg(at));
      deepLink.messageArrived();

      expect(opened, isNotNull);
      expect(opened!.pushedAt, at);
      deepLink.dispose();
    });

    test('resolves immediately when already stored, with no wait (FR-001)', () async {
      final feedStore = MessageFeedStore(dir);
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      await feedStore.append(msg(at));
      EdgeMessage? opened;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (m) => opened = m,
      );

      await deepLink.recordTap(at.toIso8601String());

      expect(opened, isNotNull);
      expect(deepLink.intent.isPending, isFalse);
      deepLink.dispose();
    });

    test('expires and reports it, rather than waiting forever (FR-003)', () async {
      final feedStore = MessageFeedStore(dir);
      EdgeMessage? opened;
      var timedOut = false;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (m) => opened = m,
        onOpenTimedOut: () => timedOut = true,
        intentTimeout: const Duration(milliseconds: 30),
      );

      await deepLink.recordTap('2026-08-13T16:45:34.000Z');
      await Future<void>.delayed(const Duration(milliseconds: 80));

      expect(timedOut, isTrue);
      expect(opened, isNull);
      deepLink.dispose();
    });

    test('a message arriving with no tap opens nothing (FR-011)', () async {
      final feedStore = MessageFeedStore(dir);
      EdgeMessage? opened;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (m) => opened = m,
      );

      await feedStore.append(msg(DateTime.utc(2026, 8, 13, 16, 45, 34)));
      deepLink.messageArrived();

      expect(opened, isNull, reason: 'no tap means no forced navigation');
      deepLink.dispose();
    });

    test('a tap naming nothing records nothing', () async {
      final feedStore = MessageFeedStore(dir);
      final deepLink = NotificationDeepLink(store: feedStore, openMessage: (_) {});
      await deepLink.recordTap(null);
      expect(deepLink.intent.isPending, isFalse);
      await deepLink.recordTap('');
      expect(deepLink.intent.isPending, isFalse);
      deepLink.dispose();
    });

    test('the local-notification path converges on the same intent (§5.4)', () async {
      // It was already correct, because a local notification is only posted for
      // an already-stored message. Convergence must not regress that.
      final feedStore = MessageFeedStore(dir);
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      await feedStore.append(msg(at));
      EdgeMessage? opened;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (m) => opened = m,
      );

      await deepLink.handleLocalNotificationTap(
          '{"type":"feed","identifier":"${at.toIso8601String()}"}');

      expect(opened, isNotNull);
      deepLink.dispose();
    });

    test('a local tap for a message not yet stored now also waits', () async {
      // Strictly better than before: previously this silently did nothing.
      final feedStore = MessageFeedStore(dir);
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      EdgeMessage? opened;
      final deepLink = NotificationDeepLink(
        store: feedStore,
        openMessage: (m) => opened = m,
      );

      await deepLink.handleLocalNotificationTap(
          '{"type":"feed","identifier":"${at.toIso8601String()}"}');
      expect(opened, isNull);

      await feedStore.append(msg(at));
      deepLink.messageArrived();
      expect(opened, isNotNull);
      deepLink.dispose();
    });
  });
}
