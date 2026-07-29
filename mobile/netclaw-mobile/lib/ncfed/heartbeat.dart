import 'dart:io';

import 'edge_client.dart';

/// Answers the Border's `n2n/edge/heartbeat`/`n2n/edge/self_status` calls
/// (066, `_edge_heartbeat_once`/`edge_self_status`) — without this, the
/// Border's periodic heartbeat call finds no handler registered, silently
/// times out every interval, and the device is marked unreachable/`live:
/// false` even while its WebSocket connection is perfectly healthy. Neither
/// call's response body is validated by the Border beyond "did it reply at
/// all" (heartbeat) or "store whatever came back" (self_status) — this is
/// deliberately minimal, not a rich device-telemetry surface.
void wireHeartbeat(EdgeMethodSource client) {
  client.on('n2n/edge/heartbeat', (params) async => <String, dynamic>{});
  client.on('n2n/edge/self_status', (params) async => <String, dynamic>{
        'platform': Platform.operatingSystem,
      });
}
