import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/capability_registration.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';

class _RecordingEdgeRpcSource implements EdgeRpcSource {
  final List<(String method, Map<String, dynamic> params)> calls = [];

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return {'registered': true};
  }
}

void main() {
  test('register() sends all currently-enabled capabilities', () async {
    final source = _RecordingEdgeRpcSource();
    final caps = CapabilityRegistration(source);

    await caps.register();

    expect(source.calls, hasLength(1));
    expect(source.calls.single.$1, 'n2n/edge/register_capabilities');
    final sent = Set.from(source.calls.single.$2['capabilities'] as List);
    expect(sent, kAllCaptureCapabilities.toSet());
  });

  test('toggling a capture type off and re-registering sends the updated (shorter) list', () async {
    final source = _RecordingEdgeRpcSource();
    final caps = CapabilityRegistration(source);

    await caps.setEnabled('audio.record', false);

    expect(source.calls, hasLength(1));
    final sent = Set.from(source.calls.single.$2['capabilities'] as List);
    expect(sent, {'camera.capture', 'camera.record_video'});
    expect(caps.enabled.contains('audio.record'), isFalse);
  });

  test('toggling a capture type back on restores it', () async {
    final source = _RecordingEdgeRpcSource();
    final caps = CapabilityRegistration(source, initiallyEnabled: {'camera.capture'});

    await caps.setEnabled('audio.record', true);

    final sent = Set.from(source.calls.single.$2['capabilities'] as List);
    expect(sent, {'camera.capture', 'audio.record'});
  });
}
