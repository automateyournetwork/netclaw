import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/ncfed/dashboard_data.dart';
import 'package:netclaw_mobile/screens/dashboard_screen.dart';

void main() {
  Future<void> pump(WidgetTester tester, DashboardSnapshot snapshot) => tester.pumpWidget(
      MaterialApp(home: Scaffold(body: DashboardScreen(snapshot: snapshot))));

  testWidgets('not-enrolled shows a clear empty state, not blank or an error',
      (tester) async {
    await pump(
      tester,
      const DashboardSnapshot(
        connected: false,
        identity: FederationIdentitySnapshot(enrolled: false, memberId: '', clawDomain: ''),
        unreadPending: UnreadPendingSnapshot(unreadFeed: 0, unreadChat: 0, pendingApprovals: 0),
      ),
    );

    expect(find.text('Not yet enrolled'), findsOneWidget);
  });

  testWidgets('connected shows healthy state, identity, and counts', (tester) async {
    await pump(
      tester,
      const DashboardSnapshot(
        connected: true,
        identity: FederationIdentitySnapshot(
          enrolled: true,
          memberId: 'member-123',
          clawDomain: 'border.home.arpa',
        ),
        unreadPending: UnreadPendingSnapshot(unreadFeed: 2, unreadChat: 1, pendingApprovals: 4),
      ),
    );

    expect(find.text('Connected to Border'), findsOneWidget);
    expect(find.text('border.home.arpa'), findsOneWidget);
    expect(find.text('member-123'), findsOneWidget);
    expect(find.text('3'), findsOneWidget); // totalUnread = 2 + 1
    expect(find.text('4'), findsOneWidget); // pendingApprovals
  });

  testWidgets('disconnected shows the degraded state, not a false healthy one',
      (tester) async {
    await pump(
      tester,
      const DashboardSnapshot(
        connected: false,
        identity: FederationIdentitySnapshot(
          enrolled: true,
          memberId: 'member-123',
          clawDomain: 'border.home.arpa',
        ),
        unreadPending: UnreadPendingSnapshot(unreadFeed: 0, unreadChat: 0, pendingApprovals: 0),
      ),
    );

    expect(find.text('Connected to Border'), findsNothing);
    expect(find.text('Reconnecting…'), findsOneWidget);
  });
}
