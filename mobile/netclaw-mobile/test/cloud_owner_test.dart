import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/screens/cloud_owner_screen.dart';

const installation = '11111111-1111-4111-8111-111111111111';
final profile = CloudProfile('https://border.example.test', installation);
final token = 'a' * 43, digest = 'b' * 64;

class MemoryOwnerStore extends CloudOwnerStore {
  final values = <String, String>{};
  final reads = <String>[];
  bool failReferences = false;
  String? pauseWritePrefix;
  bool pauseProofOnly = false;
  Completer<void>? writeStarted, releaseWrite;
  @override
  Future<String?> read(String key) async {
    reads.add(key);
    return values[key];
  }

  @override
  Future<void> write(String key, String? value) async {
    if (pauseWritePrefix != null &&
        key.startsWith(pauseWritePrefix!) &&
        (!pauseProofOnly || value?.contains('"not_submitted":true') == true)) {
      writeStarted!.complete();
      await releaseWrite!.future;
    }
    if (failReferences && key.startsWith('reference.')) {
      throw StateError('storage unavailable');
    }
    if (value == null) {
      values.remove(key);
    } else {
      values[key] = value;
    }
  }
}

class FixtureTransport implements OwnerTransport {
  final calls =
      <({String method, Uri uri, Map<String, String> headers, Json? body})>[];
  Json? operation;
  int effects = 0;
  bool wrongIdentity = false,
      badCookie = false,
      dropPrepare = false,
      dropDecision = false,
      revoked = false,
      refusePrepare = false;
  bool dropBeforeDecision = false, dropBeforePrepare = false;
  bool openLab = false, wrongReviewPrincipal = false;
  Json? accessOverride;
  bool refuseLab = false;
  Completer<void>? pauseRuntime;
  Json get labPrincipal => {
    'issuer': 'open-lab',
    'subject': installation,
    'display_name': 'Unauthenticated lab operator',
    'roles': ['lab-operator'],
  };
  Completer<void>? pausePrepare;
  Json get session => {
    'authenticated': true,
    'installation_id': installation,
    'csrf_token': token,
    'expires_ms': DateTime.now().millisecondsSinceEpoch + 600000,
    'principal': {
      'issuer': 'local',
      'subject': 'owner1',
      'display_name': 'Fixture owner',
      'roles': ['owner'],
    },
  };
  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  ) async {
    calls.add((method: method, uri: uri, headers: {...headers}, body: body));
    if (uri.path == '/api/runtime') {
      if (pauseRuntime != null) await pauseRuntime!.future;
      return OwnerResponse(200, {
        'installationId': wrongIdentity ? 'wrong' : installation,
        'role': 'border',
        if (openLab || accessOverride != null)
          'access':
              accessOverride ?? {'mode': 'open-lab', 'principal': labPrincipal},
        'capabilities': {
          'protectedProfile': true,
          'protectedOperations': true,
          'protectedProduction': true,
        },
      });
    }
    if (openLab && refuseLab) {
      return OwnerResponse(401, {'code': 'access_refused'});
    }
    if (uri.path == '/api/hud/owner/session') {
      if (revoked) return OwnerResponse(401, {'code': 'invalid_session'});
      if (method == 'DELETE') {
        return OwnerResponse(200, {'authenticated': false});
      }
      return OwnerResponse(
        200,
        session,
        cookies: method == 'POST'
            ? [
                '__Host-nc_owner_$installation=$token; Path=/; HttpOnly; SameSite=Strict${badCookie ? '' : '; Secure'}',
              ]
            : [],
      );
    }
    if (uri.path.endsWith('/catalog')) {
      return OwnerResponse(200, {
        'revision': digest,
        'members': [
          {
            'member': {'member_id': 'risk/member'},
            'model_profiles': [
              {
                'profile_id': 'sonnet',
                'provider': 'anthropic',
                'model': 'sonnet-4.6',
              },
            ],
            'tools': [
              {
                'tool': 'subnet_calculator',
                'device_ref': 'subnet',
                'arguments': {'cidr': '192.0.2.0/26'},
              },
            ],
          },
        ],
      });
    }
    if (method == 'POST' && uri.path == '/api/hud/operations') {
      if (dropBeforePrepare) throw const CloudOwnerError('transport_uncertain');
      if (refusePrepare) {
        return OwnerResponse(403, {'admission': 'not_submitted'});
      }
      operation = {
        'operation_id': 'operation1',
        'client_nonce': body!['client_nonce'],
        'revision': 1,
        'state': 'review_pending',
        'review_digest': digest,
        'review': {
          'principal': openLab && !wrongReviewPrincipal
              ? labPrincipal
              : session['principal'],
          'border': {'installation_id': installation},
          'member': {'member_id': 'risk/member'},
          'model_profile': {'provider': 'anthropic', 'model': 'sonnet-4.6'},
          'tool_call': {
            'tool': 'subnet_calculator',
            'arguments': {'cidr': '192.0.2.0/26'},
          },
          'limits': {
            'expires_at_ms': DateTime.now().millisecondsSinceEpoch + 300000,
          },
          'change_request_ref': null,
        },
        'allowed_actions': ['approve', 'deny'],
        'attempt_count': 0,
        'reconciliation_required': false,
        'may_have_executed': false,
        'result': null,
      };
      if (pausePrepare != null) await pausePrepare!.future;
      if (dropPrepare) throw const CloudOwnerError('transport_uncertain');
      return OwnerResponse(200, operation!);
    }
    if (uri.path.endsWith('/decision')) {
      if (dropBeforeDecision) {
        throw const CloudOwnerError('transport_uncertain');
      }
      expect(body!['revision'], operation!['revision']);
      expect(body['review_digest'], operation!['review_digest']);
      effects++;
      operation = {
        ...operation!,
        'revision': 2,
        'state': 'completed',
        'allowed_actions': ['reconcile'],
        'attempt_count': 1,
        'may_have_executed': true,
        'result': {
          'verified': true,
          'durable_ack': true,
          'ack_delivery_pending': false,
          'digest': digest,
          'evidence': {
            'operation_id': 'operation1',
            'audit_refs': ['fixture-audit'],
            'output': {
              'tool': {
                'output': {'network_address': '192.0.2.0'},
              },
            },
          },
        },
      };
      if (dropDecision) throw const CloudOwnerError('transport_uncertain');
      return OwnerResponse(200, operation!);
    }
    if (operation != null) return OwnerResponse(200, operation!);
    return OwnerResponse(404, {'code': 'operation_not_found'});
  }
}

Future<CloudOwnerClient> connected(
  MemoryOwnerStore store,
  FixtureTransport transport,
) async {
  final client = CloudOwnerClient(profile, store: store, transport: transport);
  await client.initialize();
  await client.login(token);
  return client;
}

void main() {
  test(
    'canonical HTTPS profiles refuse insecure URLs, paths and authority tricks',
    () {
      for (final origin in [
        'http://border.test',
        'https://border.test/',
        'https://user@border.test',
        'https://border.test?q=x',
        'https://border.test#x',
        'https://border.test/path',
      ]) {
        expect(
          () => CloudProfile(origin, installation),
          throwsA(isA<CloudOwnerError>()),
        );
      }
      expect(
        () => CloudProfile(profile.origin, 'not-an-installation'),
        throwsA(isA<CloudOwnerError>()),
      );
    },
  );
  test('wrong public identity refuses before sending any credential', () async {
    final transport = FixtureTransport()..wrongIdentity = true;
    final client = CloudOwnerClient(
      profile,
      store: MemoryOwnerStore(),
      transport: transport,
    );
    await expectLater(client.initialize(), throwsA(isA<CloudOwnerError>()));
    await expectLater(client.login(token), throwsA(isA<CloudOwnerError>()));
    expect(transport.calls.length, 1);
    expect(transport.calls.single.headers.containsKey('Cookie'), false);
  });
  test(
    'secure cookie, origin, installation and memory-only CSRF contract',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final client = await connected(store, transport);
      expect(client.authenticated, true);
      final login = transport.calls.firstWhere((call) => call.method == 'POST');
      expect(login.headers['Origin'], profile.origin);
      expect(login.headers['X-NetClaw-Installation'], installation);
      expect(login.headers['X-NetClaw-Owner-Bootstrap'], '1');
      await client.prepare(0, 0, 0);
      final prepare = transport.calls.last;
      expect(prepare.headers['X-NetClaw-CSRF'], token);
      expect(prepare.headers['Cookie'], '__Host-nc_owner_$installation=$token');
      expect(
        store.values.entries
            .where((row) => !row.key.startsWith('session.'))
            .any((row) => row.value.contains(token)),
        false,
      );
      expect(
        store.values.values.any(
          (value) =>
              value.contains('csrf_token') ||
              value.contains('tool_call') ||
              value.contains('ticket'),
        ),
        false,
      );
    },
  );
  test('insecure cookie cannot establish authority', () async {
    final store = MemoryOwnerStore(),
        transport = FixtureTransport()..badCookie = true;
    final client = CloudOwnerClient(
      profile,
      store: store,
      transport: transport,
    );
    await client.initialize();
    await expectLater(client.login(token), throwsA(isA<CloudOwnerError>()));
    expect(client.authenticated, false);
    expect(store.values.keys.any((key) => key.startsWith('session.')), false);
  });
  test(
    'storage failure prevents preparation from leaving the device',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final client = await connected(store, transport);
      store.failReferences = true;
      await expectLater(client.prepare(0, 0, 0), throwsStateError);
      expect(
        transport.calls.where((call) => call.uri.path == '/api/hud/operations'),
        isEmpty,
      );
    },
  );
  test(
    'lost prepare receipt survives restart and prevents replacement submission',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..dropPrepare = true;
      final client = await connected(store, transport);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(client.uncertain, true);
      expect(client.reference!['operation_id'], isNull);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      final restarted = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await restarted.initialize();
      expect(restarted.reference!['operation_id'], 'operation1');
      expect(
        transport.calls
            .where(
              (call) =>
                  call.method == 'POST' &&
                  call.uri.path == '/api/hud/operations',
            )
            .length,
        1,
      );
      expect(transport.effects, 0);
    },
  );
  test(
    'lost approval receipt and background resume preserve exactly one effect',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..dropDecision = true;
      final client = await connected(store, transport);
      await client.prepare(0, 0, 0);
      await expectLater(
        client.decide('approve', revision: 1, reviewDigest: digest),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(client.uncertain, true);
      expect(client.canRemove, false);
      await expectLater(
        client.decide('approve', revision: 1, reviewDigest: digest),
        throwsA(isA<CloudOwnerError>()),
      );
      client.suspend();
      expect(client.operation, isNull);
      expect(client.session, isNull);
      await client.resume();
      expect(client.operation!['result']['durable_ack'], true);
      expect(transport.effects, 1);
      final restart = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await restart.initialize();
      expect(restart.operation!['attempt_count'], 1);
      expect(transport.effects, 1);
    },
  );
  test(
    'stale digest/revision and expired review refuse without mutation',
    () async {
      final client = await connected(MemoryOwnerStore(), FixtureTransport());
      await client.prepare(0, 0, 0);
      await expectLater(
        client.decide('approve', revision: 0, reviewDigest: digest),
        throwsA(isA<CloudOwnerError>()),
      );
      await expectLater(
        client.decide('approve', revision: 1, reviewDigest: 'c' * 64),
        throwsA(isA<CloudOwnerError>()),
      );
      client.operation!['review']['limits']['expires_at_ms'] = 1;
      expect(client.canDecide('approve'), false);
      expect((client.transport as FixtureTransport).effects, 0);
    },
  );
  test(
    'verified failed receipt with delivered ACK recovers GET-only and requires explicit removal before another read',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final client = await connected(store, transport);
      await client.prepare(0, 0, 0);
      await client.decide('approve', revision: 1, reviewDigest: digest);
      // The protected service verified this signed FAILED receipt and its ACK.
      transport.operation = {
        ...transport.operation!,
        'state': 'failed',
        'result': {
          ...transport.operation!['result'] as Json,
          'evidence': {'status': 'FAILED'},
        },
      };
      final oldRef = Map<String, dynamic>.from(client.reference!);
      final beforeRecovery = transport.calls.length;
      final restarted = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await restarted.initialize();
      expect(restarted.operation!['state'], 'failed');
      expect(restarted.canRemove, true);
      expect(restarted.reference, oldRef);
      expect(
        transport.calls.skip(beforeRecovery).every((c) => c.method == 'GET'),
        true,
      );
      await expectLater(
        restarted.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(await store.reference(profile), oldRef);
      expect(
        transport.calls
            .where(
              (c) => c.method == 'POST' && c.uri.path == '/api/hud/operations',
            )
            .length,
        1,
      );
      await restarted.removeResolvedReference();
      expect(await store.reference(profile), isNull);
      await restarted.prepare(0, 0, 0);
      expect(
        restarted.reference!['client_nonce'],
        isNot(oldRef['client_nonce']),
      );
      expect(restarted.reference!['decision_sent'], isNull);
      expect(restarted.operation!['state'], 'review_pending');
      expect(
        transport.calls
            .where(
              (c) => c.method == 'POST' && c.uri.path == '/api/hud/operations',
            )
            .length,
        2,
      );
      expect(
        transport.calls.where((c) => c.uri.path.endsWith('/decision')).length,
        1,
      );
      expect(transport.effects, 1);
    },
  );
  test(
    'failed or unknown work cannot be removed or replaced with incomplete receipt or ACK',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final client = await connected(store, transport);
      await client.prepare(0, 0, 0);
      await client.decide('approve', revision: 1, reviewDigest: digest);
      final done = Map<String, dynamic>.from(transport.operation!);
      final result = done['result'] as Json;
      final oldRef = Map<String, dynamic>.from(client.reference!);
      for (final change in <Json>[
        {'result': null},
        {
          'result': {'verified': true},
        },
        {
          'result': {...result, 'verified': false},
        },
        {
          'result': {...result, 'durable_ack': false},
        },
        {
          'result': {...result, 'ack_delivery_pending': true},
        },
        {'reconciliation_required': true},
        {'state': 'outcome_unknown'},
      ]) {
        transport.operation = {...done, 'state': 'failed', ...change};
        final before = transport.calls.length;
        await client.status();
        expect(client.canRemove, false);
        await expectLater(
          client.removeResolvedReference(),
          throwsA(isA<CloudOwnerError>()),
        );
        await expectLater(
          client.prepare(0, 0, 0),
          throwsA(isA<CloudOwnerError>()),
        );
        expect(client.reference, oldRef);
        expect(await store.reference(profile), oldRef);
        expect(
          transport.calls.skip(before).every((c) => c.method == 'GET'),
          true,
        );
      }
      expect(
        transport.calls
            .where(
              (c) => c.method == 'POST' && c.uri.path == '/api/hud/operations',
            )
            .length,
        1,
      );
      expect(
        transport.calls.where((c) => c.uri.path.endsWith('/decision')).length,
        1,
      );
      expect(transport.effects, 1);
    },
  );
  test(
    'revoked session drops credential but retains operation for later owner recovery',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final client = await connected(store, transport);
      await client.prepare(0, 0, 0);
      client.suspend();
      transport.revoked = true;
      await expectLater(client.resume(), throwsA(isA<CloudOwnerError>()));
      expect(client.authenticated, false);
      expect(await store.reference(profile), isNotNull);
      expect(await store.read('session.${profile.key}'), isNull);
    },
  );
  test(
    'profile switch cannot send another origin cookie or operation identity',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final client = await connected(store, transport);
      await client.prepare(0, 0, 0);
      final other = CloudOwnerClient(
        CloudProfile('https://other.example.test', installation),
        store: store,
        transport: transport,
      );
      await other.initialize();
      expect(other.authenticated, false);
      expect(other.reference, isNull);
      expect(transport.calls.last.uri.host, 'other.example.test');
      expect(transport.calls.last.headers.containsKey('Cookie'), false);
    },
  );
  test(
    'duplicate prepare taps and suspend during response preserve one admission',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..pausePrepare = Completer<void>();
      final client = await connected(store, transport);
      final work = client.prepare(0, 0, 0);
      while (transport.operation == null) {
        await Future<void>.delayed(Duration.zero);
      }
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      client.suspend();
      transport.pausePrepare!.complete();
      await expectLater(work, throwsA(isA<CloudOwnerError>()));
      await client.resume();
      expect(client.reference!['operation_id'], 'operation1');
      expect(
        transport.calls
            .where(
              (call) =>
                  call.method == 'POST' &&
                  call.uri.path == '/api/hud/operations',
            )
            .length,
        1,
      );
    },
  );
  test(
    'confirmed unsubmitted refusal requires explicit discard; unknown cannot be removed',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..refusePrepare = true;
      final client = await connected(store, transport);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(client.canRemove, true);
      await client.removeResolvedReference();
      expect(client.reference, isNull);
      transport.refusePrepare = false;
      transport.dropPrepare = true;
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      await expectLater(
        client.removeResolvedReference(),
        throwsA(isA<CloudOwnerError>()),
      );
    },
  );
  test(
    'native HTTPS transport never accepts plaintext or an untrusted TLS server',
    () async {
      final transport = HttpsOwnerTransport();
      await expectLater(
        transport.send(Uri.parse('http://127.0.0.1/'), 'GET', {}, null),
        throwsA(isA<CloudOwnerError>()),
      );
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final subscription = server.listen((request) async {
        request.response.write('{}');
        await request.response.close();
      });
      await expectLater(
        transport.send(
          Uri.parse('https://127.0.0.1:${server.port}/'),
          'GET',
          {},
          null,
        ),
        throwsA(isA<CloudOwnerError>()),
      );
      await subscription.cancel();
      await server.close(force: true);
    },
  );
  test(
    'lost decision remains spent after restart even when server still shows review pending',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..dropBeforeDecision = true;
      final client = await connected(store, transport);
      await client.prepare(0, 0, 0);
      await expectLater(
        client.decide('approve', revision: 1, reviewDigest: digest),
        throwsA(isA<CloudOwnerError>()),
      );
      final restarted = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await restarted.initialize();
      expect(restarted.operation!['state'], 'review_pending');
      expect(restarted.reference!['decision_sent'], true);
      expect(restarted.canDecide('approve'), false);
      await expectLater(
        restarted.decide('approve', revision: 1, reviewDigest: digest),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(
        transport.calls
            .where((call) => call.uri.path.endsWith('/decision'))
            .length,
        1,
      );
    },
  );
  for (final lane in ['session', 'reference']) {
    test(
      'suspend during secure $lane persistence cannot restore private state',
      () async {
        final store = MemoryOwnerStore(), transport = FixtureTransport();
        final client = await connected(store, transport);
        await client.prepare(0, 0, 0);
        store.pauseWritePrefix = '$lane.';
        store.writeStarted = Completer<void>();
        store.releaseWrite = Completer<void>();
        final pending = lane == 'session'
            ? client.login(token)
            : client.status();
        await store.writeStarted!.future;
        client.suspend();
        store.releaseWrite!.complete();
        await expectLater(pending, throwsA(isA<CloudOwnerError>()));
        expect(client.session, isNull);
        expect(client.operation, isNull);
        expect(client.authenticated, false);
        store.pauseWritePrefix = null;
        await client.resume();
        expect(client.reference!['operation_id'], 'operation1');
      },
    );
  }
  test(
    'definite unsubmitted proof survives restart and requires explicit discard',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..refusePrepare = true;
      final client = await connected(store, transport);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      final saved = await store.reference(profile);
      expect(saved!['not_submitted'], true);
      expect(saved['operation_id'], isNull);
      final restarted = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await restarted.initialize();
      expect(restarted.notSubmitted, true);
      expect(restarted.uncertain, false);
      expect(restarted.canRemove, true);
      await expectLater(restarted.status(), throwsA(isA<CloudOwnerError>()));
      expect(restarted.canRemove, true);
      expect(
        transport.calls.where(
          (c) => c.method == 'GET' && c.uri.path == '/api/hud/operations',
        ),
        isEmpty,
      );
      await expectLater(
        restarted.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      await restarted.removeResolvedReference();
      expect(await store.reference(profile), isNull);
      transport.refusePrepare = false;
      await restarted.prepare(0, 0, 0);
      expect(restarted.operation!['operation_id'], 'operation1');
      expect(transport.effects, 0);
    },
  );
  test(
    'background during proof persistence restores only durable proof without a status probe',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..refusePrepare = true;
      final client = await connected(store, transport);
      store.pauseWritePrefix = 'reference.';
      store.pauseProofOnly = true;
      store.writeStarted = Completer<void>();
      store.releaseWrite = Completer<void>();
      final pending = client.prepare(0, 0, 0);
      await store.writeStarted!.future;
      client.suspend();
      store.releaseWrite!.complete();
      await expectLater(pending, throwsA(isA<CloudOwnerError>()));
      expect(client.notSubmitted, false);
      expect(client.session, isNull);
      store.pauseWritePrefix = null;
      await client.resume();
      expect(client.notSubmitted, true);
      expect(client.canRemove, true);
      expect(
        transport.calls.where(
          (c) => c.method == 'GET' && c.uri.path == '/api/hud/operations',
        ),
        isEmpty,
      );
    },
  );
  test(
    '404 after unknown prepare never creates proof or permits reference discard',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..dropBeforePrepare = true;
      final client = await connected(store, transport);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      final restarted = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await expectLater(
        restarted.initialize(),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(restarted.uncertain, true);
      expect(restarted.notSubmitted, false);
      expect(restarted.canRemove, false);
      expect(
        (await store.reference(profile))!.containsKey('not_submitted'),
        false,
      );
      await expectLater(
        restarted.removeResolvedReference(),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(
        transport.calls
            .where(
              (c) => c.method == 'POST' && c.uri.path == '/api/hud/operations',
            )
            .length,
        1,
      );
    },
  );
  testWidgets(
    'native UI presents complete review and requires explicit checkbox before approve once',
    (tester) async {
      final client = await connected(MemoryOwnerStore(), FixtureTransport());
      await client.prepare(0, 0, 0);
      await tester.pumpWidget(
        MaterialApp(home: CloudOwnerScreen(initialClient: client)),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('Complete immutable review')),
        findsOneWidget,
      );
      final button = find.widgetWithText(FilledButton, 'Approve once');
      expect(tester.widget<FilledButton>(button).onPressed, isNull);
      await tester.ensureVisible(
        find.byKey(const ValueKey('cloud-review-confirmation')),
      );
      await tester.tap(find.byKey(const ValueKey('cloud-review-confirmation')));
      await tester.pump();
      expect(tester.widget<FilledButton>(button).onPressed, isNotNull);
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('cloud-receipt')), findsOneWidget);
      expect((client.transport as FixtureTransport).effects, 1);
      expect(find.text('Chat'), findsNothing);
      await tester.pumpWidget(const SizedBox());
    },
  );

  test(
    'explicit open lab performs exact operations without sessions or credentials',
    () async {
      final store = MemoryOwnerStore(),
          transport = FixtureTransport()..openLab = true;
      store.values['session.${profile.key}'] =
          token; // Older profile session is not even read.
      final client = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await client.initialize();
      expect(client.openLab, true);
      expect(client.operationsReady, true);
      expect(client.authenticated, false);
      expect(client.session, isNull);
      await expectLater(client.login(token), throwsA(isA<CloudOwnerError>()));
      await client.prepare(0, 0, 0);
      expect(client.operation!['review']['principal'], transport.labPrincipal);
      await client.decide('approve', revision: 1, reviewDigest: digest);
      await client.reconcile();
      expect(client.canRemove, true);
      final beforeResume = transport.calls.length;
      client.suspend();
      await client.resume();
      expect(
        transport.calls
            .skip(beforeResume)
            .every((call) => call.method == 'GET'),
        true,
      );
      expect(client.reference!['decision_sent'], true);
      expect(transport.effects, 1);
      expect(
        transport.calls.any(
          (call) => call.uri.path == '/api/hud/owner/session',
        ),
        false,
      );
      expect(store.reads.any((key) => key.startsWith('session.')), false);
      expect(store.values['session.${profile.key}'], token);
      for (final call in transport.calls) {
        expect(
          call.headers.keys.toSet().intersection({
            'Cookie',
            'X-NetClaw-CSRF',
            'X-NetClaw-Owner-Bootstrap',
            'Authorization',
          }),
          isEmpty,
        );
        expect(call.headers['X-NetClaw-Installation'], installation);
        if (call.method != 'GET') {
          expect(call.headers['Origin'], profile.origin);
        }
      }
    },
  );

  test(
    'open lab accepts only the explicit supported mode and principal',
    () async {
      final good = FixtureTransport().labPrincipal;
      for (final access in <Json>[
        {'mode': 'none', 'principal': good},
        {'mode': 'open-lab'},
        {
          'mode': 'open-lab',
          'principal': {...good, 'issuer': 'local'},
        },
        {
          'mode': 'open-lab',
          'principal': {...good, 'subject': 'not-a-uuid'},
        },
        {
          'mode': 'open-lab',
          'principal': {
            ...good,
            'roles': ['owner'],
          },
        },
        {
          'mode': 'open-lab',
          'principal': {...good, 'display_name': 'Owner'},
        },
      ]) {
        final transport = FixtureTransport()..accessOverride = access;
        final client = CloudOwnerClient(
          profile,
          store: MemoryOwnerStore(),
          transport: transport,
        );
        await expectLater(client.initialize(), throwsA(isA<CloudOwnerError>()));
        expect(client.operationsReady, false);
        expect(transport.calls.map((call) => call.uri.path), ['/api/runtime']);
      }
    },
  );

  test(
    'open lab does not fall back to login on 401 or accept a changed identity',
    () async {
      for (final changedIdentity in [false, true]) {
        final transport = FixtureTransport()..openLab = true;
        final store = MemoryOwnerStore();
        final client = CloudOwnerClient(
          profile,
          store: store,
          transport: transport,
        );
        await client.initialize();
        await client.prepare(0, 0, 0);
        final retained = jsonEncode(await store.reference(profile));
        if (changedIdentity) {
          transport.wrongIdentity = true;
          client.suspend();
          await expectLater(client.resume(), throwsA(isA<CloudOwnerError>()));
        } else {
          transport.refuseLab = true;
          await expectLater(client.status(), throwsA(isA<CloudOwnerError>()));
        }
        expect(client.operationsReady, false);
        expect(jsonEncode(await store.reference(profile)), retained);
        expect(
          transport.calls.any(
            (call) => call.uri.path == '/api/hud/owner/session',
          ),
          false,
        );
        expect(transport.effects, 0);
      }
    },
  );

  test(
    'new anonymous prepare refuses an owner-principal review and retains its nonce',
    () async {
      final transport = FixtureTransport()
        ..openLab = true
        ..wrongReviewPrincipal = true;
      final store = MemoryOwnerStore();
      final client = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await client.initialize();
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(client.uncertain, true);
      expect(client.reference!['client_nonce'], isNotEmpty);
      expect(client.canDecide('approve'), false);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(transport.calls.where((call) => call.method == 'POST').length, 1);
    },
  );

  test(
    'historical owner reference retains principal and cannot be reapproved in open lab',
    () async {
      final store = MemoryOwnerStore(), transport = FixtureTransport();
      final old = await connected(store, transport);
      await old.prepare(0, 0, 0);
      final historicalReview = jsonEncode(old.operation!['review']);
      old.suspend();
      transport.openLab = true;
      transport.calls.clear();
      store.reads.clear();
      final client = CloudOwnerClient(
        profile,
        store: store,
        transport: transport,
      );
      await client.initialize();
      expect(jsonEncode(client.operation!['review']), historicalReview);
      expect(client.canDecide('approve'), false);
      expect(client.canDecide('deny'), false);
      await expectLater(
        client.decide('approve', revision: 1, reviewDigest: digest),
        throwsA(isA<CloudOwnerError>()),
      );
      transport.operation = {
        ...transport.operation!,
        'state': 'member_outcome_unknown',
        'attempt_count': 1,
        'may_have_executed': true,
        'reconciliation_required': true,
        'allowed_actions': ['reconcile'],
        'approval': {'original': true},
      };
      await client.status();
      expect(client.canRemove, false);
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      transport.operation = {
        ...transport.operation!,
        'state': 'failed',
        'reconciliation_required': false,
        'result': {
          'verified': true,
          'durable_ack': true,
          'ack_delivery_pending': false,
          'digest': digest,
          'evidence': {'outcome': 'failed', 'output': {}},
        },
      };
      await client.reconcile();
      expect(client.canRemove, true);
      expect(jsonEncode(client.operation!['review']), historicalReview);
      expect(client.operation!['approval'], {'original': true});
      expect(client.operation!['attempt_count'], 1);
      expect(transport.effects, 0);
      expect(
        transport.calls
            .where((call) => call.method != 'GET')
            .map((call) => call.uri.path),
        ['/api/hud/operations/operation1/reconcile'],
      );
      expect(store.reads.any((key) => key.startsWith('session.')), false);
    },
  );

  test(
    'open lab restart retains lost decisions and definite unsubmitted proof',
    () async {
      for (final refused in [false, true]) {
        final store = MemoryOwnerStore(),
            transport = FixtureTransport()..openLab = true;
        final client = CloudOwnerClient(
          profile,
          store: store,
          transport: transport,
        );
        await client.initialize();
        if (refused) {
          transport.refusePrepare = true;
          await expectLater(
            client.prepare(0, 0, 0),
            throwsA(isA<CloudOwnerError>()),
          );
        } else {
          await client.prepare(0, 0, 0);
          transport.dropBeforeDecision = true;
          await expectLater(
            client.decide('approve', revision: 1, reviewDigest: digest),
            throwsA(isA<CloudOwnerError>()),
          );
        }
        client.suspend();
        final count = transport.calls.length;
        final restart = CloudOwnerClient(
          profile,
          store: store,
          transport: transport,
        );
        await restart.initialize();
        expect(restart.canDecide('approve'), false);
        expect(restart.canRemove, refused);
        expect(
          transport.calls.skip(count).every((call) => call.method == 'GET'),
          true,
        );
        expect(transport.effects, 0);
        await expectLater(
          restart.prepare(0, 0, 0),
          throwsA(isA<CloudOwnerError>()),
        );
      }
    },
  );

  test(
    'backgrounding open lab discovery cannot expose late private state',
    () async {
      final transport = FixtureTransport()
        ..openLab = true
        ..pauseRuntime = Completer<void>();
      final client = CloudOwnerClient(
        profile,
        store: MemoryOwnerStore(),
        transport: transport,
      );
      final pending = client.initialize();
      await Future<void>.delayed(Duration.zero);
      client.suspend();
      transport.pauseRuntime!.complete();
      await expectLater(pending, throwsA(isA<CloudOwnerError>()));
      expect(client.operationsReady, false);
      expect(client.catalog, isNull);
      expect(client.operation, isNull);
    },
  );

  testWidgets(
    'existing cloud screen shows explicit lab access without sign-in UI',
    (tester) async {
      final transport = FixtureTransport()..openLab = true;
      final client = CloudOwnerClient(
        profile,
        store: MemoryOwnerStore(),
        transport: transport,
      );
      await client.initialize();
      await tester.pumpWidget(
        MaterialApp(home: CloudOwnerScreen(initialClient: client)),
      );
      await tester.pumpAndSettle();
      expect(
        find.text('Connected: Unauthenticated lab operator'),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('cloud-ticket')), findsNothing);
      expect(find.text('Sign in as owner'), findsNothing);
      expect(find.text('Sign out'), findsNothing);
      expect(find.textContaining('Select one catalogued read'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
