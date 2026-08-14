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

  group('deduplication by message identity (spec 107/US3, contract §2)', () {
    Directory tmp() {
      final d = Directory.systemTemp.createTempSync('ncfed_dedup_test_');
      addTearDown(() => d.delete(recursive: true));
      return d;
    }

    EdgeMessage msg(DateTime pushedAt, {String content = 'body', bool acked = false}) =>
        EdgeMessage(
          contentType: MessageContentType.text,
          content: content,
          designatedBy: 'agent',
          pushedAt: pushedAt,
          acknowledged: acked,
        );

    test('a duplicate pushed_at is declined (FR-004, FR-005)', () async {
      final store = MessageFeedStore(tmp());
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);

      expect(await store.append(msg(at, content: 'first')), isTrue);
      expect(await store.append(msg(at, content: 'second')), isFalse);

      expect(store.messages, hasLength(1));
      expect(store.messages.single.content, 'first',
          reason: 'the stored message wins; a duplicate never overwrites');
    });

    test('two distinct messages both store, even one second apart', () async {
      final store = MessageFeedStore(tmp());
      expect(await store.append(msg(DateTime.utc(2026, 8, 13, 16, 45, 34))), isTrue);
      expect(await store.append(msg(DateTime.utc(2026, 8, 13, 16, 45, 35))), isTrue);
      expect(store.messages, hasLength(2));
    });

    test('read state survives re-delivery (FR-006, §2.2)', () async {
      // A message the operator already read must not look unread again just
      // because the Border replayed it.
      final store = MessageFeedStore(tmp());
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      await store.append(msg(at));
      await store.acknowledge(at);
      expect(store.unreadCount, 0);

      expect(await store.append(msg(at)), isFalse);

      expect(store.unreadCount, 0, reason: 'a duplicate must not resurrect unread');
      expect(store.messages.single.acknowledged, isTrue);
    });

    test('dedup survives a restart, matching on what is on disk', () async {
      final dir = tmp();
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      await MessageFeedStore(dir).append(msg(at));

      final reopened = MessageFeedStore(dir);
      expect(await reopened.append(msg(at)), isFalse);
      expect(reopened.messages, hasLength(1));
    });

    test('identity is instant-based, not DateTime-equality based', () async {
      // Dart's DateTime.== also requires isUtc to agree, so the same moment
      // expressed in local time would otherwise store a second copy.
      final store = MessageFeedStore(tmp());
      final utc = DateTime.utc(2026, 8, 13, 16, 45, 34);
      expect(await store.append(msg(utc)), isTrue);
      expect(await store.append(msg(utc.toLocal())), isFalse);
      expect(store.messages, hasLength(1));
    });

    test('contains() reports what is stored', () async {
      final store = MessageFeedStore(tmp());
      final at = DateTime.utc(2026, 8, 13, 16, 45, 34);
      await store.append(msg(at));
      expect(store.contains(at), isTrue);
      expect(store.contains(DateTime.utc(2026, 8, 13, 16, 45, 35)), isFalse);
    });

    test('a declined duplicate does not re-announce via wireMessageFeed (§2.3)', () async {
      // Otherwise the double-entry bug becomes a double-badge bug.
      final store = MessageFeedStore(tmp());
      final client = _FakeEdgeMethodSource();
      final announced = <EdgeMessage>[];
      wireMessageFeed(client, store, onMessage: announced.add);
      final handler = client.handlers['n2n/edge/message']!;

      final params = {
        'content_type': 'text',
        'content': 'replayed body',
        'designated_by': 'agent',
        'pushed_at': '2026-08-13T16:45:34.000Z',
      };
      await handler(params);
      await handler(params);

      expect(store.messages, hasLength(1));
      expect(announced, hasLength(1));
    });
  });

  group('EdgeMessage.tryFromWire strictness (spec 107, contract §3.3)', () {
    test('rejects a missing or unparseable pushed_at rather than defaulting', () {
      expect(EdgeMessage.tryFromWire({'content_type': 'text', 'content': 'x'}), isNull);
      expect(
        EdgeMessage.tryFromWire(
            {'content_type': 'text', 'content': 'x', 'pushed_at': 'nope'}),
        isNull,
      );
    });

    test('fromWire keeps its lenient fallback for the live channel', () {
      // Unchanged on purpose (Principle XV): the authenticated live path always
      // carries pushed_at, and tightening it here would be a behavior change to
      // a path this feature is not fixing.
      final lenient = EdgeMessage.fromWire({'content_type': 'text', 'content': 'x'});
      expect(lenient.pushedAt, isNotNull);
    });

    test('accepts the fully stringified shape the sender emits', () {
      final m = EdgeMessage.tryFromWire({
        'content_type': 'text',
        'content': 'hello',
        'pushed_at': '2026-08-13T16:45:34.000Z',
        'designated_by': 'agent',
      });
      expect(m, isNotNull);
      expect(m!.content, 'hello');
    });
  });

  test('wireMessageFeed is the ONLY n2n/edge/message registration site (§4)', () {
    // EdgeClient.on() keeps only the LAST handler per method, so a second
    // registration anywhere would silently displace this one and disable live
    // delivery with no error — the highest-severity failure mode in spec 107,
    // and the cheapest to guard. Structural, because the bug is the existence
    // of a second call site, not the behavior of any one of them.
    final libDir = Directory('lib');
    final offenders = <String>[];
    for (final entity in libDir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final text = entity.readAsStringSync();
      if (!text.contains("'n2n/edge/message'")) continue;
      // The declaration inside wireMessageFeed is the one legitimate site.
      if (entity.path.endsWith('message_feed.dart')) continue;
      if (text.contains(".on('n2n/edge/message'")) offenders.add(entity.path);
    }
    expect(offenders, isEmpty,
        reason: 'only wireMessageFeed may register n2n/edge/message; found: $offenders');
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
