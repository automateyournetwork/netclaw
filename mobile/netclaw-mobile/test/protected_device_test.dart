import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_flow.dart';
import 'package:netclaw_mobile/ncfed/enrollment_qr_payload.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/ncfed/headless_connect.dart';
import 'package:netclaw_mobile/ncfed/protected_device_client.dart';
import 'package:netclaw_mobile/ncfed/protected_device_descriptor.dart';
import 'package:netclaw_mobile/screens/cloud_owner_screen.dart';
import 'cloud_owner_test.dart'
    show FixtureTransport, MemoryOwnerStore, installation, profile;
import 'edge_client_lifecycle_test.dart' show TestChannel;

final devicePrincipal = <String, dynamic>{
  'issuer': 'device-key',
  'subject': '22222222-2222-4222-8222-222222222222',
  'display_name': 'Fixture iPhone',
  'roles': ['device-operator'],
};
final payload = EnrollmentQrPayload(
  borderHost: 'border.example.test',
  borderPort: 443,
  clawDomain: 'border.example.test',
  enrollmentToken: 'in2n_private_fixture',
  installationId: installation,
  wsPath: '/mobile/ws',
);
Map<String, dynamic> border() => {
  'installation_id': installation,
  'capabilities': {
    'text': false,
    'voice_text': false,
    'attachments': false,
    'task_outcomes_v1': false,
    'request_recovery': false,
    'protected_operations': {
      'schema': 1,
      'installation_id': installation,
      'origin': profile.origin,
      'methods': [...protectedDeviceMethods],
      'principal': {...devicePrincipal},
    },
  },
};

class DeviceFixture extends FixtureTransport {
  bool otherDevice = false;
  @override
  Map<String, dynamic> get session => {
    ...super.session,
    'principal': {
      ...devicePrincipal,
      if (otherDevice) 'subject': '33333333-3333-4333-8333-333333333333',
    },
  };
  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Map<String, dynamic>? body,
  ) async {
    final result = await super.send(uri, method, headers, body);
    if (uri.path == '/api/runtime') {
      return OwnerResponse(200, {
        ...result.body,
        'access': {'mode': 'device-key', 'principal': devicePrincipal},
      });
    }
    return result;
  }
}

class FixtureIdentity extends EdgeIdentity {
  @override
  Future<String> publicKeyFingerprint() async => 'a' * 64;
}

CloudOwnerClient deviceClient(
  DeviceFixture transport,
  MemoryOwnerStore store,
) => CloudOwnerClient(
  profile,
  store: store,
  transport: transport,
  expectedDevicePrincipal: devicePrincipal,
);

void main() {
  test(
    'legacy QR remains root WSS; protected destination rejects path/installation mismatch',
    () {
      final legacy = EnrollmentQrPayload.parse(
        jsonEncode({
          'border_host': 'localhost',
          'border_port': 8443,
          'claw_domain': 'localhost',
          'enrollment_token': 'fixture',
        }),
      );
      expect(legacy.websocketUri.toString(), 'wss://localhost:8443/');
      for (final change in [
        {'ws_path': '/admin'},
        {'ws_path': '/mobile/ws'},
        {'installation_id': 'wrong'},
      ]) {
        expect(
          () => EnrollmentQrPayload.parse(
            jsonEncode({
              'border_host': 'localhost',
              'border_port': 8443,
              'claw_domain': 'localhost',
              'enrollment_token': 'fixture',
              ...change,
            }),
          ),
          throwsFormatException,
        );
      }
    },
  );
  test(
    'protected descriptor requires exact schema installation domain methods and principal',
    () {
      expect(
        ProtectedDeviceDescriptor.fromBorder(border(), payload)!.principal,
        devicePrincipal,
      );
      final mutations = <void Function(Map<String, dynamic>)>[
        (b) => b['installation_id'] = 'wrong',
        (b) => b['capabilities']['text'] = true,
        (b) => b['capabilities']['protected_operations']['schema'] = 2,
        (b) => b['capabilities']['protected_operations']['origin'] =
            'https://evil.example.test',
        (b) => b['capabilities']['protected_operations']['methods'] = [
          'n2n/edge/ask',
        ],
        (b) => b['capabilities']['protected_operations']['principal']['roles'] =
            ['owner'],
        (b) => b['capabilities'].remove('protected_operations'),
      ];
      for (final mutate in mutations) {
        final b = border();
        mutate(b);
        expect(
          () => ProtectedDeviceDescriptor.fromBorder(b, payload),
          throwsFormatException,
        );
      }
      final retained = EnrollmentQrPayload(
        borderHost: payload.borderHost,
        borderPort: 443,
        clawDomain: payload.clawDomain,
        enrollmentToken: '',
        wsPath: '/mobile/ws',
        installationId: installation,
        expectedDeviceSubject: '33333333-3333-4333-8333-333333333333',
      );
      expect(
        () => ProtectedDeviceDescriptor.fromBorder(border(), retained),
        throwsFormatException,
      );
    },
  );
  test(
    'pending enrollment persists before send without token and prevents a second enrollment',
    () async {
      final dir = await Directory.systemTemp.createTemp('mobile-pending-');
      addTearDown(() => dir.delete(recursive: true));
      final store = EnrollmentStore(dir);
      var calls = 0;
      final raw = jsonEncode({
        'border_host': payload.borderHost,
        'border_port': 443,
        'claw_domain': payload.clawDomain,
        'enrollment_token': payload.enrollmentToken,
        'installation_id': installation,
        'ws_path': '/mobile/ws',
      });
      Future<EdgeClient> lost(
        EnrollmentQrPayload p, {
        required String memberId,
        required EdgeIdentity identity,
        String? displayName,
      }) async {
        calls++;
        expect((await store.load())!.pending, isTrue);
        expect(
          await File('${dir.path}/ncfed_enrollment.json').readAsString(),
          isNot(contains(payload.enrollmentToken)),
        );
        throw EdgeClientException('timeout', 'lost after consumption');
      }

      final first = await attemptEnrollmentFromQr(
        raw,
        memberId: 'risk/simulator',
        identity: FixtureIdentity(),
        store: store,
        enroll: lost,
      );
      expect(first, isA<EnrollmentFailure>());
      expect((first as EnrollmentFailure).pending, isTrue);
      final retained = await EnrollmentStore(dir).load();
      expect(retained!.keyFingerprint, 'a' * 64);
      expect(retained.toPayload().enrollmentToken, isEmpty);
      expect(retained.toPayload().wsPath, '/mobile/ws');
      await attemptEnrollmentFromQr(
        raw,
        memberId: 'risk/other',
        identity: FixtureIdentity(),
        store: store,
        enroll: lost,
      );
      expect(calls, 1);
      expect((await store.load())!.memberId, 'risk/simulator');
      var dials = 0;
      await expectLater(
        connectHeadless(
          directory: dir,
          reconnect:
              (
                p, {
                required memberId,
                required keyFingerprint,
                required identity,
              }) async {
                dials++;
                throw StateError('must not dial');
              },
        ),
        throwsA(isA<ProtectedHeadlessUnavailable>()),
      );
      expect(dials, 0);
    },
  );
  test('successful enrollment confirms the exact public key; mismatch stays pending', () async {
    for (final matches in [true, false]) {
      final dir = await Directory.systemTemp.createTemp('mobile-enrollment-confirm-');
      addTearDown(() => dir.delete(recursive: true));
      final store = EnrollmentStore(dir), channel = TestChannel();
      final edge = EdgeClient.forTesting(channel);
      edge.enrollFingerprint = (matches ? 'a' : 'b') * 64;
      edge.protectedDevice = ProtectedDeviceDescriptor.fromBorder(border(), payload);
      addTearDown(() async { await edge.close(); await channel.input.close(); });
      final result = await attemptEnrollmentFromQr(jsonEncode({
        'border_host': payload.borderHost, 'border_port': 443,
        'claw_domain': payload.clawDomain, 'enrollment_token': payload.enrollmentToken,
        'installation_id': installation, 'ws_path': '/mobile/ws',
      }), memberId: 'risk/native', identity: FixtureIdentity(), store: store,
        enroll: (p, {required memberId, required identity, displayName}) async => edge);
      expect(result, matches ? isA<EnrollmentSuccess>() : isA<EnrollmentFailure>());
      final saved = (await store.load())!;
      expect(saved.pending, !matches);
      expect(saved.keyFingerprint, 'a' * 64);
      if (matches) expect(saved.deviceSubject, devicePrincipal['subject']);
      expect(await File('${dir.path}/ncfed_enrollment.json').readAsString(),
        isNot(contains(payload.enrollmentToken)));
    }
  });
  test('only exact native not-enrolled rollback proof releases pending enrollment', () async {
    for (final matching in [true, false]) {
      final dir = await Directory.systemTemp.createTemp('mobile-no-enrollment-');
      addTearDown(() => dir.delete(recursive: true));
      final store = EnrollmentStore(dir);
      final result = await attemptEnrollmentFromQr(jsonEncode({
        'border_host': payload.borderHost, 'border_port': 443,
        'claw_domain': payload.clawDomain, 'enrollment_token': payload.enrollmentToken,
        'installation_id': installation, 'ws_path': '/mobile/ws',
      }), memberId: 'risk/native', identity: FixtureIdentity(), store: store,
        enroll: (p, {required memberId, required identity, displayName}) async =>
          throw EdgeClientException('-32000', 'refused', data: {
            'admission':'not_enrolled', 'code':'enrollment_refused','status':400,
            'member_id': matching ? memberId : 'another-device', 'key_fingerprint':'a'*64,
          }));
      expect((result as EnrollmentFailure).pending, !matching);
      expect(await store.load(), matching ? isNull : isNotNull);
    }
  });
  test('protected home answers the Border heartbeat without legacy registration', () async {
    final channel = TestChannel();
    final edge = EdgeClient.forTesting(channel);
    edge.protectedDevice = ProtectedDeviceDescriptor.fromBorder(border(), payload);
    addTearDown(() async { await edge.close(); await channel.input.close(); });
    protectedDeviceClient(edge, store: MemoryOwnerStore());
    channel.input.add(jsonEncode({
      'id': 'border:heartbeat', 'method': 'n2n/edge/heartbeat', 'params': {},
    }));
    await channel.sink.firstSend.future.timeout(const Duration(seconds: 2));
    expect(channel.sink.sent.single, {
      'jsonrpc': '2.0', 'id': 'border:heartbeat', 'result': <String, dynamic>{},
    });
    expect(edge.isClosed, isFalse);
  });
  test('device runtime is rejected by ordinary owner client', () async {
    final transport = DeviceFixture();
    await expectLater(
      CloudOwnerClient(
        profile,
        store: MemoryOwnerStore(),
        transport: transport,
      ).initialize(),
      throwsA(isA<CloudOwnerError>()),
    );
    expect(transport.calls.length, 1);
  });
  test(
    'device initializes without owner session and rejects another device review',
    () async {
      final transport = DeviceFixture(), store = MemoryOwnerStore();
      final client = deviceClient(transport, store);
      await client.initialize();
      expect(client.deviceKey, isTrue);
      expect(client.openLab, isFalse);
      expect(
        transport.calls.any((c) => c.uri.path.contains('session')),
        isFalse,
      );
      transport.otherDevice = true;
      await expectLater(
        client.prepare(0, 0, 0),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(client.uncertain, isTrue);
      expect(client.canDecide('approve'), isFalse);
    },
  );
  for (final phase in ['prepare', 'decision']) {
    test(
      'lost device $phase retains identity and recovery adds no repeat',
      () async {
        final transport = DeviceFixture(), store = MemoryOwnerStore();
        final client = deviceClient(transport, store);
        await client.initialize();
        if (phase == 'prepare') transport.dropPrepare = true;
        if (phase == 'prepare') {
          await expectLater(client.prepare(0, 0, 0), throwsA(anything));
        } else {
          await client.prepare(0, 0, 0);
          transport.dropDecision = true;
          await expectLater(
            client.decide(
              'approve',
              revision: client.operation!['revision'],
              reviewDigest: client.operation!['review_digest'],
            ),
            throwsA(anything),
          );
        }
        final reference = Map<String, dynamic>.from(client.reference!);
        final count = transport.calls.where((c) => c.method == 'POST').length;
        final restarted = deviceClient(transport, store);
        await restarted.initialize();
        expect(restarted.reference!['client_nonce'], reference['client_nonce']);
        expect(transport.calls.where((c) => c.method == 'POST').length, count);
        if (phase == 'decision') {
          expect(restarted.canDecide('approve'), isFalse);
        }
      },
    );
  }
  test(
    'WSS adapter sends only five scoped methods and preserves admission proof',
    () async {
      final channel = TestChannel();
      final edge = EdgeClient.forTesting(channel);
      addTearDown(() async {
        await edge.close();
        await channel.input.close();
      });
      final binding = ProtectedDeviceDescriptor.fromBorder(border(), payload)!;
      edge.protectedDevice = binding;
      final transport = ProtectedDeviceTransport(edge, binding);
      final headers = {'X-NetClaw-Installation': installation};
      final result = transport.send(
        Uri.parse('${profile.origin}/api/hud/operations'),
        'POST',
        headers,
        {'client_nonce': 'nonce'},
      );
      await channel.sink.firstSend.future;
      final sent = channel.sink.sent.single;
      expect(sent['method'], 'n2n/edge/operations/prepare');
      expect(sent['params']['installation_id'], installation);
      channel.input.add(
        jsonEncode({
          'id': sent['id'],
          'error': {
            'code': -32000,
            'message': 'refused',
            'data': {
              'code': 'scope_refused',
              'status': 403,
              'admission': 'not_submitted',
            },
          },
        }),
      );
      expect((await result).body['admission'], 'not_submitted');
      await expectLater(
        transport.send(
          Uri.parse('${profile.origin}/api/hud/owner/session'),
          'POST',
          headers,
          {},
        ),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(channel.sink.sent.length, 1);
    },
  );
  testWidgets(
    'device UI exposes review without login/manual profile or legacy actions',
    (tester) async {
      final client = deviceClient(DeviceFixture(), MemoryOwnerStore());
      await client.initialize();
      await tester.pumpWidget(
        MaterialApp(
          home: CloudOwnerScreen(initialClient: client, deviceMode: true),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Mobile operations'), findsOneWidget);
      expect(find.text('Prepare review'), findsOneWidget);
      for (final label in [
        'Verify cloud Border',
        'Sign in as owner',
        'Choose cloud profile',
        'Sign out',
      ]) {
        expect(find.text(label), findsNothing);
      }
    },
  );
}
