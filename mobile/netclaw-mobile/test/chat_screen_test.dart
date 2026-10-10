import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/screens/chat_screen.dart';
import 'package:share_plus/share_plus.dart';

/// Minimal stand-in for the wire connection `EdgeAskClient` needs — avoids
/// constructing a real `EdgeClient` (which requires an actual
/// WebSocketChannel) just to test the widget in isolation.
class _FakeEdgeRpcSource implements EdgeRpcSource {
  final Map<String, EdgeMethodHandler> handlers = {};
  Map<String, dynamic>? taskResultResponse;

  @override
  void on(String method, EdgeMethodHandler handler) {
    handlers[method] = handler;
  }

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    if (method == 'n2n/tasks/result' && taskResultResponse != null) {
      return taskResultResponse!;
    }
    return {'task_id': 'task-1', 'state': 'working'};
  }
}

/// Builds a ChatScreen wired to a store pre-seeded with one turn in `state`.
/// Real dart:io (Directory/ConversationStore) is used, so setup runs inside
/// `runAsync()` — testWidgets() runs in a fake-async zone where a plain
/// await never lets real File I/O complete.
Future<Widget> _buildChatScreen(WidgetTester tester, String state,
    {String? answerText,
    _FakeEdgeRpcSource? source,
    Future<ShareResult> Function(ShareParams)? shareAction,
    List<int>? photoBytes}) async {
  late Directory dir;
  late ConversationStore store;
  await tester.runAsync(() async {
    dir = await Directory.systemTemp.createTemp('ncfed_chat_test_');
    store = ConversationStore(dir);
    await store.addPending('task-1', 'check BGP', photoBytes: photoBytes);
    if (state != 'pending') {
      await store.updateState('task-1', state, answerText: answerText);
    }
  });
  addTearDown(() => dir.delete(recursive: true));
  return MaterialApp(
    home: Scaffold(
        body: ChatScreen(
            askClient: EdgeAskClient(source ?? _FakeEdgeRpcSource()),
            store: store,
            shareAction: shareAction)),
  );
}

/// Seeds several turns with distinct requestText/state/origin combinations,
/// for the search/filter tests (109/US6) below.
Future<Widget> _buildChatScreenWithTurns(WidgetTester tester) async {
  late Directory dir;
  late ConversationStore store;
  await tester.runAsync(() async {
    dir = await Directory.systemTemp.createTemp('ncfed_chat_search_test_');
    store = ConversationStore(dir);
    await store.addPending('task-1', 'is BGP up on the core switch');
    await store.updateState('task-1', 'completed', answerText: 'Yes, BGP is established.');
    await store.addPending('task-2', 'check interface status');
    await store.updateState('task-2', 'failed', answerText: 'Timed out.');
    await store.addPending('task-3', 'reboot the router', origin: 'watch');
    await store.updateState('task-3', 'cancelled');
  });
  addTearDown(() => dir.delete(recursive: true));
  return MaterialApp(
    home: Scaffold(body: ChatScreen(askClient: EdgeAskClient(_FakeEdgeRpcSource()), store: store)),
  );
}

void main() {
  testWidgets('an in-progress turn shows a distinct state from a completed one (T015)',
      (tester) async {
    await tester.pumpWidget(await _buildChatScreen(tester, 'pending'));
    await tester.pump();

    expect(find.text('Working…'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);
    expect(find.text('All healthy.'), findsNothing);
  });

  testWidgets('a completed turn shows its answer, not the in-progress state', (tester) async {
    await tester.pumpWidget(
        await _buildChatScreen(tester, 'completed', answerText: 'All healthy.'));
    await tester.pump();

    expect(find.text('Working…'), findsNothing);
    expect(find.text('Cancel'), findsNothing);
    expect(find.text('All healthy.'), findsOneWidget);
  });

  testWidgets('cancelling updates the turn to cancelled, not failed', (tester) async {
    await tester.pumpWidget(await _buildChatScreen(tester, 'cancelled'));
    await tester.pump();

    expect(find.text('Cancelled'), findsOneWidget);
    expect(find.text('Working…'), findsNothing);
    expect(find.textContaining('Failed'), findsNothing);
  });

  testWidgets(
      'a turn that finished while disconnected recovers via n2n/tasks/result on next load',
      (tester) async {
    // No push ever arrives on `updates` in this test -- reconciliation is
    // the ONLY path that can surface the answer, exactly like a real
    // device whose connection went stale before the Border's push landed.
    final source = _FakeEdgeRpcSource()
      ..taskResultResponse = {
        'task_id': 'task-1',
        'state': 'completed',
        'output_text': 'Recovered answer.',
        'tokens_used': 12,
      };
    await tester.pumpWidget(await _buildChatScreen(tester, 'pending', source: source));
    await tester.pump();
    await tester.pump();

    expect(find.text('Recovered answer.'), findsOneWidget);
    expect(find.text('Working…'), findsNothing);
  });

  group('answer copy/share/select/markdown (109/US2)', () {
    Future<String?> copiedText(WidgetTester tester, Future<void> Function() action) async {
      String? copied;
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        (call) async {
          if (call.method == 'Clipboard.setData') {
            copied = (call.arguments as Map)['text'] as String?;
          }
          return null;
        },
      );
      addTearDown(() =>
          tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, null));
      await action();
      return copied;
    }

    testWidgets('a completed answer is selectable', (tester) async {
      await tester.pumpWidget(
          await _buildChatScreen(tester, 'completed', answerText: 'All healthy.'));
      await tester.pump();

      expect(find.byType(SelectableText), findsOneWidget);
    });

    testWidgets('the overflow menu Copy action copies the full answer', (tester) async {
      await tester.pumpWidget(
          await _buildChatScreen(tester, 'completed', answerText: 'All healthy.'));
      await tester.pump();

      final copied = await copiedText(tester, () async {
        await tester.tap(find.byTooltip('Answer actions'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Copy answer'));
        await tester.pumpAndSettle();
      });

      expect(copied, 'All healthy.');
      expect(find.text('Answer copied'), findsOneWidget);
    });

    testWidgets('long-pressing the answer opens the identical menu as the overflow button',
        (tester) async {
      await tester.pumpWidget(
          await _buildChatScreen(tester, 'completed', answerText: 'All healthy.'));
      await tester.pump();

      await tester.longPress(find.text('All healthy.'));
      await tester.pumpAndSettle();

      expect(find.text('Copy answer'), findsOneWidget);
      expect(find.text('Copy question + answer'), findsOneWidget);
      expect(find.text('Share'), findsOneWidget);
    });

    testWidgets('"Copy question + answer" copies both, question first', (tester) async {
      await tester.pumpWidget(
          await _buildChatScreen(tester, 'completed', answerText: 'All healthy.'));
      await tester.pump();

      final copied = await copiedText(tester, () async {
        await tester.tap(find.byTooltip('Answer actions'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Copy question + answer'));
        await tester.pumpAndSettle();
      });

      expect(copied, 'check BGP\n\nAll healthy.');
    });

    testWidgets('the Share action is wired through the injected shareAction', (tester) async {
      ShareParams? shared;
      await tester.pumpWidget(await _buildChatScreen(
        tester,
        'completed',
        answerText: 'All healthy.',
        shareAction: (params) async {
          shared = params;
          return ShareResult('', ShareResultStatus.success);
        },
      ));
      await tester.pump();

      await tester.tap(find.byTooltip('Answer actions'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Share'));
      await tester.pumpAndSettle();

      expect(shared?.text, 'All healthy.');
    });

    testWidgets('a fenced-block answer renders via Markdown; bare CLI output stays preformatted',
        (tester) async {
      await tester.pumpWidget(await _buildChatScreen(tester, 'completed',
          answerText: 'result:\n```\ninterface up\n```'));
      await tester.pump();

      expect(find.byType(SelectableText), findsWidgets); // fenced block still selectable
      expect(find.textContaining('interface up'), findsOneWidget);

      await tester.pumpWidget(await _buildChatScreen(tester, 'completed',
          answerText: 'interface # note\n * bullet\nsnake_case=1'));
      await tester.pump();

      // Bare CLI output with no fence/table row renders as plain preformatted
      // SelectableText, unmangled.
      expect(find.text('interface # note\n * bullet\nsnake_case=1'), findsOneWidget);
    });

    testWidgets('a pending/working turn shows no answer body at all -- "Working…" instead',
        (tester) async {
      // 109/FR-006 (Clarifications, 2026-08-14): non-terminal turns never
      // reach Markdown classification in the first place -- chat_screen.dart
      // shows the in-progress row, not AnswerBody, until a turn is terminal.
      await tester.pumpWidget(await _buildChatScreen(tester, 'pending'));
      await tester.pump();

      expect(find.text('Working…'), findsOneWidget);
      expect(find.byType(SelectableText), findsNothing);
    });
  });

  group('search and filter (109/US6)', () {
    testWidgets('typing a query narrows the list live', (tester) async {
      await tester.pumpWidget(await _buildChatScreenWithTurns(tester));
      await tester.pump();

      expect(find.text('is BGP up on the core switch'), findsOneWidget);
      expect(find.text('check interface status'), findsOneWidget);
      expect(find.text('reboot the router'), findsOneWidget);

      await tester.enterText(find.byType(TextField).first, 'BGP');
      await tester.pump();

      expect(find.text('is BGP up on the core switch'), findsOneWidget);
      expect(find.text('check interface status'), findsNothing);
      expect(find.text('reboot the router'), findsNothing);
    });

    testWidgets('clearing the query restores the full list', (tester) async {
      await tester.pumpWidget(await _buildChatScreenWithTurns(tester));
      await tester.pump();

      final searchField = find.byType(TextField).first;
      await tester.enterText(searchField, 'BGP');
      await tester.pump();
      await tester.enterText(searchField, '');
      await tester.pump();

      expect(find.text('is BGP up on the core switch'), findsOneWidget);
      expect(find.text('check interface status'), findsOneWidget);
      expect(find.text('reboot the router'), findsOneWidget);
    });

    testWidgets('a state filter chip composes with an active text query', (tester) async {
      await tester.pumpWidget(await _buildChatScreenWithTurns(tester));
      await tester.pump();

      await tester.enterText(find.byType(TextField).first, 'interface');
      await tester.pump();
      await tester.tap(find.widgetWithText(FilterChip, 'failed'));
      await tester.pump();

      expect(find.text('check interface status'), findsOneWidget);

      // Same query, but require a state that this turn does NOT have.
      await tester.tap(find.widgetWithText(FilterChip, 'failed')); // deselect
      await tester.tap(find.widgetWithText(FilterChip, 'cancelled'));
      await tester.pump();

      expect(find.text('check interface status'), findsNothing);
      expect(find.text('No matching turns.'), findsOneWidget);
    });

    testWidgets('an origin filter chip narrows to matching turns', (tester) async {
      await tester.pumpWidget(await _buildChatScreenWithTurns(tester));
      await tester.pump();

      await tester.tap(find.widgetWithText(FilterChip, 'watch'));
      await tester.pump();

      expect(find.text('reboot the router'), findsOneWidget);
      expect(find.text('is BGP up on the core switch'), findsNothing);
      expect(find.text('check interface status'), findsNothing);
    });

    testWidgets('a query matching nothing shows an explicit empty state', (tester) async {
      await tester.pumpWidget(await _buildChatScreenWithTurns(tester));
      await tester.pump();

      await tester.enterText(find.byType(TextField).first, 'nonexistent');
      await tester.pump();

      expect(find.text('No matching turns.'), findsOneWidget);
    });
  });
}
