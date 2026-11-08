import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/ncfed/cluster_trust.dart';
import 'package:netclaw_mobile/ncfed/enrollment_qr_payload.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/ncfed/endpoint_recovery.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/protected_device_client.dart';
import 'package:netclaw_mobile/ncfed/protected_device_descriptor.dart';
import 'cloud_owner_test.dart' show MemoryOwnerStore, FixtureTransport;
import 'edge_client_lifecycle_test.dart' show TestChannel;

class RetainedIdentity extends EdgeIdentity {
  @override
  Future<String> publicKeyFingerprint() async => 'a' * 64;
}

final fixture =
    jsonDecode(
          File(
            '../../tests/fixtures/ha-179/cluster-golden.json',
          ).readAsStringSync(),
        )
        as Json;
final pin = ClusterPin.fromJson(fixture['pin']);
final devicePrincipal = <String, dynamic>{
  'issuer': 'device-key',
  'subject': '22222222-2222-4222-8222-222222222222',
  'display_name': 'Enrolled mobile device',
  'roles': ['device-operator'],
};
late String nativeCryptoPath;
void nativeTest(String name, Future<void> Function() body) => test(
  name,
  body,
  skip: !Platform.isMacOS
      ? 'Requires the production CryptoKit verifier on macOS'
      : false,
);
Future<Json> nativeCrypto(
  Uint8List data, {
  Uint8List? spki,
  Uint8List? signature,
}) async {
  final result = await Process.run(nativeCryptoPath, [
    jsonEncode({
      'data': base64Encode(data),
      if (spki != null) 'spki': base64Encode(spki),
      if (signature != null) 'signature': base64Encode(signature),
    }),
  ]);
  if (result.exitCode != 0) {
    throw const FormatException('Native verification refused');
  }
  return jsonDecode(result.stdout as String) as Json;
}

Future<ClusterBinding> binding(Json descriptor, {ClusterPin? saved}) =>
    ClusterBinding.verify(
      descriptor,
      saved ?? pin,
      origin: (descriptor['manifest']['manifest']['nodes'] as List).firstWhere(
        (n) => n['node_id'] == descriptor['node_id'],
      )['endpoints']['https'],
      installationId: descriptor['installation_id'],
      nowMs: fixture['now_ms'],
      crypto: nativeCrypto,
    );

class ClusterTransport extends FixtureTransport {
  final ClusterBinding cluster;
  int epoch;
  bool noQuorum = false;
  ClusterTransport(this.cluster) : epoch = cluster.epoch!;
  @override
  Json get session => {...super.session, 'principal': devicePrincipal};
  Json get authority => {
    'mode': 'cluster',
    'cluster_id': cluster.pin.clusterId,
    'generation': cluster.pin.generation,
    'served_by': cluster.nodeId,
    'epoch': epoch,
    'observation_only': true,
  };
  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  ) async {
    final response = await super.send(uri, method, headers, body);
    if (uri.path == '/api/runtime') {
      return OwnerResponse(200, {
        ...response.body,
        'installationId': cluster.installationId,
        'access': {'mode': 'device-key', 'principal': devicePrincipal},
        'cluster': cluster.descriptor,
      });
    }
    if (noQuorum) return OwnerResponse(503, {'code': 'no_quorum'});
    if (uri.path.endsWith('/catalog')) {
      return OwnerResponse(200, {
        ...response.body,
        'capabilities': ['cluster_execution_v2'],
        'authority': authority,
      });
    }
    if (response.body['review'] is Json) {
      final review = response.body['review'] as Json;
      review['border'] = {
        'installation_id': cluster.nodes[0]['installation_id'],
        'key_id': cluster.nodes[0]['key_id'],
        'identity': cluster.nodes[0]['identity'],
      };
      review.putIfAbsent(
        'cluster',
        () => {
          'cluster_id': cluster.pin.clusterId,
          'generation': cluster.pin.generation,
          'manifest_revision': cluster.pin.revision,
          'issuer_node_id': cluster.nodes[0]['node_id'],
          'authority_epoch': epoch,
        },
      );
      return OwnerResponse(response.status, {
        ...response.body,
        'authority': authority,
        'result_reference': null,
      });
    }
    return response;
  }
}

void main() {
  setUpAll(() async {
    if (!Platform.isMacOS) return;
    final dir = await Directory.systemTemp.createTemp(
      'r08-public-crypto-test-',
    );
    addTearDown(() => dir.delete(recursive: true));
    nativeCryptoPath = '${dir.path}/cluster_public_crypto';
    final built = await Process.run('swiftc', [
      'ios/Runner/ClusterPublicCrypto.swift',
      'test/support/cluster_crypto_main.swift',
      '-o',
      nativeCryptoPath,
    ]);
    if (built.exitCode != 0) {
      throw StateError(
        'Public CryptoKit verifier did not compile: ${built.stderr}',
      );
    }
  });
  test(
    'duplicate keys and excessive nesting are rejected before signed document decoding',
    () {
      expect(
        () => clusterDecode('{"cluster_id":"a","cluster_id":"b"}'),
        throwsFormatException,
      );
      expect(() => clusterDecode('{"a":{"b":1,"b":2}}'), throwsFormatException);
      expect(
        () => clusterDecode('${'[' * 34}0${']' * 34}'),
        throwsFormatException,
      );
      expect(clusterDecode('{"a":"escaped \\"", "b":[1,true,null]}'), {
        'a': 'escaped "',
        'b': [1, true, null],
      });
    },
  );
  nativeTest(
    'native P256 verifies Python canonical golden manifest and stable cluster audience',
    () async {
      final a = await binding(fixture['descriptors'][0]),
          b = await binding(fixture['descriptors'][1]);
      expect(a.pin.sameAudience(b.pin), isTrue);
      expect(
        () => a.descriptor['generation'] = 'changed',
        throwsUnsupportedError,
      );
      expect(
        () => a.nodes[0]['endpoints']['https'] = 'https://changed.test',
        throwsUnsupportedError,
      );
      expect(a.nodeId, isNot(b.nodeId));
      final pa = CloudProfile(a.origin, a.installationId, cluster: a),
          pb = CloudProfile(b.origin, b.installationId, cluster: b);
      expect(pa.key, pb.key);
      final da = ProtectedDeviceDescriptor(
        a.installationId,
        a.origin,
        devicePrincipal,
        cluster: a,
      );
      final db = ProtectedDeviceDescriptor(
        b.installationId,
        b.origin,
        devicePrincipal,
        cluster: b,
      );
      expect(ProtectedDeviceStore(da).scope, ProtectedDeviceStore(db).scope);
      expect(ProtectedDeviceStore(da).scope, contains(a.pin.generation));
    },
  );
  nativeTest(
    'cluster handshake binds the same serving origin, enrollment generation and principal',
    () async {
      final a = await binding(fixture['descriptors'][0]), uri = a.websocketUri;
      final payload = EnrollmentQrPayload(
        borderHost: uri.host,
        borderPort: uri.port,
        clawDomain: uri.host,
        enrollmentToken: '',
        wsPath: uri.path,
        installationId: a.installationId,
        clusterPin: a.pin,
        clusterNodeId: a.nodeId,
        expectedDeviceSubject: devicePrincipal['subject'],
        expectedEnrollmentGeneration: '11111111-1111-4111-8111-111111111111',
      );
      Json response() => {
        'installation_id': a.installationId,
        'cluster': a.descriptor,
        'capabilities': {
          'text': false,
          'voice_text': false,
          'attachments': false,
          'task_outcomes_v1': false,
          'request_recovery': false,
          'protected_operations': {
            'schema': 1,
            'installation_id': a.installationId,
            'origin': a.origin,
            'methods': protectedDeviceMethods,
            'principal': {...devicePrincipal},
            'enrollment_generation': payload.expectedEnrollmentGeneration,
          },
        },
      };
      expect(
        ProtectedDeviceDescriptor.fromBorder(
          response(),
          payload,
          cluster: a,
        )!.principal,
        devicePrincipal,
      );
      for (final mutate in <void Function(Json)>[
        (d) => d['origin'] = '${a.origin}:9443',
        (d) =>
            d['enrollment_generation'] = '22222222-2222-4222-8222-222222222222',
        (d) =>
            d['principal']['subject'] = '33333333-3333-4333-8333-333333333333',
        (d) => d['methods'] = combinedDeviceMethods,
      ]) {
        final changed = response();
        mutate(changed['capabilities']['protected_operations']);
        expect(
          () => ProtectedDeviceDescriptor.fromBorder(
            changed,
            payload,
            cluster: a,
          ),
          throwsFormatException,
        );
      }
    },
  );
  nativeTest(
    'untrusted root, tampering, wrong generation, rollback, retired and certificate expiry refuse',
    () async {
      final descriptor = fixture['descriptors'][0] as Json;
      for (final mutate in <void Function(Json)>[
        (v) => v['anchor_key_id'] = '0' * 64,
        (v) => v['generation'] = '11111111-1111-4111-8111-111111111111',
        (v) => v['manifest']['manifest']['nodes'][0]['endpoints']['https'] =
            'https://attacker.test',
        (v) => v['authority']['state'] = 'retired',
        (v) => v['installation_id'] = '11111111-1111-4111-8111-111111111111',
      ]) {
        final changed = jsonDecode(jsonEncode(descriptor)) as Json;
        mutate(changed);
        await expectLater(binding(changed), throwsA(isA<FormatException>()));
      }
      final updated = await binding(fixture['updated_descriptor']);
      await expectLater(
        binding(descriptor, saved: updated.pin),
        throwsFormatException,
      );
      expect(
        () => clusterCertificateSpki(descriptor['anchor_certificate'], 0),
        throwsFormatException,
      );
    },
  );
  nativeTest(
    'cluster QR pins and pending identity survive cold persistence without token',
    () async {
      final a = await binding(fixture['descriptors'][0]);
      final uri = a.websocketUri;
      final p = EnrollmentQrPayload.parse(
        jsonEncode({
          'border_host': uri.host,
          'claw_domain': uri.host,
          'border_port': uri.port,
          'ws_path': uri.path,
          'installation_id': a.installationId,
          'enrollment_token': 'in2n_fixture',
          'client_nonce': '11111111-1111-4111-8111-111111111111',
          'cluster': {...a.pin.toJson(), 'node_id': a.nodeId},
        }),
      );
      final dir = await Directory.systemTemp.createTemp('r08-mobile-source-');
      addTearDown(() => dir.delete(recursive: true));
      final store = EnrollmentStore(dir);
      await store.save(
        StoredEnrollment(
          memberId: 'device',
          keyFingerprint: 'a' * 64,
          borderHost: uri.host,
          borderPort: uri.port,
          clawDomain: uri.host,
          wsPath: uri.path,
          installationId: a.installationId,
          pending: true,
          clusterPin: p.clusterPin,
          clusterNodeId: p.clusterNodeId,
          clientNonce: p.clientNonce,
        ),
      );
      final retained = (await store.load())!;
      expect(retained.pending, isTrue);
      expect(retained.toPayload().clusterPin!.toJson(), a.pin.toJson());
      expect(
        await File('${dir.path}/ncfed_enrollment.json').readAsString(),
        isNot(contains('in2n_fixture')),
      );
    },
  );
  nativeTest(
    'successor status retains old issuer, decision marker and blocks stale approval',
    () async {
      final a = await binding(fixture['descriptors'][0]),
          b = await binding(fixture['descriptors'][1]);
      final store = MemoryOwnerStore(), first = ClusterTransport(a);
      final ca = CloudOwnerClient(
        CloudProfile(a.origin, a.installationId, cluster: a),
        store: store,
        transport: first,
        expectedDevicePrincipal: devicePrincipal,
      );
      await ca.initialize();
      await ca.prepare(0, 0, 0);
      expect(ca.canDecide('approve'), isTrue);
      final original = ca.reference!;
      final successor = ClusterTransport(b)
        ..epoch = first.epoch + 1
        ..operation = first.operation;
      final cb = CloudOwnerClient(
        CloudProfile(b.origin, b.installationId, cluster: b),
        store: store,
        transport: successor,
        expectedDevicePrincipal: devicePrincipal,
      );
      await cb.initialize();
      expect(cb.reference, original);
      expect(cb.canDecide('approve'), isFalse);
      expect(cb.authorityMessage, contains('stale'));
      expect(successor.calls.every((c) => c.method == 'GET'), isTrue);
      await store.saveReference(cb.profile, {
        ...original,
        'decision_sent': true,
      });
      cb.suspend();
      await cb.resume();
      expect(cb.reference!['decision_sent'], isTrue);
      successor.noQuorum = true;
      await expectLater(cb.status(), throwsA(isA<CloudOwnerError>()));
      expect(cb.reference!['decision_sent'], isTrue);
      expect(cb.canDecide('approve'), isFalse);
    },
  );
  nativeTest(
    'only a verified alternate node can replace the endpoint, retaining device identity',
    () async {
      final a = await binding(fixture['descriptors'][0]),
          b = await binding(fixture['descriptors'][1]);
      final dir = await Directory.systemTemp.createTemp(
        'r08-alternate-source-',
      );
      addTearDown(() => dir.delete(recursive: true));
      final store = EnrollmentStore(dir), uri = a.websocketUri;
      final original = StoredEnrollment(
        memberId: 'device',
        keyFingerprint: 'a' * 64,
        borderHost: uri.host,
        borderPort: uri.port,
        clawDomain: uri.host,
        wsPath: uri.path,
        installationId: a.installationId,
        deviceSubject: devicePrincipal['subject'],
        protectedOrigin: a.origin,
        clusterPin: a.pin,
        clusterNodeId: a.nodeId,
        clusterDescriptor: a.descriptor,
        enrollmentGeneration: '11111111-1111-4111-8111-111111111111',
      );
      await store.save(original);
      var dials = 0;
      Future<EdgeClient> connect(
        EnrollmentQrPayload p, {
        required String memberId,
        required String keyFingerprint,
        required EdgeIdentity identity,
      }) async {
        dials++;
        expect(memberId, original.memberId);
        expect(keyFingerprint, original.keyFingerprint);
        expect(p.enrollmentToken, isEmpty);
        expect(p.clusterNodeId, b.nodeId);
        expect(p.expectedDeviceSubject, original.deviceSubject);
        final channel = TestChannel();
        addTearDown(() => channel.input.close());
        final edge = EdgeClient.forTesting(channel)
          ..clusterBinding = b
          ..enrollFingerprint = keyFingerprint;
        edge.protectedDevice = ProtectedDeviceDescriptor(
          b.installationId,
          b.origin,
          devicePrincipal,
          cluster: b,
          enrollmentGeneration: original.enrollmentGeneration,
        );
        return edge;
      }

      await expectLater(
        replaceClusterEndpoint(
          store: store,
          expected: original,
          nodeId: '11111111-1111-4111-8111-111111111111',
          identity: RetainedIdentity(),
          reconnect: connect,
          crypto: nativeCrypto,
        ),
        throwsFormatException,
      );
      expect(dials, 0);
      final next = await replaceClusterEndpoint(
        store: store,
        expected: original,
        nodeId: b.nodeId,
        identity: RetainedIdentity(),
        reconnect: connect,
        crypto: nativeCrypto,
      );
      expect(next.memberId, original.memberId);
      expect(next.deviceSubject, original.deviceSubject);
      expect(next.keyFingerprint, original.keyFingerprint);
      expect(next.endpointRevision, 1);
      expect(next.clusterPin!.sameAudience(original.clusterPin!), isTrue);
      expect((await store.load())!.clusterNodeId, b.nodeId);
      expect(dials, 1);
      await expectLater(
        replaceClusterEndpoint(
          store: store,
          expected: original,
          nodeId: b.nodeId,
          identity: RetainedIdentity(),
          reconnect: connect,
          crypto: nativeCrypto,
          isCurrent: () => false,
        ),
        throwsStateError,
      );
      expect(dials, 1);
    },
  );
}
