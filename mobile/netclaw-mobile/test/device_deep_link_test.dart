import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/device_deep_link.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';

class _RecordingEdgeRpcSource implements EdgeRpcSource {
  final List<(String method, Map<String, dynamic> params)> calls = [];

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return {'task_id': 'task-device-1'};
  }
}

void main() {
  group('parseDeviceDeepLink', () {
    test('parses a well-formed netclaw://device/<id> link', () {
      expect(parseDeviceDeepLink('netclaw://device/switch-42'), 'switch-42');
    });

    test('rejects a different scheme', () {
      expect(parseDeviceDeepLink('https://device/switch-42'), isNull);
    });

    test('rejects a different host', () {
      expect(parseDeviceDeepLink('netclaw://member/switch-42'), isNull);
    });

    test('rejects a missing id', () {
      expect(parseDeviceDeepLink('netclaw://device/'), isNull);
    });

    test('rejects garbage that is not even a URI shape', () {
      expect(parseDeviceDeepLink('not a link at all'), isNull);
    });
  });

  test('deviceStatusRequestText produces the exact templated request text', () {
    expect(deviceStatusRequestText('switch-42'),
        'What is the current status of device switch-42?');
  });

  group('DeviceDeepLinkHandler', () {
    test('a known-shape identifier produces the exact templated request', () async {
      final source = _RecordingEdgeRpcSource();
      final handler = DeviceDeepLinkHandler(EdgeAskClient(source));

      final taskId = await handler.handle('netclaw://device/switch-42');

      expect(taskId, 'task-device-1');
      expect(source.calls, hasLength(1));
      expect(source.calls.single.$1, 'n2n/edge/ask');
      expect(source.calls.single.$2,
          {'text': 'What is the current status of device switch-42?'});
    });

    test('a non-deep-link string never reaches n2n/edge/ask at all', () async {
      final source = _RecordingEdgeRpcSource();
      final handler = DeviceDeepLinkHandler(EdgeAskClient(source));

      final taskId = await handler.handle('just some random QR content');

      expect(taskId, isNull);
      expect(source.calls, isEmpty);
    });

    // Closes T023's "no separate unknown-device client-side error path"
    // check (research D8): handle() for a WELL-FORMED but nonexistent
    // device still calls n2n/edge/ask normally -- there is no
    // isDeviceKnown()-style guard anywhere in this class to special-case.
    // "Unknown device" is entirely the agent-turn failure path US1/T010
    // already covers, on the Border side.
    test('a well-formed but unverifiable device id still reaches n2n/edge/ask', () async {
      final source = _RecordingEdgeRpcSource();
      final handler = DeviceDeepLinkHandler(EdgeAskClient(source));

      final taskId = await handler.handle('netclaw://device/does-not-exist-anywhere');

      expect(taskId, 'task-device-1'); // the fake source always "succeeds" --
      expect(source.calls, hasLength(1)); // the point is that the call was made at all
    });
  });
}
