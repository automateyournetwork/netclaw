import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/heartbeat.dart';

class _RecordingMethodSource implements EdgeMethodSource {
  final _handlers = <String, EdgeMethodHandler>{};

  @override
  void on(String method, EdgeMethodHandler handler) {
    _handlers[method] = handler;
  }

  Future<Map<String, dynamic>> invoke(String method) async {
    final handler = _handlers[method];
    if (handler == null) throw StateError('no handler registered for $method');
    return await handler(const {});
  }
}

void main() {
  test('wireHeartbeat answers both n2n/edge/heartbeat and n2n/edge/self_status', () async {
    final source = _RecordingMethodSource();
    wireHeartbeat(source);

    // Without this, the Border's periodic heartbeat call finds no handler
    // and silently times out every interval -- the device gets marked
    // unreachable/live:false even while its connection is perfectly
    // healthy (confirmed against a real production Border, 068 polish).
    final heartbeatReply = await source.invoke('n2n/edge/heartbeat');
    expect(heartbeatReply, isA<Map<String, dynamic>>());

    final statusReply = await source.invoke('n2n/edge/self_status');
    expect(statusReply['platform'], isNotEmpty);
  });
}
