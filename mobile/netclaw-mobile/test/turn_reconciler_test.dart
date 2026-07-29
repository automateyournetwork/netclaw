import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/turn_reconciler.dart';

/// Recovery for an answer that finished while this device had no live channel.
///
/// Two bugs made this the common case rather than the edge case:
///   * the Border only pushed `ask_result` to the exact channel object that had
///     submitted the request, so ANY reconnect during the turn meant no push at
///     all (a real iPhone reconnected 4x during one 2-minute turn);
///   * reconciliation lived in `ChatScreen.initState`, so it stopped running
///     entirely once the tabs moved to an IndexedStack.
///
/// Result: the work completed, the answer sat on the Border, and the phone spun
/// on "Working" indefinitely.
class _FakeRpc implements EdgeRpcSource {
  /// taskId -> the `n2n/tasks/result` payload to answer with.
  final Map<String, Map<String, dynamic>> results;
  final List<String> resultCalls = [];
  int failNextN;

  _FakeRpc(this.results, {this.failNextN = 0});

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    if (method == 'n2n/tasks/result') {
      final id = params['task_id'] as String;
      resultCalls.add(id);
      if (failNextN > 0) {
        failNextN--;
        throw EdgeClientException('connection_error', 'still disconnected');
      }
      return results[id] ?? {'task_id': id, 'state': 'pending'};
    }
    if (method == 'n2n/edge/ask') return {'task_id': 'new-task'};
    return {};
  }
}

void main() {
  late Directory dir;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('ncfed_reconcile');
  });

  tearDown(() async {
    if (await dir.exists()) await dir.delete(recursive: true);
  });

  Future<ConversationStore> storeWith(List<(String, String)> turns) async {
    final store = ConversationStore(dir);
    for (final (taskId, text) in turns) {
      await store.addPending(taskId, text);
    }
    return store;
  }

  test('recovers an answer that completed while disconnected', () async {
    final store = await storeWith([('t1', 'check R1')]);
    final rpc = _FakeRpc({
      't1': {
        'task_id': 't1',
        'state': 'completed',
        'output_text': 'R1 is up, all interfaces nominal',
      }
    });

    final recovered = await reconcileStaleTurns(EdgeAskClient(rpc), store);

    expect(recovered, 1);
    final turn = store.turns.single;
    expect(turn.state, 'completed');
    expect(turn.answerText, 'R1 is up, all interfaces nominal',
        reason: 'the answer sitting on the Border must reach the phone');
  });

  test('a failed task recovers its REASON, not a blank failure', () async {
    // TaskManager.run stores {"error": ...} on exception, so the explanation
    // lives under `error`. Dropping it left the phone showing a bare "Failed".
    final store = await storeWith([('t1', 'slow thing')]);
    final rpc = _FakeRpc({
      't1': {
        'task_id': 't1',
        'state': 'failed',
        'error': 'agent turn timed out',
      }
    });

    await reconcileStaleTurns(EdgeAskClient(rpc), store);

    expect(store.turns.single.state, 'failed');
    expect(store.turns.single.answerText, 'agent turn timed out');
  });

  test('a still-running turn is left alone for the next pass', () async {
    final store = await storeWith([('t1', 'long thing')]);
    final rpc = _FakeRpc({'t1': {'task_id': 't1', 'state': 'working'}});

    final recovered = await reconcileStaleTurns(EdgeAskClient(rpc), store);

    expect(recovered, 1, reason: 'working is a real state transition');
    expect(store.turns.single.state, 'working');
  });

  test('terminal turns are never re-queried', () async {
    final store = await storeWith([('t1', 'done already')]);
    await store.updateState('t1', 'completed', answerText: 'answer');
    final rpc = _FakeRpc({});

    await reconcileStaleTurns(EdgeAskClient(rpc), store);

    expect(rpc.resultCalls, isEmpty,
        reason: 'only pending/working turns need reconciling');
  });

  test('an unreachable Border is not an error, and retries next time', () async {
    final store = await storeWith([('t1', 'check R1')]);
    final rpc = _FakeRpc({
      't1': {'task_id': 't1', 'state': 'completed', 'output_text': 'late answer'}
    }, failNextN: 1);

    // First pass: still disconnected. Must not throw, must not corrupt state.
    final first = await reconcileStaleTurns(EdgeAskClient(rpc), store);
    expect(first, 0);
    expect(store.turns.single.state, 'pending',
        reason: 'a failed fetch must leave the turn recoverable');

    // Second pass (i.e. the next reconnect) succeeds.
    final second = await reconcileStaleTurns(EdgeAskClient(rpc), store);
    expect(second, 1);
    expect(store.turns.single.answerText, 'late answer');
  });

  test('is idempotent — a second pass changes nothing and re-queries nothing',
      () async {
    final store = await storeWith([('t1', 'check R1')]);
    final rpc = _FakeRpc({
      't1': {'task_id': 't1', 'state': 'completed', 'output_text': 'answer'}
    });

    await reconcileStaleTurns(EdgeAskClient(rpc), store);
    final callsAfterFirst = rpc.resultCalls.length;
    await reconcileStaleTurns(EdgeAskClient(rpc), store);

    expect(rpc.resultCalls.length, callsAfterFirst,
        reason: 'the recovered turn is terminal and must not be re-fetched');
    expect(store.turns.single.answerText, 'answer');
  });

  test('recovers several stranded turns in one pass', () async {
    final store = await storeWith([
      ('t1', 'first'),
      ('t2', 'second'),
      ('t3', 'third'),
    ]);
    final rpc = _FakeRpc({
      't1': {'task_id': 't1', 'state': 'completed', 'output_text': 'a1'},
      't2': {'task_id': 't2', 'state': 'failed', 'error': 'boom'},
      // t3 deliberately absent -> answered 'pending', stays stale
    });

    final recovered = await reconcileStaleTurns(EdgeAskClient(rpc), store);

    expect(recovered, 2);
    final byId = {for (final t in store.turns) t.taskId: t};
    expect(byId['t1']!.answerText, 'a1');
    expect(byId['t2']!.answerText, 'boom');
    expect(byId['t3']!.state, 'pending');
  });

  test('onChanged fires only when something was actually recovered', () async {
    final store = await storeWith([('t1', 'x')]);
    var calls = 0;

    await reconcileStaleTurns(
        EdgeAskClient(_FakeRpc({})), store, onChanged: () => calls++);
    expect(calls, 0, reason: 'nothing recovered -> no repaint');

    await reconcileStaleTurns(
        EdgeAskClient(_FakeRpc({
          't1': {'task_id': 't1', 'state': 'completed', 'output_text': 'ok'}
        })),
        store,
        onChanged: () => calls++);
    expect(calls, 1);
  });
}
