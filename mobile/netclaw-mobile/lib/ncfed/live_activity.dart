import 'package:flutter/services.dart';

/// Bridges to `LiveActivityBridge.swift` for the Lock Screen Live Activity
/// (099/FR-017/FR-018). Best-effort like push registration (`_tryRegisterPush`)
/// -- Android has no equivalent and there's no platform implementation there,
/// so a failure here must never crash or block anything else; the approval
/// itself works fully with or without this.
class LiveActivity {
  static const _channel = MethodChannel('ca.automateyournetwork.netclaw/live_activity');

  Future<void> start({required int approvalId, required String targetName}) async {
    try {
      await _channel.invokeMethod('start', {'approvalId': approvalId, 'targetName': targetName});
    } catch (_) {
      // No Live Activity support on this platform/OS version -- nothing to do.
    }
  }

  Future<void> end() async {
    try {
      await _channel.invokeMethod('end');
    } catch (_) {}
  }
}
