import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/enrollment_flow.dart';

/// Every edge member enrolled with `display_name: null`, because
/// `attemptEnrollmentFromQr` is the only caller of `EdgeClient.enroll` and never
/// passed one — even though both already supported it. Owner attribution then
/// had to be guessed from enrollment timestamps, which caused a real misroute:
/// a message intended for one operator's phone was delivered to another's
/// because the mesh carried no way to tell the two apart.
///
/// The label is derived rather than prompted so it can never be skipped or left
/// blank; the manual-enrollment screen can override it.
void main() {
  group('defaultDeviceLabel', () {
    test('is never empty', () {
      expect(defaultDeviceLabel('risk/1785078347014').trim(), isNotEmpty);
    });

    test('distinguishes two devices on the same platform', () {
      // The whole point: two Androids must not collapse to one indistinguishable
      // label, which is what made the misroute possible.
      final a = defaultDeviceLabel('risk/1785077389894');
      final b = defaultDeviceLabel('risk/1785078347014');
      expect(a, isNot(equals(b)));
    });

    test('carries the memberId tail so it maps back to the mesh identity', () {
      final label = defaultDeviceLabel('risk/1785078347014');
      expect(label, contains('7014'),
          reason: 'an operator must be able to tie the label to the member row');
    });

    test('names the platform in human terms', () {
      final label = defaultDeviceLabel('risk/1785078347014');
      final expected = switch (Platform.operatingSystem) {
        'ios' => 'iPhone',
        'android' => 'Android',
        final other => other,
      };
      expect(label, contains(expected));
    });

    test('handles a short memberId without throwing', () {
      // Defensive: memberId is normally `risk/<millis>`, but the label must not
      // be the thing that breaks enrollment if that ever changes.
      for (final id in ['', 'a', 'ab', 'abc', 'abcd']) {
        expect(() => defaultDeviceLabel(id), returnsNormally);
        expect(defaultDeviceLabel(id).trim(), isNotEmpty);
      }
    });

    test('is stable for the same memberId', () {
      // Reconnect/re-enroll of the same device must not produce a new name.
      final id = 'risk/1785078347014';
      expect(defaultDeviceLabel(id), defaultDeviceLabel(id));
    });
  });
}
