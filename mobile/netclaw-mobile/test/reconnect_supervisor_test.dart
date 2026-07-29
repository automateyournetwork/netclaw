import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/reconnect_supervisor.dart';

void main() {
  test('backoff doubles on repeated failure, capped at 60s (T034)', () async {
    var attempt = 0;
    final sleeps = <Duration>[];
    late ReconnectSupervisor<String> supervisor;
    supervisor = ReconnectSupervisor<String>(
      dial: () async {
        attempt += 1;
        throw Exception('simulated connect failure #$attempt');
      },
      onConnected: (_) {},
      sleep: (d) async {
        sleeps.add(d);
        if (sleeps.length >= 6) supervisor.stop();
      },
    );

    await supervisor.run();

    // The source (_in2n_member_dialer) doubles `backoff` BEFORE sleeping on
    // it each failed attempt, so the first retry is 10s, not 5s — see the
    // class doc comment for the exact line-by-line trace.
    expect(sleeps, [
      const Duration(seconds: 10),
      const Duration(seconds: 20),
      const Duration(seconds: 40),
      const Duration(seconds: 60),
      const Duration(seconds: 60),
      const Duration(seconds: 60), // capped — never exceeds 60s
    ]);
  });

  test('a successful reconnect resets the backoff counter to its initial value (T034)', () async {
    var attempt = 0;
    final sleeps = <Duration>[];
    late ReconnectSupervisor<String> supervisor;
    supervisor = ReconnectSupervisor<String>(
      dial: () async {
        attempt += 1;
        if (attempt <= 3) throw Exception('simulated failure #$attempt');
        return 'connected';
      },
      onConnected: (_) {},
      sleep: (d) async {
        sleeps.add(d);
        if (sleeps.length >= 5) supervisor.stop();
      },
    );

    await supervisor.run();

    // 3 failures: 10s, 20s, 40s; then success resets to initialBackoff and
    // the healthy check interval (10s) is used while connected.
    expect(sleeps[0], const Duration(seconds: 10));
    expect(sleeps[1], const Duration(seconds: 20));
    expect(sleeps[2], const Duration(seconds: 40));
    expect(supervisor.currentBackoff, ReconnectSupervisor.initialBackoff);
    expect(supervisor.isConnected, isTrue);
  });

  test('stop() ends the retry loop cleanly', () async {
    final supervisor = ReconnectSupervisor<String>(
      dial: () async => throw Exception('always fails'),
      onConnected: (_) {},
      sleep: (_) async {},
    );
    final future = supervisor.run();
    supervisor.stop();
    await future.timeout(const Duration(seconds: 1));
  });
}
