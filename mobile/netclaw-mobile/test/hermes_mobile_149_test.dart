import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/dashboard_data.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/turn_reconciler.dart';
import 'package:netclaw_mobile/screens/dashboard_screen.dart';

class Rpc implements EdgeRpcSource {
  final Future<Map<String, dynamic>> Function(String, Map<String, dynamic>) invoke;
  Rpc(this.invoke);
  @override
  void on(String method, EdgeMethodHandler handler) {}
  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) => invoke(method, params);
}

void main() {
  late Directory dir;
  setUp(() async => dir = await Directory.systemTemp.createTemp('hermes-mobile149'));
  tearDown(() async => dir.delete(recursive: true));

  test('persist before send, recover lost receipt by request ID without replay', () async {
    final store = ConversationStore(dir);
    var sends = 0;
    String? request;
    final rpc = Rpc((method, params) async {
      if (method == 'n2n/edge/ask') {
        sends++;
        request = params['request_id'] as String;
        final persisted = ConversationStore(dir);
        await persisted.load();
        expect(persisted.turns.single.requestId, request);
        expect(params['origin'], 'voice');
        throw TimeoutException('receipt lost');
      }
      expect(method, 'n2n/tasks/result');
      expect(params, {'request_id': request});
      return {'task_id': 'owned-task', 'state': 'completed', 'output_text': 'Done'};
    });
    final ask = EdgeAskClient(rpc, store: store);
    await ask.ask('check', origin: 'voice');
    expect(store.turns.single.state, 'outcome_unknown');
    final reloaded = ConversationStore(dir);
    await reloaded.load();
    final reconnect = EdgeAskClient(rpc, store: reloaded);
    await reconcileStaleTurns(reconnect, reloaded);
    expect(reloaded.turns.single.taskId, 'owned-task');
    expect(reloaded.turns.single.state, 'completed');
    expect(reloaded.turns.single.answerText, 'Done');
    expect(sends, 1);
  });

  test('manual Watch lookup recovers provisional receipt and its rebound alias', () async {
    final store = ConversationStore(dir);
    await store.prepareAdmission('request-r', 'r', 'work');
    final reads = <Map<String, dynamic>>[];
    final ask = EdgeAskClient(Rpc((method, params) async {
      expect(method, 'n2n/tasks/result');
      reads.add(params);
      return {'task_id': 'owned-task', 'state': 'completed', 'output_text': 'Done'};
    }), store: store);
    expect((await ask.result('request-r')).state, TaskState.completed);
    expect((await ask.result('request-r')).state, TaskState.completed);
    expect(reads, [{'request_id': 'r'}, {'task_id': 'owned-task'}]);
  });

  test('canonical unknown survives legacy failed projection and nullable usage', () {
    final update = TaskUpdate.fromAskResult({'task_id': 't', 'state': 'failed', 'outcome_state': 'outcome_unknown', 'tokens_used': null});
    expect(update.state, TaskState.outcomeUnknown);
    expect(update.tokensUsed, isNull);
    expect(update.state.explanation, contains('do not resend'));
    expect(parseTaskState('interrupted'), TaskState.interrupted);
    expect(parseTaskState('future-state').wireName, 'outcome_unknown');
  });

  test('requested cancellation stays unresolved; confirmed result may reconcile', () async {
    final store = ConversationStore(dir);
    await store.addPending('t', 'work');
    final ask = EdgeAskClient(Rpc((method, _) async => method.endsWith('/cancel')
        ? {'cancel_requested': true, 'cancellation_confirmed': false}
        : {'task_id': 't', 'state': 'cancelled'}), store: store);
    expect(await ask.cancel('t'), isFalse);
    expect(store.turns.single.state, 'cancellation_requested');
    await store.updateState('t', 'working');
    expect(store.turns.single.state, 'cancellation_requested');
    await store.clear();
    expect(store.turns, hasLength(1));
    await reconcileStaleTurns(ask, store);
    expect(store.turns.single.state, 'cancelled');
  });

  test('legacy peer with lost task reports uncertainty and is never resubmitted', () async {
    final store = ConversationStore(dir);
    await store.prepareAdmission('request-r', 'r', 'work');
    var reads = 0;
    final ask = EdgeAskClient(Rpc((method, _) async {
      expect(method, 'n2n/tasks/result');
      reads++;
      throw EdgeClientException('-32602', 'unsupported request lookup');
    }), store: store);
    await reconcileStaleTurns(ask, store);
    await reconcileStaleTurns(ask, store);
    expect(reads, 2);
    expect(store.turns.single.state, 'outcome_unknown');
  });

  for (final type in ['hermes', 'openclaw', 'unknown']) {
    testWidgets('summary shows $type without guessing metadata', (tester) async {
      final snapshot = DashboardSnapshot(connected: true,
        identity: const FederationIdentitySnapshot(enrolled: true, memberId: 'phone', clawDomain: 'border.claw'),
        unreadPending: const UnreadPendingSnapshot(unreadFeed: 0, unreadChat: 0, pendingApprovals: 0),
        border: type == 'unknown' ? {} : {'harness': {'type': type, 'version': '1'}, 'model': 'fixture', 'capabilities': {'text': true, 'voice_text': true, 'attachments': type != 'hermes'}},
      );
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: DashboardScreen(snapshot: snapshot, onOpenFeed: () {}, onOpenChat: () {}, onOpenApprovals: () {}))));
      expect(find.text('Border type: $type'), findsOneWidget);
      if (type == 'unknown') expect(find.textContaining('Model: unknown'), findsOneWidget);
      if (type == 'hermes') expect(find.textContaining('Photo/video: unavailable'), findsOneWidget);
    });
  }
}
