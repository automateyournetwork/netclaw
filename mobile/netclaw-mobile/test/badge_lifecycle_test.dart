import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/ncfed/badge_lifecycle.dart';

/// 099/FR-002 -- `_HomeShellState` can't be constructed here (its
/// `EdgeClient` dependency only exposes real-I/O static factories, which is
/// why no existing test in this app mounts `HomeShell`), so this exercises
/// the one conditional this fix adds directly: recompute on `resumed`, and
/// on nothing else.
void main() {
  test('recomputes on resumed', () async {
    var calls = 0;
    final observer = BadgeLifecycleObserver(() async {
      calls++;
    });

    observer.didChangeAppLifecycleState(AppLifecycleState.resumed);
    // The callback is fire-and-forget (matches `_recomputeBadge`'s own
    // call site, which is never awaited from a lifecycle callback), so
    // give its Future a turn to complete.
    await Future<void>.delayed(Duration.zero);

    expect(calls, 1);
  });

  test('does not recompute on any other lifecycle state', () async {
    var calls = 0;
    final observer = BadgeLifecycleObserver(() async {
      calls++;
    });

    for (final state in [
      AppLifecycleState.inactive,
      AppLifecycleState.paused,
      AppLifecycleState.detached,
      AppLifecycleState.hidden,
    ]) {
      observer.didChangeAppLifecycleState(state);
    }
    await Future<void>.delayed(Duration.zero);

    expect(calls, 0);
  });

  test('recomputes again on a second resume', () async {
    var calls = 0;
    final observer = BadgeLifecycleObserver(() async {
      calls++;
    });

    observer.didChangeAppLifecycleState(AppLifecycleState.resumed);
    observer.didChangeAppLifecycleState(AppLifecycleState.paused);
    observer.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await Future<void>.delayed(Duration.zero);

    expect(calls, 2);
  });
}
