import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';

void main() {
  test('appended messages persist across a simulated app restart (T029)', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_feed_test_');
    addTearDown(() => dir.delete(recursive: true));

    final first = EdgeMessage(
      contentType: MessageContentType.text,
      content: 'Toronto branch WAN outage detected — 14 locations affected.',
      designatedBy: 'agent',
      pushedAt: DateTime.utc(2026, 7, 22, 21, 40),
    );
    final second = EdgeMessage(
      contentType: MessageContentType.text,
      content: 'Follow-up: outage resolved.',
      designatedBy: 'agent',
      pushedAt: DateTime.utc(2026, 7, 22, 22, 5),
    );

    final storeBeforeRestart = MessageFeedStore(dir);
    await storeBeforeRestart.append(first);
    await storeBeforeRestart.append(second);
    expect(storeBeforeRestart.messages, hasLength(2));

    // Simulated restart: a brand-new store instance, same directory, no
    // in-memory state carried over — persistence must come from disk alone.
    final storeAfterRestart = MessageFeedStore(dir);
    expect(storeAfterRestart.messages, isEmpty); // not loaded yet
    await storeAfterRestart.load();
    expect(storeAfterRestart.messages, hasLength(2));
    expect(storeAfterRestart.messages[0].content, first.content);
    expect(storeAfterRestart.messages[1].content, second.content);
  });

  test('wireMessageFeed appends a Border-pushed message and acknowledges it', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_feed_test_');
    addTearDown(() => dir.delete(recursive: true));
    final store = MessageFeedStore(dir);

    final fakeClient = _FakeEdgeMethodSource();
    wireMessageFeed(fakeClient, store);

    final result = await fakeClient.handlers['n2n/edge/message']!({
      'content_type': 'text',
      'content': 'hello phone',
      'designated_by': 'agent',
      'pushed_at': '2026-07-22T21:40:00Z',
    });

    expect(result, {'received': true});
    expect(store.messages, hasLength(1));
    expect(store.messages.single.content, 'hello phone');
  });

  group('acknowledge/delete/unreadCount (073/FR-008/FR-012/FR-013)', () {
    late Directory dir;
    setUp(() async => dir = await Directory.systemTemp.createTemp('ncfed_feed_ack_test_'));
    tearDown(() => dir.delete(recursive: true));

    test('a new message is unread; unreadCount reflects it', () async {
      final store = MessageFeedStore(dir);
      await store.append(EdgeMessage(
        contentType: MessageContentType.text,
        content: 'hello',
        designatedBy: 'agent',
        pushedAt: DateTime.utc(2026, 7, 27),
      ));
      expect(store.unreadCount, 1);
      expect(store.messages.single.acknowledged, isFalse);
    });

    test('acknowledge clears unread state but keeps the message visible', () async {
      final store = MessageFeedStore(dir);
      final pushedAt = DateTime.utc(2026, 7, 27);
      await store.append(EdgeMessage(
        contentType: MessageContentType.text,
        content: 'hello',
        designatedBy: 'agent',
        pushedAt: pushedAt,
      ));

      await store.acknowledge(pushedAt);

      expect(store.unreadCount, 0);
      expect(store.messages, hasLength(1));
      expect(store.messages.single.acknowledged, isTrue);
    });

    test('acknowledge persists across a simulated restart', () async {
      final pushedAt = DateTime.utc(2026, 7, 27);
      final store = MessageFeedStore(dir);
      await store.append(EdgeMessage(
        contentType: MessageContentType.text,
        content: 'hello',
        designatedBy: 'agent',
        pushedAt: pushedAt,
      ));
      await store.acknowledge(pushedAt);

      final reloaded = MessageFeedStore(dir);
      await reloaded.load();
      expect(reloaded.unreadCount, 0);
      expect(reloaded.messages.single.acknowledged, isTrue);
    });

    test('delete permanently removes the message', () async {
      final store = MessageFeedStore(dir);
      final pushedAt = DateTime.utc(2026, 7, 27);
      await store.append(EdgeMessage(
        contentType: MessageContentType.text,
        content: 'hello',
        designatedBy: 'agent',
        pushedAt: pushedAt,
      ));

      await store.delete(pushedAt);

      expect(store.messages, isEmpty);
      expect(store.unreadCount, 0);

      final reloaded = MessageFeedStore(dir);
      await reloaded.load();
      expect(reloaded.messages, isEmpty);
    });

    test('a message written before this feature shipped (no acknowledged key) defaults to '
        'acknowledged=true, never unread (research D5)', () async {
      final file = File('${dir.path}/ncfed_message_feed.jsonl');
      await file.writeAsString(
        '${jsonEncode({
              'content_type': 'text',
              'content': 'pre-existing message',
              'designated_by': 'agent',
              'pushed_at': DateTime.utc(2026, 1, 1).toIso8601String(),
              // deliberately no 'acknowledged' key
            })}\n',
      );

      final store = MessageFeedStore(dir);
      await store.load();

      expect(store.unreadCount, 0);
      expect(store.messages.single.acknowledged, isTrue);
    });
  });
}

/// Minimal stand-in exposing just the `.on(method, handler)` surface
/// `wireMessageFeed` needs — avoids constructing a real `EdgeClient`
/// (which requires an actual WebSocketChannel) just to test the handler
/// wiring in isolation.
class _FakeEdgeMethodSource implements EdgeMethodSource {
  final Map<String, EdgeMethodHandler> handlers = {};

  @override
  void on(String method, EdgeMethodHandler handler) {
    handlers[method] = handler;
  }
}
