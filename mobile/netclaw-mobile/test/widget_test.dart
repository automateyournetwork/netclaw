import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/main.dart';

void main() {
  // mobile_scanner has no test-environment implementation at all -- without
  // these, EnrollmentScreen's MobileScanner throws MissingPluginException
  // from an unawaited() Future the instant it mounts, which flutter_test
  // treats as an unrecoverable test failure even though the real app
  // handles a missing/denied camera permission just fine (verified for real
  // on-device/emulator, see mobile/netclaw-mobile/README.md). Mocking just
  // enough of its channel surface to let start() return successfully avoids
  // fighting an unawaited async error after the fact.
  const scannerMethodChannel = MethodChannel('dev.steenbakker.mobile_scanner/scanner/method');
  const scannerEventChannel = MethodChannel('dev.steenbakker.mobile_scanner/scanner/event');
  const deviceOrientationChannel =
      MethodChannel('dev.steenbakker.mobile_scanner/scanner/deviceOrientation');

  setUp(() {
    // A non-Android/iOS/macOS platform skips mobile_scanner's native
    // surface-producer/texture-registry setup entirely -- which needs a
    // real Flutter engine and can't be faked from Dart alone.
    debugDefaultTargetPlatformOverride = TargetPlatform.linux;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(scannerMethodChannel, (call) async {
      switch (call.method) {
        case 'state':
          return 1; // MobileScannerAuthorizationState.authorized
        case 'start':
          return <String, Object?>{
            'textureId': 0,
            'cameraDirection': 0,
            'numberOfCameras': 1,
            'currentTorchState': -1,
            'size': {'width': 100.0, 'height': 100.0},
          };
        default:
          return null; // stop/pause/resetScale/etc. -- nothing else is checked here
      }
    });
    for (final channel in [scannerEventChannel, deviceOrientationChannel]) {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async => null); // listen/cancel -- never emits
    }
  });

  tearDown(() {
    for (final channel in [scannerMethodChannel, scannerEventChannel, deviceOrientationChannel]) {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
    }
  });

  testWidgets('App starts on the enrollment screen when nothing is persisted',
      (WidgetTester tester) async {
    late Directory dir;
    await tester.runAsync(() async {
      dir = await Directory.systemTemp.createTemp('ncfed_widget_test_');
      await tester.pumpWidget(MaterialApp(
        home: EnrollmentGate(documentsDirectory: () async => dir),
      ));
      // _init() awaits documentsDirectory() then store.load() sequentially,
      // each a real dart:io/Future hop that needs real wall-clock time to
      // resolve even inside runAsync -- pumpAndSettle can't be used instead
      // since the loading state's CircularProgressIndicator animates
      // indefinitely. A bare pump() loop with no real delay between
      // iterations races ahead of the pending File I/O and finds `mounted`
      // already false by the time it resolves; the small real delay here
      // is what actually gives dart:io's IO thread a chance to complete.
      for (var i = 0; i < 10; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await tester.pump(const Duration(milliseconds: 20));
      }
    });
    addTearDown(() => dir.delete(recursive: true));

    expect(find.text('Scan Border QR Code'), findsOneWidget);
    // Must happen before this test function returns -- flutter_test's own
    // end-of-test invariant check runs before any tearDown()/addTearDown()
    // callback gets a chance to fire.
    debugDefaultTargetPlatformOverride = null;
  });
}
