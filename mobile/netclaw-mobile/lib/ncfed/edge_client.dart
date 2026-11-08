import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'edge_identity.dart';
import 'cluster_trust.dart';
import 'enrollment_qr_payload.dart';
import 'protected_device_descriptor.dart';

/// Raised for any NCFED-level failure: a JSON-RPC error reply, a request
/// timeout, or the underlying connection failing/closing.
class EdgeClientException implements Exception {
  final String code;
  final String message;
  final Map<String, dynamic>? data;
  EdgeClientException(this.code, this.message, {this.data});

  @override
  String toString() => 'EdgeClientException($code): $message';
}

/// -32023 is `_ERR_NOT_TRUSTED` (`internal_channel.py`) — the ONLY reply
/// that means the Border itself rejected this exact pinned key (e.g. an
/// operator explicitly removed the device), so the persisted enrollment
/// cannot currently authenticate. Retain its identity and operation references
/// for operator review; this never authorizes automatic reenrollment. Every other failure a reconnect
/// attempt can produce (`timeout`, `connection_error`, a raw socket/TLS
/// exception that never reached the Border at all) is plausibly transient
/// — a crash, a network blip, the Border restarting — and must NOT be
/// treated the same way, or a momentary outage permanently burns a working
/// enrollment (068 polish, found via a real crash-and-relaunch report).
bool isRevokedByBorder(Object error) =>
    error is EdgeClientException && error.code == '-32023';

typedef EdgeMethodHandler =
    FutureOr<Map<String, dynamic>> Function(Map<String, dynamic> params);

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
  Future<Map<String, dynamic>> call(
    String method,
    Map<String, dynamic> params, {
    Duration timeout,
  });
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
  int _connectionGeneration = 0;
  final WebSocketChannel Function(Uri)? _testDial;

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
  Map<String, dynamic> border = {};
  ProtectedDeviceDescriptor? protectedDevice;
  ClusterBinding? clusterBinding;
  String? clusterMemberId;

  Future<void> _rememberBorder(
    Map<String, dynamic> result,
    EnrollmentQrPayload payload,
  ) async {
    final generation = _connectionGeneration;
    final channel = _channel;
    final value = result['border'];
    final next = value is Map<String, dynamic> ? value : <String, dynamic>{};
    if (payload.clusterPin != null) {
      final preflight = clusterBinding;
      if (preflight == null) {
        throw const FormatException('Cluster discovery required');
      }
      final verified = await ClusterBinding.verify(
        next['cluster'],
        preflight.pin,
        origin: preflight.origin,
        installationId: payload.installationId!,
        nodeId: payload.clusterNodeId,
      );
      if (_closed ||
          generation != _connectionGeneration ||
          !identical(channel, _channel)) {
        throw StateError('Cluster reconnect was superseded');
      }
      clusterBinding = verified;
    } else if (next.containsKey('cluster')) {
      throw const FormatException('Cluster onboarding requires explicit pins');
    }
    protectedDevice = ProtectedDeviceDescriptor.fromBorder(
      next,
      payload,
      cluster: clusterBinding,
    );
    border = next;
  }

  static Future<ClusterBinding?> _clusterPreflight(
    EnrollmentQrPayload payload,
  ) async {
    if (payload.clusterPin == null) return null;
    final origin = Uri(
      scheme: 'https',
      host: payload.clawDomain,
      port: payload.borderPort,
    ).origin;
    final binding = await ClusterBinding.verify(
      await fetchClusterDescriptor(origin),
      payload.clusterPin!,
      origin: origin,
      installationId: payload.installationId!,
      nodeId: payload.clusterNodeId,
    );
    if (binding.websocketUri != payload.websocketUri || !binding.available) {
      throw const FormatException('Cluster endpoint has no current authority');
    }
    return binding;
  }

  static Future<Uint8List> _handshakeProof(
    EnrollmentQrPayload payload,
    Map<String, dynamic> challenge,
    String memberId,
    String purpose,
  ) async {
    if (payload.clusterPin == null) {
      return hexDecode(challenge['nonce'] as String);
    }
    final pin = payload.clusterPin!;
    if (challenge.length != 7 ||
        challenge['schema_version'] != 1 ||
        challenge['cluster_id'] != pin.clusterId ||
        challenge['generation'] != pin.generation ||
        challenge['node_id'] != payload.clusterNodeId ||
        challenge['installation_id'] != payload.installationId ||
        challenge['nonce'] is! String ||
        !RegExp(r'^[a-f0-9]{64}$').hasMatch(challenge['nonce']) ||
        challenge['expires_at_ms'] is! int ||
        challenge['expires_at_ms'] <= DateTime.now().millisecondsSinceEpoch ||
        challenge['expires_at_ms'] >
            DateTime.now().millisecondsSinceEpoch + 31000) {
      throw const FormatException('Cluster challenge changed');
    }
    final tokenHash = purpose == 'enroll'
        ? (await publicCrypto(
            Uint8List.fromList(utf8.encode(payload.enrollmentToken)),
          ))['sha256']
        : null;
    return Uint8List.fromList([
      ...utf8.encode('netclaw.ncfed.ha/device-proof/v1\u0000'),
      ...clusterCanonical({
        'challenge': challenge,
        'member_id': memberId,
        'purpose': purpose,
        'token_sha256': tokenHash,
      }),
    ]);
  }

  Future<Map<String, dynamic>> signedDeviceRequest(
    String method,
    Map<String, dynamic> params,
  ) async {
    final cluster = clusterBinding, device = protectedDevice;
    if (cluster == null ||
        device?.enrollmentGeneration == null ||
        clusterMemberId == null ||
        isClosed) {
      throw const FormatException('Current cluster device required');
    }
    final bytes = List.generate(16, (_) => Random.secure().nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final hex = hexEncode(Uint8List.fromList(bytes));
    final requestId =
        '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
    final proof = <String, dynamic>{
      'schema_version': 1,
      'cluster_id': cluster.pin.clusterId,
      'generation': cluster.pin.generation,
      'member_id': clusterMemberId,
      'enrollment_generation': device!.enrollmentGeneration,
      'request_id': requestId,
      'method': method,
      'params_sha256': (await publicCrypto(clusterCanonical(params)))['sha256'],
    };
    final signature = await identity.sign(
      Uint8List.fromList([
        ...utf8.encode('netclaw.ncfed.ha/device-request/v1\u0000'),
        ...clusterCanonical(proof),
      ]),
    );
    if (isClosed || clusterBinding != cluster || protectedDevice != device) {
      throw StateError('Device connection changed');
    }
    return {...proof, 'signature': hexEncode(signature)};
  }

  EdgeClient._(this._channel, this.identity, {this._testDial}) {
    _listen();
  }

  @visibleForTesting
  EdgeClient.forTesting(
    WebSocketChannel channel, {
    EdgeIdentity identity = const EdgeIdentity(),
    WebSocketChannel Function(Uri)? dial,
  }) : this._(channel, identity, testDial: dial);

  void _listen() {
    final origin = _channel;
    final generation = _connectionGeneration;
    // The channel reports dial/TLS failure through BOTH ready and its stream.
    // The stream below owns failure state; still observe ready so certificate
    // refusal does not escape as an unrelated unhandled asynchronous error.
    unawaited(origin.ready.catchError((Object _) {}));
    bool current() =>
        identical(origin, _channel) && generation == _connectionGeneration;
    debugPrint('[edge-diag] dial ${DateTime.now().toIso8601String()}');
    _sub = _channel.stream.listen(
      (raw) {
        if (!current()) return;
        try {
          _onMessage(raw);
        } catch (_) {
          _failAll('Invalid peer message');
          _channel.sink
              .close(1002, 'Invalid RPC message')
              .catchError((Object _) {});
        }
      },
      onError: (Object error) {
        if (current()) {
          _failAll('error: $error (${DateTime.now().toIso8601String()})');
        }
      },
      onDone: () {
        if (current()) {
          _failAll(
            'onDone closeCode=${origin.closeCode} closeReason=${origin.closeReason} '
            '(${DateTime.now().toIso8601String()})',
          );
        }
      },
    );
  }

  /// Registers a handler for a Border-initiated method (e.g.
  /// n2n/edge/heartbeat, n2n/edge/self_status, n2n/edge/message).
  @override
  void on(String method, EdgeMethodHandler handler) {
    _handlers[method] = handler;
  }

  void _failAll(Object error, {bool notify = true}) {
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
    if (notify) onDisconnected?.call();
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
    final generation = ++_connectionGeneration;
    final verifiedCluster = await _clusterPreflight(payload);
    if (generation != _connectionGeneration) {
      throw StateError("Reconnect superseded");
    }
    clusterBinding = verifiedCluster;
    clusterMemberId = memberId;
    final uri = payload.websocketUri;
    debugPrint(
      '[edge-diag] socket connect requested (reconnectInPlace) ${DateTime.now().toIso8601String()}',
    );
    final channel =
        _testDial?.call(uri) ??
        IOWebSocketChannel.connect(uri, pingInterval: _clientPingInterval);
    // Observe immediately, even if cancelling the prior listener is delayed.
    unawaited(channel.ready.catchError((Object _) {}));
    // Cancelling the subscription stops us READING the old socket but does not
    // close it: without the sink close below, the previous WebSocket stayed
    // open with nobody listening until the OS or the network tore it down,
    // which the Border logs as `no close frame received or sent`. Confirmed on
    // the live Border: 8 abandoned sockets in one day, each one a redial.
    final previous = _channel;
    _failAll('Connection replaced', notify: false);
    await _sub?.cancel();
    if (generation != _connectionGeneration) {
      await channel.sink.close();
      throw EdgeClientException('connection_error', 'Reconnect was superseded');
    }
    _channel = channel;
    _closed = false;
    _listen();
    // Fire-and-forget: a close that fails (socket already dead) is exactly the
    // case we don't care about, and must not delay the new connection.
    // `close()` returns a Future, so a synchronous try/catch would NOT catch a
    // rejection — that would surface as an unhandled async error precisely when
    // the old socket is already gone. Suppress on the Future itself.
    previous.sink.close().catchError((Object _) {});

    final challenge = Completer<Map<String, dynamic>>();
    _connectionWaiters.add(challenge);
    on('n2n/edge/challenge', (params) {
      if (!challenge.isCompleted) {
        challenge.complete(params);
      }
      return <String, dynamic>{};
    });
    try {
      final nonce = await challenge.future.timeout(const Duration(seconds: 10));
      final signature = await identity.sign(
        await _handshakeProof(payload, nonce, memberId, 'hello'),
      );
      if (generation != _connectionGeneration || _closed) {
        throw EdgeClientException(
          'connection_error',
          'Reconnect was superseded',
        );
      }
      final result = await call('in2n/hello', {
        'member_id': memberId,
        if (payload.installationId != null)
          'installation_id': payload.installationId,
        'key_fingerprint': keyFingerprint,
        'signature': hexEncode(signature),
      });
      if (generation != _connectionGeneration || _closed) {
        throw EdgeClientException(
          'connection_error',
          'Reconnect was superseded',
        );
      }
      await _rememberBorder(result, payload);
      enrollFingerprint = keyFingerprint;
    } catch (e) {
      if (generation == _connectionGeneration && identical(channel, _channel)) {
        _failAll(e);
        await close();
      } else {
        await channel.sink.close();
      }
      rethrow;
    } finally {
      _connectionWaiters.remove(challenge);
    }
  }

  void _onMessage(dynamic raw) {
    if (_closed) return;
    if (raw is! String || raw.length > 4 * 1024 * 1024) {
      throw const FormatException('Invalid RPC size');
    }
    final msg =
        (clusterBinding == null ? jsonDecode(raw) : clusterDecode(raw))
            as Map<String, dynamic>;
    if (msg.containsKey('method')) {
      final method = msg['method'] as String;
      final params =
          (msg['params'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      final handler = _handlers[method];
      debugPrint(
        '[edge-diag] inbound $method handler=${handler != null} '
        '${DateTime.now().toIso8601String()}',
      );
      if (handler == null) {
        return; // unknown method — silently dropped, mirrors EdgeChannel
      }
      final origin = _channel;
      Future<void>(() async {
        final id = msg['id'];
        try {
          final result = await handler(params);
          if (id != null && !_closed && identical(origin, _channel)) {
            origin.sink.add(
              jsonEncode({'jsonrpc': '2.0', 'id': id, 'result': result}),
            );
          }
        } catch (_) {
          if (id != null && !_closed && identical(origin, _channel)) {
            origin.sink.add(
              jsonEncode({
                'jsonrpc': '2.0',
                'id': id,
                'error': {'code': -32603, 'message': 'Mobile handler failed'},
              }),
            );
          }
        }
      }).catchError((Object _) => _failAll('Reply transport failed'));
    } else if (msg.containsKey('id')) {
      final completer = _pending[msg['id']];
      if (completer == null || completer.isCompleted) return;
      if (msg.containsKey('error')) {
        final err = msg['error'] as Map<String, dynamic>;
        completer.completeError(
          EdgeClientException(
            '${err['code']}',
            '${err['message']}',
            data: err['data'] is Map<String, dynamic>
                ? err['data'] as Map<String, dynamic>
                : null,
          ),
        );
      } else {
        completer.complete(
          (msg['result'] as Map<String, dynamic>?) ?? <String, dynamic>{},
        );
      }
      _pending.remove(msg['id']);
    }
  }

  @override
  Future<Map<String, dynamic>> call(
    String method,
    Map<String, dynamic> params, {
    Duration timeout = const Duration(seconds: 30),
  }) async {
    if (_closed) {
      throw EdgeClientException('connection_error', 'Connection is closed');
    }
    final encoded = jsonEncode({
      'jsonrpc': '2.0',
      'id': 'phone:${_nextId + 1}',
      'method': method,
      'params': params,
    });
    _nextId += 1;
    final id = 'phone:$_nextId';
    final completer = Completer<Map<String, dynamic>>();
    _pending[id] = completer;
    debugPrint(
      '[edge-diag] outbound $method ${DateTime.now().toIso8601String()}',
    );
    try {
      try {
        _channel.sink.add(encoded);
      } catch (_) {
        // This future has not yet acquired a listener: remove it before
        // failing the other calls so no unobserved error is created.
        _pending.remove(id);
        _failAll('Request transport failed');
        throw EdgeClientException(
          'connection_error',
          'Request transport failed',
        );
      }
      return await completer.future.timeout(
        timeout,
        onTimeout: () {
          throw EdgeClientException('timeout', '$method timed out');
        },
      );
    } finally {
      _pending.remove(id);
    }
  }

  Future<void> close() async {
    _connectionGeneration++;
    _failAll('Client closed', notify: false);
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
    final verifiedCluster = await _clusterPreflight(payload);
    final uri = payload.websocketUri;
    // Standard TLS hostname verification (against the platform's public CA
    // trust store) happens automatically here — a mismatched/untrusted
    // certificate makes this connection fail outright (research D7); no
    // custom certificate inspection code exists anywhere in this client.
    debugPrint(
      '[edge-diag] socket connect requested (enroll) ${DateTime.now().toIso8601String()}',
    );
    final channel = IOWebSocketChannel.connect(
      uri,
      pingInterval: _clientPingInterval,
    );
    final client = EdgeClient._(channel, identity);
    client.clusterBinding = verifiedCluster;
    client.clusterMemberId = memberId;

    final challenge = Completer<Map<String, dynamic>>();
    client._connectionWaiters.add(challenge);
    client.on('n2n/edge/challenge', (params) {
      if (!challenge.isCompleted) {
        challenge.complete(params);
      }
      return <String, dynamic>{};
    });
    try {
      final nonce = await challenge.future.timeout(const Duration(seconds: 10));
      final certPem = await identity.certificatePem();
      final signature = await identity.sign(
        await _handshakeProof(payload, nonce, memberId, 'enroll'),
      );
      final result = await client.call('in2n/enroll', {
        'token': payload.enrollmentToken,
        if (payload.clusterPin != null) 'client_nonce': payload.clientNonce,
        if (payload.installationId != null)
          'installation_id': payload.installationId,
        'member_id': memberId,
        'cert_pem': certPem,
        'signature': hexEncode(signature),
        'runtime_kind': runtimeKind,
        'display_name': ?displayName,
      });
      await client._rememberBorder(result, payload);
      client.enrollFingerprint = result['enroll_fingerprint'] as String?;
      return client;
    } catch (_) {
      await client.close();
      rethrow;
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
    final verifiedCluster = await _clusterPreflight(payload);
    final uri = payload.websocketUri;
    debugPrint(
      '[edge-diag] socket connect requested (reconnect) ${DateTime.now().toIso8601String()}',
    );
    final channel = IOWebSocketChannel.connect(
      uri,
      pingInterval: _clientPingInterval,
    );
    final client = EdgeClient._(channel, identity);
    client.clusterBinding = verifiedCluster;
    client.clusterMemberId = memberId;

    final challenge = Completer<Map<String, dynamic>>();
    client._connectionWaiters.add(challenge);
    client.on('n2n/edge/challenge', (params) {
      if (!challenge.isCompleted) {
        challenge.complete(params);
      }
      return <String, dynamic>{};
    });
    try {
      final nonce = await challenge.future.timeout(const Duration(seconds: 10));
      final signature = await identity.sign(
        await _handshakeProof(payload, nonce, memberId, 'hello'),
      );
      final result = await client.call('in2n/hello', {
        'member_id': memberId,
        if (payload.installationId != null)
          'installation_id': payload.installationId,
        'key_fingerprint': keyFingerprint,
        'signature': hexEncode(signature),
      });
      await client._rememberBorder(result, payload);
      client.enrollFingerprint = keyFingerprint;
      return client;
    } catch (_) {
      await client.close();
      rethrow;
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
