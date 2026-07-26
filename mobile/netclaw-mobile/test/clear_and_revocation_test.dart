import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/ncfed/reconnect_supervisor.dart';

void main() {
  late Directory dir;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('ncfed_clear');
  });

  tearDown(() async {
    if (await dir.exists()) await dir.delete(recursive: true);
  });

  group('ConversationStore.clear', () {
    test('removes every turn and the backing file', () async {
      final store = ConversationStore(dir);
      await store.addPending('t1', 'first');
      await store.addPending('t2', 'second');
      expect(store.turns, hasLength(2));

      await store.clear();

      expect(store.turns, isEmpty);
      expect(File('${dir.path}/ncfed_conversation.json').existsSync(), isFalse);
    });

    test('a cleared store stays empty across a simulated restart', () async {
      final store = ConversationStore(dir);
      await store.addPending('t1', 'first');
      await store.clear();

      // Fresh instance = cold start reading the same directory.
      final reopened = ConversationStore(dir);
      await reopened.load();
      expect(reopened.turns, isEmpty);
    });

    test('clearing an already-empty store is a no-op, not an error', () async {
      final store = ConversationStore(dir);
      await store.clear();
      await store.clear();
      expect(store.turns, isEmpty);
    });

    test('hasInProgressTurns drives the extra warning in the confirm dialog', () async {
      final store = ConversationStore(dir);
      expect(store.hasInProgressTurns, isFalse, reason: 'empty store has nothing running');

      await store.addPending('t1', 'ask');
      expect(store.hasInProgressTurns, isTrue, reason: 'a pending turn is in progress');

      await store.updateState('t1', 'completed', answerText: 'done');
      expect(store.hasInProgressTurns, isFalse, reason: 'terminal turns are not in progress');
    });
  });

  group('MessageFeedStore.clear', () {
    EdgeMessage msg(String content) => EdgeMessage(
          contentType: MessageContentType.text,
          content: content,
          designatedBy: 'agent',
          pushedAt: DateTime.now().toUtc(),
        );

    test('removes every message and the backing file', () async {
      final store = MessageFeedStore(dir);
      await store.append(msg('one'));
      await store.append(msg('two'));
      expect(store.messages, hasLength(2));

      await store.clear();

      expect(store.messages, isEmpty);
      expect(File('${dir.path}/ncfed_message_feed.jsonl').existsSync(), isFalse);
    });

    test('append still works after a clear (file is recreated)', () async {
      final store = MessageFeedStore(dir);
      await store.append(msg('one'));
      await store.clear();
      await store.append(msg('after'));

      expect(store.messages.map((m) => m.content), ['after']);
      final reopened = MessageFeedStore(dir);
      await reopened.load();
      expect(reopened.messages.map((m) => m.content), ['after'],
          reason: 'the post-clear append must survive a restart');
    });
  });

  group('ReconnectSupervisor revocation', () {
    test('stops the loop and reports unrecoverable when the Border revokes', () async {
      var dials = 0;
      var unrecoverable = 0;
      final supervisor = ReconnectSupervisor<void>(
        dial: () async {
          dials++;
          throw EdgeClientException('-32023', 'not trusted');
        },
        onConnected: (_) {},
        onUnrecoverable: () => unrecoverable++,
        sleep: (_) async {},
      );

      await supervisor.run().timeout(const Duration(seconds: 5));

      expect(dials, 1, reason: 'a revoked identity must not be retried at all');
      expect(unrecoverable, 1);
    });

    test('a transient failure still retries and backs off', () async {
      var dials = 0;
      var unrecoverable = 0;
      late ReconnectSupervisor<void> supervisor;
      supervisor = ReconnectSupervisor<void>(
        dial: () async {
          dials++;
          if (dials < 3) throw Exception('connection_error');
          return;
        },
        onConnected: (_) => supervisor.stop(),
        onUnrecoverable: () => unrecoverable++,
        sleep: (_) async {},
      );

      await supervisor.run().timeout(const Duration(seconds: 5));

      expect(dials, 3, reason: 'transient errors retry until success');
      expect(unrecoverable, 0, reason: 'a timeout is not a revocation');
      expect(supervisor.currentBackoff, ReconnectSupervisor.initialBackoff,
          reason: 'backoff resets once connected');
    });
  });
}
