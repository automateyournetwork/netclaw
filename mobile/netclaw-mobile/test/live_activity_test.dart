import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/ncfed/live_activity.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('ca.automateyournetwork.netclaw/live_activity');

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });

  test('start() with no platform implementation never throws (best-effort)', () async {
    // No mock handler registered -- mirrors Android/no-op reality.
    await expectLater(
      LiveActivity().start(approvalId: 42, targetName: 'reboot-router'),
      completes,
    );
  });

  test('end() with no platform implementation never throws (best-effort)', () async {
    await expectLater(LiveActivity().end(), completes);
  });

  test('start() invokes the channel with the correct method and arguments', () async {
    MethodCall? received;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      received = call;
      return null;
    });

    await LiveActivity().start(approvalId: 42, targetName: 'reboot-router');

    expect(received?.method, 'start');
    expect(received?.arguments, {'approvalId': 42, 'targetName': 'reboot-router'});
  });

  test('end() invokes the channel', () async {
    MethodCall? received;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      received = call;
      return null;
    });

    await LiveActivity().end();

    expect(received?.method, 'end');
  });
}
