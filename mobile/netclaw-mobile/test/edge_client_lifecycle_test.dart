import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';

class TestSink implements WebSocketSink {
  final sent = <dynamic>[];
  final firstSend = Completer<void>();
  bool closed = false;
  bool failSend = false;
  @override
  void add(dynamic data) {
    if (failSend) throw StateError('fixture send failure');
    sent.add(jsonDecode(data as String));
    if (!firstSend.isCompleted) firstSend.complete();
  }
  @override
  Future<void> close([int? closeCode, String? closeReason]) async { closed = true; }
  @override
  Future<void> get done => Future.value();
  @override
  Future<void> addStream(Stream stream) async {}
  @override
  void addError(Object error, [StackTrace? stackTrace]) {}
}
class TestChannel implements WebSocketChannel {
  final input = StreamController<dynamic>();
  @override
  Future<void> get ready => Future<void>.value();
  @override
  final TestSink sink = TestSink();
  @override
  Stream<dynamic> get stream => input.stream;
  @override
  int? get closeCode => null;
  @override
  String? get closeReason => null;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late TestChannel channel;
  late EdgeClient client;
  setUp(() { channel = TestChannel(); client = EdgeClient.forTesting(channel); });
  tearDown(() async { await client.close(); await channel.input.close(); });

  test('valid replies complete the actual client request', () async {
    final result = client.call('show', {});
    final id = channel.sink.sent.single['id'];
    channel.input.add(jsonEncode({'id': id, 'result': {'status': 'ok'}}));
    expect(await result, {'status': 'ok'});
  });
  test('send failure closes client and rejects subsequent work promptly', () async {
    channel.sink.failSend = true;
    await expectLater(client.call('show', {}), throwsA(isA<EdgeClientException>()));
    expect(client.isClosed, isTrue);
    await expectLater(client.call('again', {}), throwsA(isA<EdgeClientException>()));
  });
  test('explicit close resolves pending requests without reconnect notification', () async {
    var notifications = 0;
    client.onDisconnected = () { notifications++; };
    final expectation = expectLater(client.call('show', {}), throwsA(isA<EdgeClientException>()));
    await client.close();
    await expectation;
    expect(channel.sink.closed, isTrue);
    expect(notifications, 0);
  });
  for (final message in ['invalid-json', '[]', '{"id":"phone:1","result":3}', '{"method":42}']) {
    test('malformed message fails pending work: $message', () async {
      final expectation = expectLater(client.call('show', {}), throwsA(isA<EdgeClientException>()));
      channel.input.add(message);
      await expectation;
      expect(client.isClosed, isTrue);
      expect(channel.sink.closed, isTrue);
    });
  }
  test('handler failure returns sanitized RPC error without unhandled future', () async {
    client.on('broken', (_) => throw StateError('private fixture detail'));
    channel.input.add(jsonEncode({'id': 'peer:1', 'method': 'broken', 'params': {}}));
    await channel.sink.firstSend.future.timeout(const Duration(seconds: 5));
    expect(channel.sink.sent.single['error']['code'], -32603);
    expect(jsonEncode(channel.sink.sent), isNot(contains('private fixture detail')));
    expect(client.isClosed, isFalse);
  });
  test('timeout does not poison later requests', () async {
    await expectLater(client.call('slow', {}, timeout: const Duration(milliseconds: 1)), throwsA(isA<EdgeClientException>()));
    final result = client.call('next', {});
    channel.input.add(jsonEncode({'id': channel.sink.sent.last['id'], 'result': {'ok': true}}));
    expect(await result, {'ok': true});
  });
}
