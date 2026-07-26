import 'dart:async';

import 'edge_client.dart' show isRevokedByBorder;

/// Ports `_in2n_member_dialer`'s exact backoff bounds (`bgp-daemon-v2.py`,
/// research D4) to Dart: there is no missing Python reconnect capability to
/// build here, only a port, since Dart and Python code cannot literally be
/// shared (D4). Drives any `dial()` callback that produces a connection of
/// type `T` (or throws); this class knows nothing about WebSockets, NCFED,
/// or `EdgeClient` — it is the same generic bounded-retry shape whether
/// wired to `EdgeClient.enroll` or `EdgeClient.reconnect` (US1/US3), and is
/// directly testable (T034) without a real connection type at all.
///
/// Faithfully replicates a subtlety in the original: `_in2n_member_dialer`
/// doubles `backoff` *before* sleeping on it each failed attempt (the log
/// line reports the pre-doubling value, but `asyncio.sleep(backoff)` runs
/// after the reassignment) — so the FIRST retry after a failure actually
/// waits 10s, not `initialBackoff` (5s); the sequence on repeated failure is
/// 10s, 20s, 40s, 60s, 60s... `initialBackoff` is what a freshly-reset
/// counter starts at before its first doubling, matching the source exactly.
class ReconnectSupervisor<T> {
  static const initialBackoff = Duration(seconds: 5);
  static const maxBackoff = Duration(seconds: 60);
  static const healthyCheckInterval = Duration(seconds: 10);

  final Future<T> Function() dial;
  final void Function(T connection) onConnected;
  final Future<void> Function(Duration duration) _sleep;

  Duration _backoff = initialBackoff;
  bool _stopped = false;
  bool _connected;

  /// Called instead of retrying when a dial fails in a way that retrying can
  /// never fix — currently only a Border revocation (`-32023`). Without this
  /// the loop treated revocation as a transient error and re-dialled a dead
  /// enrollment forever, at a 60s ceiling, with the operator seeing nothing but
  /// a permanent spinner.
  final void Function()? onUnrecoverable;

  ReconnectSupervisor({
    required this.dial,
    required this.onConnected,
    this.onUnrecoverable,
    Future<void> Function(Duration duration)? sleep,
    bool initiallyConnected = false,
  })  : _sleep = sleep ?? Future.delayed,
        _connected = initiallyConnected;

  /// The backoff duration the next failed dial would wait before retrying
  /// (T034 asserts this stays within [initialBackoff, maxBackoff]).
  Duration get currentBackoff => _backoff;
  bool get isConnected => _connected;

  /// Runs the permanent retry loop. Call `stop()` (e.g. on explicit
  /// unenrollment) to end it cleanly — `run()`'s Future then completes.
  Future<void> run() async {
    while (!_stopped) {
      if (!_connected) {
        try {
          final client = await dial();
          _connected = true;
          _backoff = initialBackoff; // reset on success (T034)
          onConnected(client);
        } catch (e) {
          if (isRevokedByBorder(e)) {
            // Terminal: this identity is gone. Stop the loop and hand control
            // back so the app can return to enrollment.
            _stopped = true;
            onUnrecoverable?.call();
            return;
          }
          final doubled = _backoff * 2;
          _backoff = doubled > maxBackoff ? maxBackoff : doubled;
        }
      }
      await _sleep(_connected ? healthyCheckInterval : _backoff);
    }
  }

  /// The owner calls this when the active connection drops (e.g. from
  /// `EdgeClient.isClosed` turning true) so the next loop iteration re-dials.
  void notifyDisconnected() {
    _connected = false;
  }

  void stop() {
    _stopped = true;
  }
}
