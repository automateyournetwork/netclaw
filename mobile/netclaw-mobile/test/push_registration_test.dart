import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/push_registration.dart';
import 'package:netclaw_mobile/screens/settings_screen.dart';

void main() {
  group('pushPlatformFor', () {
    test('iOS registers as apns', () {
      expect(pushPlatformFor(TargetPlatform.iOS), 'apns');
    });

    test('Android registers as fcm', () {
      expect(pushPlatformFor(TargetPlatform.android), 'fcm');
    });
  });

  group('classifyPushError', () {
    // The distinction that matters: an unconfigured build is expected and
    // benign, a configured-but-broken one is a defect. These used to be
    // indistinguishable — both vanished into one swallowed catch.
    test('a missing default Firebase app is "not configured", not a failure', () {
      expect(
        classifyPushError(
          Exception('[core/no-app] No Firebase App "[DEFAULT]" has been created'),
        ),
        PushStatus.notConfigured,
      );
    });

    test('a missing GoogleService-Info.plist is "not configured"', () {
      expect(
        classifyPushError(
          Exception('Could not locate configuration file: GoogleService-Info.plist'),
        ),
        PushStatus.notConfigured,
      );
    });

    test('a missing google-services.json is "not configured"', () {
      expect(
        classifyPushError(
          Exception('google-services.json is missing from module root'),
        ),
        PushStatus.notConfigured,
      );
    });

    test('classification is case-insensitive', () {
      expect(
        classifyPushError(Exception('CORE/NOT-INITIALIZED')),
        PushStatus.notConfigured,
      );
    });

    test('an unrecognised error is a real failure, not silently excused', () {
      expect(
        classifyPushError(Exception('SERVICE_NOT_AVAILABLE')),
        PushStatus.failed,
      );
    });

    test('a network error while registering is a real failure', () {
      expect(
        classifyPushError(Exception('Connection reset by peer')),
        PushStatus.failed,
      );
    });
  });

  group('describePushStatus', () {
    test('every status has a distinct, non-empty explanation', () {
      final titles = <String>{};
      for (final status in PushStatus.values) {
        final described = describePushStatus(status);
        expect(described.title, isNotEmpty, reason: '$status has no title');
        expect(described.detail, isNotEmpty, reason: '$status has no detail');
        titles.add(described.title);
      }
      expect(titles.length, PushStatus.values.length);
    });

    test('a real failure tells the operator it is a bug, not a setting', () {
      expect(describePushStatus(PushStatus.failed).detail, contains('bug'));
    });

    test('an unconfigured build explains answers only arrive while open', () {
      expect(
        describePushStatus(PushStatus.notConfigured).detail,
        contains('app is open'),
      );
    });
  });
}
