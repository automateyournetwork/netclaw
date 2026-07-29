import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/screens/chat_screen.dart';

/// Retry, requested by a tester: "Retry button would be useful / or if you
/// click on fail it asks to retry". A failed turn was previously a dead end —
/// the only way to try again was retyping the whole request.
class _FakeRpc implements EdgeRpcSource {
  final List<(String, Map<String, dynamic>)> calls = [];
  int _n = 0;

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return {'task_id': 'retry-task-${++_n}'};
  }
}

void main() {
  late Directory dir;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('ncfed_retry');
  });

  tearDown(() async {
    if (await dir.exists()) await dir.delete(recursive: true);
  });

  /// `ConversationStore` writes real files, and `testWidgets` runs its body in a
  /// FakeAsync zone where dart:io futures never complete — so setup I/O has to
  /// go through `runAsync`.
  Future<ConversationStore> storeWithFailedTurn(WidgetTester tester) async {
    late ConversationStore store;
    await tester.runAsync(() async {
      store = ConversationStore(dir);
      await store.addPending('t-failed', 'show me the BGP table');
      await store.updateState('t-failed', 'failed', answerText: 'Border unreachable');
    });
    return store;
  }

  Future<void> pumpChat(WidgetTester tester, ConversationStore store, _FakeRpc rpc) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: ChatScreen(askClient: EdgeAskClient(rpc), store: store)),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
  }

  testWidgets('a failed turn offers a Retry action', (tester) async {
    final store = await storeWithFailedTurn(tester);
    await pumpChat(tester, store, _FakeRpc());

    expect(find.text('Border unreachable'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget,
        reason: 'a failed turn must not be a dead end');
  });

  testWidgets('Retry resends the original text as a new turn', (tester) async {
    final store = await storeWithFailedTurn(tester);
    final rpc = _FakeRpc();
    await pumpChat(tester, store, rpc);

    await tester.tap(find.text('Retry'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    final asks = rpc.calls.where((c) => c.$1 == 'n2n/edge/ask').toList();
    expect(asks, hasLength(1));
    expect(asks.single.$2, {'text': 'show me the BGP table'},
        reason: 'retry must resend the ORIGINAL request verbatim');
    expect(store.turns, hasLength(2),
        reason: 'the failed turn stays as a record; retry is a new turn');
    expect(store.turns.last.state, 'pending');
  });

  testWidgets('tapping the failed turn itself asks to retry', (tester) async {
    final store = await storeWithFailedTurn(tester);
    final rpc = _FakeRpc();
    await pumpChat(tester, store, rpc);

    // "Or if you click on fail it asks to retry" — the whole tile is tappable.
    await tester.tap(find.text('show me the BGP table'));
    await tester.pump();

    expect(find.text('Retry this request?'), findsOneWidget);

    // Scope to the dialog: the tile behind it has its own Retry button, so a
    // bare widgetWithText finder matches two and tap() refuses.
    await tester.tap(find.descendant(
      of: find.byType(AlertDialog),
      matching: find.widgetWithText(TextButton, 'Retry'),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(rpc.calls.where((c) => c.$1 == 'n2n/edge/ask'), hasLength(1));
  });

  testWidgets('dismissing the retry dialog sends nothing', (tester) async {
    final store = await storeWithFailedTurn(tester);
    final rpc = _FakeRpc();
    await pumpChat(tester, store, rpc);

    await tester.tap(find.text('show me the BGP table'));
    await tester.pump();
    await tester.tap(find.descendant(
      of: find.byType(AlertDialog),
      matching: find.widgetWithText(TextButton, 'Cancel'),
    ));
    await tester.pump();

    expect(rpc.calls, isEmpty, reason: 'declining must not resend');
    expect(store.turns, hasLength(1));
  });

  testWidgets('a completed turn offers no Retry', (tester) async {
    late ConversationStore store;
    await tester.runAsync(() async {
      store = ConversationStore(dir);
      await store.addPending('t-ok', 'ping R1');
      await store.updateState('t-ok', 'completed', answerText: 'R1 is up');
    });
    await pumpChat(tester, store, _FakeRpc());

    expect(find.text('R1 is up'), findsOneWidget);
    expect(find.text('Retry'), findsNothing,
        reason: 'retry is only for turns that did not produce an answer');
  });

  testWidgets('a cancelled turn is also retryable', (tester) async {
    late ConversationStore store;
    await tester.runAsync(() async {
      store = ConversationStore(dir);
      await store.addPending('t-cancel', 'long running thing');
      await store.updateState('t-cancel', 'cancelled');
    });
    await pumpChat(tester, store, _FakeRpc());

    expect(find.text('Cancelled'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });
}
