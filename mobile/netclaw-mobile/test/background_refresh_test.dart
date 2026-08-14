import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/background_refresh.dart';

void main() {
  group('summarizeBackgroundRefresh (FR-013: ONE notification, not one per item)', () {
    test('a single new message', () {
      expect(summarizeBackgroundRefresh(1, 0), '1 new message');
    });

    test('several new messages', () {
      expect(summarizeBackgroundRefresh(3, 0), '3 new messages');
    });

    test('a single approval request', () {
      expect(summarizeBackgroundRefresh(0, 1), '1 approval request');
    });

    test('several approval requests', () {
      expect(summarizeBackgroundRefresh(0, 2), '2 approval requests');
    });

    test('messages and approvals together combine into one summary', () {
      expect(summarizeBackgroundRefresh(2, 1), '2 new messages, 1 approval request');
    });

    test('nothing arrived produces an empty summary (caller must not post in this case)', () {
      expect(summarizeBackgroundRefresh(0, 0), '');
    });
  });
}
