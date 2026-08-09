import 'package:flutter/widgets.dart';

/// Decides when a foreground/background lifecycle transition should trigger
/// a badge reconciliation (099/FR-002). Extracted out of `_HomeShellState`
/// for the same reason `confirmAndResolve` was pulled out of
/// `approvals_screen.dart` in 073 -- `_HomeShellState` can't be constructed
/// in a test without a real `EdgeClient`/WebSocket connection (its
/// constructor is private outside `edge_client.dart`, and no existing test
/// in this app mounts `HomeShell` for exactly that reason), so the one
/// piece of new conditional logic this fix adds needs a home a test can
/// reach directly.
class BadgeLifecycleObserver extends WidgetsBindingObserver {
  BadgeLifecycleObserver(this._recompute);

  final Future<void> Function() _recompute;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _recompute();
    }
  }
}
