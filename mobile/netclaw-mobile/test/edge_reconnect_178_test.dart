import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_qr_payload.dart';
import 'package:web_socket_channel/io.dart';
import 'edge_client_lifecycle_test.dart' show TestChannel;

const payload = EnrollmentQrPayload(
  borderHost: 'localhost',
  borderPort: 9443,
  clawDomain: 'localhost',
  enrollmentToken: '',
);

class DelayedIdentity extends EdgeIdentity {
  final started = Completer<void>();
  final signature = Completer<Uint8List>();
  @override
  Future<Uint8List> sign(Uint8List data) {
    started.complete();
    return signature.future;
  }
}

void main() {
  test(
    'failed real WebSocket handshake is handled without an unobserved ready error',
    () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final serving = server.listen((request) async {
        request.response.statusCode = HttpStatus.forbidden;
        await request.response.close();
      });
      final channel = IOWebSocketChannel.connect(
        'ws://127.0.0.1:${server.port}',
      );
      final client = EdgeClient.forTesting(channel);
      await expectLater(
        client.call('must-not-send', {}),
        throwsA(isA<EdgeClientException>()),
      );
      expect(client.isClosed, isTrue);
      await client.close();
      await serving.cancel();
      await server.close(force: true);
    },
  );
  test(
    'close during old-listener cancellation fences replacement channel',
    () async {
      final old = TestChannel(), replacement = TestChannel();
      final cancelStarted = Completer<void>(), finishCancel = Completer<void>();
      old.input.onCancel = () {
        cancelStarted.complete();
        return finishCancel.future;
      };
      final client = EdgeClient.forTesting(old, dial: (_) => replacement);
      final outcome = expectLater(
        client.reconnectInPlace(
          payload,
          memberId: 'risk/device',
          keyFingerprint: 'a' * 64,
        ),
        throwsA(isA<EdgeClientException>()),
      );
      await cancelStarted.future;
      final closed = client.close();
      finishCancel.complete();
      await outcome;
      await closed;
      expect(client.isClosed, isTrue);
      expect(replacement.sink.closed, isTrue);
      expect(replacement.sink.sent, isEmpty);
      await old.input.close();
      unawaited(replacement.input.close());
    },
  );
  test(
    'late native signature after close never sends hello or revives channel',
    () async {
      final old = TestChannel(), replacement = TestChannel();
      final identity = DelayedIdentity();
      final client = EdgeClient.forTesting(
        old,
        identity: identity,
        dial: (_) => replacement,
      );
      final outcome = expectLater(
        client.reconnectInPlace(
          payload,
          memberId: 'risk/device',
          keyFingerprint: 'a' * 64,
        ),
        throwsA(isA<EdgeClientException>()),
      );
      await Future<void>.delayed(Duration.zero);
      replacement.input.add(
        jsonEncode({
          'method': 'n2n/edge/challenge',
          'params': {'nonce': '01'},
        }),
      );
      await identity.started.future;
      await client.close();
      identity.signature.complete(Uint8List.fromList([1]));
      await outcome;
      expect(client.isClosed, isTrue);
      expect(replacement.sink.closed, isTrue);
      expect(replacement.sink.sent, isEmpty);
      await old.input.close();
      unawaited(replacement.input.close());
    },
  );
}
