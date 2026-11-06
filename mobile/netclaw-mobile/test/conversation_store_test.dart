import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/external_source.dart';

void main() {
  test('concurrent cold readers and admission await the existing history', () async {
    final dir = await Directory.systemTemp.createTemp('r06_cold_read_');
    addTearDown(() => dir.delete(recursive: true));
    final original = ConversationStore(dir);
    await original.addPending('retained', 'original request');
    await original.updateState('retained', 'completed', answerText: 'original answer');
    final cold = ConversationStore(dir);
    final first = cold.load();
    await cold.load();
    expect(cold.turns.single.taskId, 'retained');
    await cold.prepareAdmission('new-local', 'new-request', 'a different request');
    await first;
    final disk = ConversationStore(dir);
    await disk.load();
    expect(disk.turns.map((t) => t.taskId), ['retained', 'new-local']);
  });

  test('failed cold read does not mark history loaded', () async {
    final dir = await Directory.systemTemp.createTemp('r06_failed_read_');
    addTearDown(() => dir.delete(recursive: true));
    final file = File('${dir.path}/ncfed_conversation.json');
    await file.writeAsString('not json');
    final store = ConversationStore(dir);
    await expectLater(store.load(), throwsFormatException);
    await file.writeAsString(jsonEncode([
      ConversationTurn(taskId: 'retained', requestText: 'original', submittedAt: DateTime.utc(2026)).toJson(),
    ]));
    await store.load();
    expect(store.turns.single.taskId, 'retained');
  });

  test('native external source survives cold load; model prose and malformed fields supply none', () async {
    final dir = await Directory.systemTemp.createTemp('r06_sources_');
    addTearDown(() => dir.delete(recursive: true));
    final update = TaskUpdate.fromAskResult({'task_id':'task-177','state':'completed','output_text':'model claims peer-b',
      'external_sources':[{'peer':'peer-a','kind':'tool','request_id':'request-a','task_id':null,'trust':'remote-untrusted'}]});
    final before = ConversationStore(dir);
    await before.addPending('task-177','ask external peer');
    await before.updateState('task-177','completed',answerText:update.outputText,externalSources:update.externalSources);
    final after = ConversationStore(dir); await after.load();
    expect(after.turns.single.externalSources.single.peer,'peer-a');
    expect(after.turns.single.externalSources.single.requestId,'request-a');
    expect(ExternalSource.parse([{'peer':'peer-b','kind':'tool','request_id':'forged','trust':'local'}]),isEmpty);
    expect(ExternalSource.parse(List.filled(17,update.externalSources.single.toJson())),isEmpty);
    expect(TaskUpdate.fromAskResult({'task_id':'old','state':'completed','output_text':'from peer-b'}).externalSources,isEmpty);
  });
  test('appended turns persist across a simulated app restart (T011)', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_conv_test_');
    addTearDown(() => dir.delete(recursive: true));

    final storeBeforeRestart = ConversationStore(dir);
    await storeBeforeRestart.addPending('task-1', 'check BGP on core routers');
    await storeBeforeRestart.updateState('task-1', 'completed', answerText: 'All healthy.');
    expect(storeBeforeRestart.turns, hasLength(1));

    final storeAfterRestart = ConversationStore(dir);
    expect(storeAfterRestart.turns, isEmpty); // not loaded yet
    await storeAfterRestart.load();
    expect(storeAfterRestart.turns, hasLength(1));
    expect(storeAfterRestart.turns.single.requestText, 'check BGP on core routers');
    expect(storeAfterRestart.turns.single.answerText, 'All healthy.');
    expect(storeAfterRestart.turns.single.state, 'completed');
  });

  test('a stray late update never flips an already-terminal turn (cancel-after-completion race)',
      () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_conv_test_');
    addTearDown(() => dir.delete(recursive: true));

    final store = ConversationStore(dir);
    await store.addPending('task-2', 'fast request');
    await store.updateState('task-2', 'completed', answerText: 'done already');
    await store.updateState('task-2', 'cancelled'); // arrives late, after completion

    expect(store.turns.single.state, 'completed');
    expect(store.turns.single.answerText, 'done already');
  });

  test('clear() deletes finished turns, the persisted file, and their photos',
      () async {
    // Previously this added two *pending* turns and asserted clear() removed
    // them both -- encoding the reported bug (in-flight requests destroyed) as
    // the expected contract. Turns are marked terminal first so the test
    // exercises what clearing history is actually for.
    final dir = await Directory.systemTemp.createTemp('ncfed_conv_test_');
    addTearDown(() => dir.delete(recursive: true));

    final store = ConversationStore(dir);
    await store.addPending('task-3', 'no photo here');
    await store.addPending('task-4', 'has a photo', photoBytes: [1, 2, 3]);
    final photoPath = store.turns.last.photoPath!;
    expect(await File(photoPath).exists(), isTrue);
    await store.updateState('task-3', 'completed', answerText: 'done');
    await store.updateState('task-4', 'completed', answerText: 'done');

    await store.clear();

    expect(store.turns, isEmpty);
    expect(await File(photoPath).exists(), isFalse);
    expect(await File('${dir.path}/ncfed_conversation.json').exists(), isFalse);

    // A fresh store over the same directory sees nothing either -- clear()
    // really did remove the persisted file, not just the in-memory list.
    final reloaded = ConversationStore(dir);
    await reloaded.load();
    expect(reloaded.turns, isEmpty);
  });

  test("clear() keeps an in-flight turn's photo on disk", () async {
    // A preserved turn still renders in the UI, so deleting its photo would
    // leave a broken '[Photo unavailable]' tile attached to a live request.
    final dir = await Directory.systemTemp.createTemp('ncfed_conv_photo_keep_');
    addTearDown(() => dir.delete(recursive: true));

    final store = ConversationStore(dir);
    await store.addPending('finished', 'old', photoBytes: [9, 9]);
    final goneP = store.turns.last.photoPath!;
    await store.updateState('finished', 'completed', answerText: 'a');
    await store.addPending('inflight', 'current', photoBytes: [1, 2, 3]);
    final keptP = store.turns.last.photoPath!;

    await store.clear();

    expect(await File(goneP).exists(), isFalse, reason: 'finished photo removed');
    expect(await File(keptP).exists(), isTrue, reason: 'in-flight photo retained');
    expect(store.turns.single.photoPath, keptP);
  });

  group('acknowledge/delete/unreadCount/origin (073/FR-008/FR-012/FR-013/FR-016)', () {
    late Directory dir;
    setUp(() async => dir = await Directory.systemTemp.createTemp('ncfed_conv_ack_test_'));
    tearDown(() => dir.delete(recursive: true));

    test('a completed turn is unread; a still-in-progress turn is not (nothing to acknowledge yet)',
        () async {
      final store = ConversationStore(dir);
      await store.addPending('task-1', 'q1');
      await store.updateState('task-1', 'completed', answerText: 'a1');
      await store.addPending('task-2', 'q2'); // stays pending

      expect(store.unreadCount, 1);
    });

    test('acknowledge clears unread state but keeps the turn visible', () async {
      final store = ConversationStore(dir);
      await store.addPending('task-1', 'q1');
      await store.updateState('task-1', 'completed', answerText: 'a1');

      await store.acknowledge('task-1');

      expect(store.unreadCount, 0);
      expect(store.turns, hasLength(1));
      expect(store.turns.single.acknowledged, isTrue);
    });

    test('acknowledge persists across a simulated restart', () async {
      final store = ConversationStore(dir);
      await store.addPending('task-1', 'q1');
      await store.updateState('task-1', 'completed', answerText: 'a1');
      await store.acknowledge('task-1');

      final reloaded = ConversationStore(dir);
      await reloaded.load();
      expect(reloaded.unreadCount, 0);
      expect(reloaded.turns.single.acknowledged, isTrue);
    });

    test('delete permanently removes the turn and its photo', () async {
      final store = ConversationStore(dir);
      await store.addPending('task-1', 'q1', photoBytes: [1, 2, 3]);
      final photoPath = store.turns.single.photoPath!;
      await store.updateState('task-1', 'completed', answerText: 'a1');

      await store.delete('task-1');

      expect(store.turns, isEmpty);
      expect(await File(photoPath).exists(), isFalse);

      final reloaded = ConversationStore(dir);
      await reloaded.load();
      expect(reloaded.turns, isEmpty);
    });

    test('onCompleted fires exactly once, the moment a turn transitions into completed', () async {
      final store = ConversationStore(dir);
      final completed = <String>[];
      store.onCompleted = (turn) => completed.add(turn.taskId);
      await store.addPending('task-1', 'q1');

      await store.updateState('task-1', 'working');
      expect(completed, isEmpty); // not completed yet

      await store.updateState('task-1', 'completed', answerText: 'a1');
      expect(completed, ['task-1']);

      // A stray late update after completion must not fire onCompleted again.
      await store.updateState('task-1', 'cancelled');
      expect(completed, ['task-1']);
    });

    test('addPending defaults origin to "phone"; the watch relay can pass "watch" (FR-016)',
        () async {
      final store = ConversationStore(dir);
      await store.addPending('task-1', 'from phone');
      await store.addPending('task-2', 'from watch', origin: 'watch');

      expect(store.turns[0].origin, 'phone');
      expect(store.turns[1].origin, 'watch');
    });

    test('addPending accepts origin "siri", and it round-trips through toJson/fromJson '
        'unchanged, exactly as "watch" already does (spec 111 FR-011, research.md R5)', () async {
      final store = ConversationStore(dir);
      await store.addPending('task-3', 'asked via Siri', origin: 'siri');

      expect(store.turns.single.origin, 'siri');

      final reloaded = ConversationStore(dir);
      await reloaded.load();
      expect(reloaded.turns.single.origin, 'siri');
    });

    test('a turn written before this feature shipped (no acknowledged/origin keys) defaults to '
        'acknowledged=true and origin="phone" (research D5)', () async {
      final file = File('${dir.path}/ncfed_conversation.json');
      await file.writeAsString(jsonEncode([
        {
          'task_id': 'old-task',
          'request_text': 'pre-existing question',
          'answer_text': 'pre-existing answer',
          'state': 'completed',
          'submitted_at': DateTime.utc(2026, 1, 1).toIso8601String(),
          'photo_path': null,
          // deliberately no 'acknowledged'/'origin' keys
        }
      ]));

      final store = ConversationStore(dir);
      await store.load();

      expect(store.unreadCount, 0);
      expect(store.turns.single.acknowledged, isTrue);
      expect(store.turns.single.origin, 'phone');
    });
  });
}
