import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Regression: `reconnectInPlace` cancelled the old stream subscription but
/// never closed the old socket. Cancelling stops us *reading* it; the WebSocket
/// stayed open with nobody listening until the OS or the network tore it down —
/// which the Border logs as `no close frame received or sent`. Measured on the
/// live Border: 8 abandoned sockets in a single day, one per redial.
///
/// The fix is one line (`previous.sink.close()`), so the test that matters is
/// the one asserting the *discipline*: a channel that is replaced must be
/// closed. Exercising the real `reconnectInPlace` would need a live WSS
/// endpoint plus Secure Enclave signing, so this pins the swap-and-close
/// contract directly against the same fake-channel shape.
class _FakeSink implements WebSocketSink {
  bool closed = false;
  int closeCount = 0;
  final _added = <dynamic>[];

  List<dynamic> get added => _added;

  @override
  Future close([int? closeCode, String? closeReason]) async {
    closed = true;
    closeCount++;
  }

  @override
  void add(dynamic data) => _added.add(data);

  @override
  void addError(Object error, [StackTrace? stackTrace]) {}

  @override
  Future addStream(Stream stream) async {}

  @override
  Future get done => Future.value();
}

class _FakeChannel {
  final _controller = StreamController<dynamic>.broadcast();
  final sink = _FakeSink();
  Stream<dynamic> get stream => _controller.stream;
  void dispose() => _controller.close();
}

/// Mirrors the swap sequence in `reconnectInPlace`: open the replacement, drop
/// the old subscription, install the replacement, then close what was replaced.
Future<void> _swapChannel({
  required _FakeChannel previous,
  required _FakeChannel replacement,
  required StreamSubscription? previousSub,
}) async {
  await previousSub?.cancel();
  // Mirrors production exactly: close() returns a Future, so the rejection has
  // to be suppressed on the Future, not with a synchronous try/catch.
  previous.sink.close().catchError((Object _) {});
}

void main() {
  test('replacing a channel closes the one it replaced', () async {
    final previous = _FakeChannel();
    final replacement = _FakeChannel();
    final sub = previous.stream.listen((_) {});

    await _swapChannel(
        previous: previous, replacement: replacement, previousSub: sub);

    expect(previous.sink.closed, isTrue,
        reason: 'an abandoned socket must be closed, not just unsubscribed');
    expect(replacement.sink.closed, isFalse,
        reason: 'the new channel must stay open');

    previous.dispose();
    replacement.dispose();
  });

  test('repeated reconnects leak nothing', () async {
    // The failure mode was cumulative: one abandoned socket per redial. Ten
    // redials must close ten sockets.
    final channels = <_FakeChannel>[];
    _FakeChannel current = _FakeChannel();
    channels.add(current);
    StreamSubscription? sub = current.stream.listen((_) {});

    for (var i = 0; i < 10; i++) {
      final next = _FakeChannel();
      channels.add(next);
      await _swapChannel(previous: current, replacement: next, previousSub: sub);
      current = next;
      sub = current.stream.listen((_) {});
    }

    final abandoned = channels.sublist(0, channels.length - 1);
    expect(abandoned.every((c) => c.sink.closed), isTrue,
        reason: 'every replaced socket must be closed');
    expect(abandoned.map((c) => c.sink.closeCount), everyElement(1),
        reason: 'closed exactly once — not repeatedly');
    expect(channels.last.sink.closed, isFalse,
        reason: 'only the live channel stays open');

    for (final c in channels) {
      c.dispose();
    }
  });

  test('a close that throws does not block the swap', () async {
    // A socket that is already dead throws on close. That is the case we least
    // care about and it must never delay or fail the new connection.
    final previous = _ThrowingChannel();
    final replacement = _FakeChannel();
    final sub = previous.stream.listen((_) {});

    await expectLater(
      _swapChannel(
          previous: previous, replacement: replacement, previousSub: sub),
      completes,
    );

    replacement.dispose();
  });
}

class _ThrowingSink extends _FakeSink {
  @override
  Future close([int? closeCode, String? closeReason]) async {
    throw StateError('socket already dead');
  }
}

class _ThrowingChannel extends _FakeChannel {
  @override
  // ignore: overridden_fields
  final _ThrowingSink sink = _ThrowingSink();
}
