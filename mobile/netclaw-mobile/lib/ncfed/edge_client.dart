import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'edge_identity.dart';
import 'enrollment_qr_payload.dart';

/// Raised for any NCFED-level failure: a JSON-RPC error reply, a request
/// timeout, or the underlying connection failing/closing.
class EdgeClientException implements Exception {
  final String code;
  final String message;
  EdgeClientException(this.code, this.message);

  @override
  String toString() => 'EdgeClientException($code): $message';
}

/// -32023 is `_ERR_NOT_TRUSTED` (`internal_channel.py`) — the ONLY reply
/// that means the Border itself rejected this exact pinned key (e.g. an
/// operator explicitly removed the device), so the persisted enrollment
/// really is dead and safe to discard. Every other failure a reconnect
/// attempt can produce (`timeout`, `connection_error`, a raw socket/TLS
/// exception that never reached the Border at all) is plausibly transient
/// — a crash, a network blip, the Border restarting — and must NOT be
/// treated the same way, or a momentary outage permanently burns a working
/// enrollment (068 polish, found via a real crash-and-relaunch report).
bool isRevokedByBorder(Object error) => error is EdgeClientException && error.code == '-32023';

typedef EdgeMethodHandler = FutureOr<Map<String, dynamic>> Function(Map<String, dynamic> params);

/// Anything that can register a handler for a Border-initiated method —
/// implemented by `EdgeClient`. Lets feed/heartbeat wiring code (and its
/// tests) depend on just this narrow surface instead of the full client
/// and its real WebSocket connection.
abstract class EdgeMethodSource {
  void on(String method, EdgeMethodHandler handler);
}

/// `EdgeMethodSource` plus the ability to make outbound calls — what
/// `EdgeAskClient` (feature 067) needs. A separate, wider interface from
/// `EdgeMethodSource` so `wireMessageFeed` (which only ever registers a
/// handler) keeps depending on the narrowest surface it actually needs.
abstract class EdgeRpcSource implements EdgeMethodSource {
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout});
}

/// One connection to a NetClaw Border over the NCFED edge (WebSocket)
/// transport (feature 066). Mirrors the Border's own EdgeChannel
/// (mcp-servers/protocol-mcp/bgp/federation/edge.py) dispatch shape — whole
/// JSON-RPC 2.0 messages over `.send()`/the message stream, no byte framing
/// (a WebSocket connection already frames each message).
class EdgeClient implements EdgeRpcSource {
  /// Client-side WebSocket keepalive. `IOWebSocketChannel.connect()` sends
  /// nothing of its own by default, so an idle socket depended entirely on the
  /// Border's pings surviving the carrier/NAT path — and the client had no way
  /// to notice a half-open socket at all. Kept comfortably under the Border's
  /// 90s ping_timeout so both ends agree the connection is alive.
  ///
  /// This does NOT make a socket survive the app being backgrounded: iOS and
  /// Android both suspend the isolate, and no keepalive interval changes that.
  /// Reliable delivery to a backgrounded app needs push (see
  /// MOBILE-ONBOARDING.md); this only covers the foregrounded and
  /// idle-but-awake cases.
  static const _clientPingInterval = Duration(seconds: 20);

  WebSocketChannel _channel;
  final EdgeIdentity identity;
  int _nextId = 0;
  final _pending = <String, Completer<Map<String, dynamic>>>{};
  final _handlers = <String, EdgeMethodHandler>{};
  final _connectionWaiters = <Completer>{};
  StreamSubscription? _sub;
  bool _closed = false;

  /// True once the connection has failed/closed (including a call that
  /// timed out or errored) — the reconnect supervisor uses this, via
  /// [onDisconnected], to decide when to re-dial.
  bool get isClosed => _closed;

  /// Fires exactly once per dropped connection, right after `_failAll` — the
  /// reconnect supervisor (068 polish) hooks this instead of polling
  /// `isClosed`, so a drop is noticed immediately rather than on the next
  /// poll tick.
  void Function()? onDisconnected;

  /// The Border-computed SHA-256 fingerprint of this device's public key,
  /// returned by the `in2n/enroll` response. The caller (enrollment_screen)
  /// MUST persist this alongside `memberId` — it is required by
  /// `reconnect()`'s `in2n/hello` call, and is authoritative Border-issued
  /// data, not something this client independently re-derives from the
  /// certificate (avoids needing an X.509/DER parser in Dart).
  String? enrollFingerprint;

  EdgeClient._(this._channel, this.identity) {
    _listen();
  }

  void _listen() {
    debugPrint('[edge-diag] dial ${DateTime.now().toIso8601String()}');
    _sub = _channel.stream.listen(
      _onMessage,
      onError: (Object error) =>
          _failAll('error: $error (${DateTime.now().toIso8601String()})'),
      onDone: () => _failAll(
          'onDone closeCode=${_channel.closeCode} closeReason=${_channel.closeReason} '
          '(${DateTime.now().toIso8601String()})'),
    );
  }

  /// Registers a handler for a Border-initiated method (e.g.
  /// n2n/edge/heartbeat, n2n/edge/self_status, n2n/edge/message).
  @override
  void on(String method, EdgeMethodHandler handler) {
    _handlers[method] = handler;
  }

  void _failAll(Object error) {
    if (_closed) return;
    debugPrint('[edge-diag] failAll: $error');
    _closed = true; // the connection is no longer usable either way
    final err = EdgeClientException('connection_error', '$error');
    for (final c in _pending.values) {
      if (!c.isCompleted) c.completeError(err);
    }
    _pending.clear();
    for (final c in _connectionWaiters) {
      if (!c.isCompleted) c.completeError(err);
    }
    onDisconnected?.call();
  }

  /// Re-dials the Border and re-proves possession of the pinned key, reusing
  /// THIS SAME `EdgeClient` object — unlike the static [reconnect] factory,
  /// which builds a brand-new one at enrollment time. Every wrapper object
  /// already built around this client (`EdgeAskClient`, `ApprovalClient`,
  /// `CaptureClient`'s wired handler, `wireMessageFeed`'s registration, ...)
  /// keeps working transparently after a drop — nothing to rewire, since
  /// `_handlers` is untouched and callers hold the same object identity.
  /// Throws on failure; the caller (`ReconnectSupervisor`) is expected to
  /// catch and back off.
  Future<void> reconnectInPlace(
    EnrollmentQrPayload payload, {
    required String memberId,
    required String keyFingerprint,
  }) async {
    verifyClawDomainBeforeDial(payload);
    final uri = Uri(scheme: 'wss', host: payload.clawDomain, port: payload.borderPort);
    debugPrint('[edge-diag] socket connect requested (reconnectInPlace) ${DateTime.now().toIso8601String()}');
    final channel = IOWebSocketChannel.connect(uri, pingInterval: _clientPingInterval);
    // Cancelling the subscription stops us READING the old socket but does not
    // close it: without the sink close below, the previous WebSocket stayed
    // open with nobody listening until the OS or the network tore it down,
    // which the Border logs as `no close frame received or sent`. Confirmed on
    // the live Border: 8 abandoned sockets in one day, each one a redial.
    final previous = _channel;
    await _sub?.cancel();
    _channel = channel;
    _closed = false;
    _listen();
    // Fire-and-forget: a close that fails (socket already dead) is exactly the
    // case we don't care about, and must not delay the new connection.
    // `close()` returns a Future, so a synchronous try/catch would NOT catch a
    // rejection — that would surface as an unhandled async error precisely when
    // the old socket is already gone. Suppress on the Future itself.
    previous.sink.close().catchError((Object _) {});

    final challenge = Completer<Uint8List>();
    _connectionWaiters.add(challenge);
    on('n2n/edge/challenge', (params) {
      if (!challenge.isCompleted) {
        challenge.complete(hexDecode(params['nonce'] as String));
      }
      return <String, dynamic>{};
    });
    try {
      final nonce = await challenge.future.timeout(const Duration(seconds: 10));
      final signature = await identity.sign(nonce);
      await call('in2n/hello', {
        'member_id': memberId,
        'key_fingerprint': keyFingerprint,
        'signature': hexEncode(signature),
      });
      enrollFingerprint = keyFingerprint;
    } catch (e) {
      _failAll(e); // the redial itself failed -- let the caller's retry loop handle it
      rethrow;
    } finally {
      _connectionWaiters.remove(challenge);
    }
  }

  void _onMessage(dynamic raw) {
    final msg = jsonDecode(raw as String) as Map<String, dynamic>;
    if (msg.containsKey('method')) {
      final method = msg['method'] as String;
      final params = (msg['params'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      final handler = _handlers[method];
      debugPrint('[edge-diag] inbound $method handler=${handler != null} '
          '${DateTime.now().toIso8601String()}');
      if (handler == null) return; // unknown method — silently dropped, mirrors EdgeChannel
      Future(() async {
        final result = await handler(params);
        final id = msg['id'];
        if (id != null) {
          _channel.sink.add(jsonEncode({'jsonrpc': '2.0', 'id': id, 'result': result}));
        }
      });
    } else if (msg.containsKey('id')) {
      final completer = _pending.remove(msg['id']);
      if (completer == null || completer.isCompleted) return;
      if (msg.containsKey('error')) {
        final err = msg['error'] as Map<String, dynamic>;
        completer.completeError(EdgeClientException('${err['code']}', '${err['message']}'));
      } else {
        completer.complete((msg['result'] as Map<String, dynamic>?) ?? <String, dynamic>{});
      }
    }
  }

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) {
    _nextId += 1;
    final id = 'phone:$_nextId';
    final completer = Completer<Map<String, dynamic>>();
    _pending[id] = completer;
    debugPrint('[edge-diag] outbound $method ${DateTime.now().toIso8601String()}');
    _channel.sink.add(jsonEncode({'jsonrpc': '2.0', 'id': id, 'method': method, 'params': params}));
    return completer.future.timeout(timeout, onTimeout: () {
      _pending.remove(id);
      throw EdgeClientException('timeout', '$method timed out');
    });
  }

  Future<void> close() async {
    _closed = true;
    await _sub?.cancel();
    await _channel.sink.close();
  }

  /// Dials the Border and completes the in2n/enroll handshake (first-time
  /// enrollment). Applies D7's domain check BEFORE dialing —
  /// see verifyClawDomainBeforeDial.
  static Future<EdgeClient> enroll(
    EnrollmentQrPayload payload, {
    required String memberId,
    required EdgeIdentity identity,
    String runtimeKind = 'mobile',
    String? displayName,
  }) async {
    verifyClawDomainBeforeDial(payload);
    final uri = Uri(scheme: 'wss', host: payload.clawDomain, port: payload.borderPort);
    // Standard TLS hostname verification (against the platform's public CA
    // trust store) happens automatically here — a mismatched/untrusted
    // certificate makes this connection fail outright (research D7); no
    // custom certificate inspection code exists anywhere in this client.
    debugPrint('[edge-diag] socket connect requested (enroll) ${DateTime.now().toIso8601String()}');
    final channel = IOWebSocketChannel.connect(uri, pingInterval: _clientPingInterval);
    final client = EdgeClient._(channel, identity);

    final challenge = Completer<Uint8List>();
    client._connectionWaiters.add(challenge);
    client.on('n2n/edge/challenge', (params) {
      if (!challenge.isCompleted) {
        challenge.complete(hexDecode(params['nonce'] as String));
      }
      return <String, dynamic>{};
    });
    try {
      final nonce = await challenge.future.timeout(const Duration(seconds: 10));
      final certPem = await identity.certificatePem();
      final signature = await identity.sign(nonce);
      final result = await client.call('in2n/enroll', {
        'token': payload.enrollmentToken,
        'member_id': memberId,
        'cert_pem': certPem,
        'signature': hexEncode(signature),
        'runtime_kind': runtimeKind,
        'display_name': ?displayName,
      });
      client.enrollFingerprint = result['enroll_fingerprint'] as String?;
      return client;
    } finally {
      client._connectionWaiters.remove(challenge);
    }
  }

  /// Reconnects to an already-enrolled Border via in2n/hello (pinned-key
  /// proof, no token) — used after a dropped connection (US3). `keyFingerprint`
  /// MUST be the `enrollFingerprint` value `enroll()` returned at enrollment
  /// time and persisted by the caller — the Border, not this client, is the
  /// source of truth for what fingerprint it pinned.
  static Future<EdgeClient> reconnect(
    EnrollmentQrPayload payload, {
    required String memberId,
    required String keyFingerprint,
    required EdgeIdentity identity,
  }) async {
    verifyClawDomainBeforeDial(payload);
    final uri = Uri(scheme: 'wss', host: payload.clawDomain, port: payload.borderPort);
    debugPrint('[edge-diag] socket connect requested (reconnect) ${DateTime.now().toIso8601String()}');
    final channel = IOWebSocketChannel.connect(uri, pingInterval: _clientPingInterval);
    final client = EdgeClient._(channel, identity);

    final challenge = Completer<Uint8List>();
    client._connectionWaiters.add(challenge);
    client.on('n2n/edge/challenge', (params) {
      if (!challenge.isCompleted) {
        challenge.complete(hexDecode(params['nonce'] as String));
      }
      return <String, dynamic>{};
    });
    try {
      final nonce = await challenge.future.timeout(const Duration(seconds: 10));
      final signature = await identity.sign(nonce);
      await client.call('in2n/hello', {
        'member_id': memberId,
        'key_fingerprint': keyFingerprint,
        'signature': hexEncode(signature),
      });
      client.enrollFingerprint = keyFingerprint;
      return client;
    } finally {
      client._connectionWaiters.remove(challenge);
    }
  }
}

Uint8List hexDecode(String hex) {
  final bytes = Uint8List(hex.length ~/ 2);
  for (var i = 0; i < bytes.length; i++) {
    bytes[i] = int.parse(hex.substring(i * 2, i * 2 + 2), radix: 16);
  }
  return bytes;
}

String hexEncode(Uint8List bytes) =>
    bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
