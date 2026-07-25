import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/screens/feed_screen.dart';

/// T032 deep-link rendering: tapping a push notification hands `FeedScreen` a
/// `highlightPushedAt`, and the matching message must be visually
/// distinguishable from the rest of the feed. Without this the
/// `NotificationDeepLink` wiring in `main.dart` would land the operator on an
/// undifferentiated list and they'd have to hunt for the message the
/// notification was about.
void main() {
  late Directory dir;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('ncfed_feed_highlight');
  });

  tearDown(() async {
    if (await dir.exists()) await dir.delete(recursive: true);
  });

  EdgeMessage msg(String content, DateTime pushedAt) => EdgeMessage(
        contentType: MessageContentType.text,
        content: content,
        designatedBy: 'agent',
        pushedAt: pushedAt,
      );

  /// The highlighted tile is the one whose Card carries a coloured border;
  /// every other tile leaves `shape` null.
  int highlightedCardCount(WidgetTester tester) => tester
      .widgetList<Card>(find.byType(Card))
      .where((c) => c.shape != null)
      .length;

  /// `MessageFeedStore` persists to real files, and `testWidgets` runs its body
  /// inside a `FakeAsync` zone where real dart:io futures never complete — so
  /// the setup I/O has to happen in `tester.runAsync`. Priming the store here
  /// also marks it loaded, which makes `FeedScreen`'s own `load()` a no-op and
  /// keeps the widget under test off the filesystem entirely.
  Future<MessageFeedStore> storeWith(
    WidgetTester tester,
    List<EdgeMessage> messages,
  ) async {
    late MessageFeedStore store;
    await tester.runAsync(() async {
      store = MessageFeedStore(dir);
      await store.load();
      for (final m in messages) {
        await store.append(m);
      }
    });
    return store;
  }

  final first = DateTime.utc(2026, 7, 25, 17, 4, 33);
  final second = DateTime.utc(2026, 7, 25, 17, 5, 12);
  final third = DateTime.utc(2026, 7, 25, 17, 6, 46);

  testWidgets('the message a notification refers to is highlighted', (tester) async {
    final store = await storeWith(tester, [
      msg('first', first),
      msg('second', second),
      msg('third', third),
    ]);

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: FeedScreen(store: store, highlightPushedAt: second)),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('second'), findsOneWidget);
    expect(highlightedCardCount(tester), 1,
        reason: 'exactly the notification target should be highlighted');
  });

  testWidgets('no highlight is drawn when the feed is opened normally', (tester) async {
    final store = await storeWith(tester, [msg('first', first), msg('second', second)]);

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: FeedScreen(store: store)),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.byType(Card), findsNWidgets(2));
    expect(highlightedCardCount(tester), 0);
  });

  testWidgets('a pushedAt that matches nothing degrades to no highlight', (tester) async {
    // A notification for a message this device never persisted (cleared feed,
    // reinstall) must not blow up or highlight an arbitrary neighbour.
    final store = await storeWith(tester, [msg('first', first)]);

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: FeedScreen(store: store, highlightPushedAt: DateTime.utc(2001)),
      ),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('first'), findsOneWidget);
    expect(highlightedCardCount(tester), 0);
  });

  testWidgets('a second notification moves the highlight (T032 didUpdateWidget)',
      (tester) async {
    final store = await storeWith(tester, [msg('first', first), msg('third', third)]);

    Widget screen(DateTime? highlight) => MaterialApp(
          home: Scaffold(body: FeedScreen(store: store, highlightPushedAt: highlight)),
        );

    await tester.pumpWidget(screen(first));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(highlightedCardCount(tester), 1);

    await tester.pumpWidget(screen(third));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(highlightedCardCount(tester), 1,
        reason: 'the highlight moves rather than accumulating');
    final highlighted = tester
        .widgetList<Card>(find.byType(Card))
        .toList()
        .indexWhere((c) => c.shape != null);
    expect(highlighted, 1, reason: 'the newer message is second in the list');
  });
}
