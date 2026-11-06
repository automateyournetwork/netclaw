import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/main.dart' show EnrollmentGate;
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/endpoint_recovery.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/ncfed/protected_device_descriptor.dart';
import 'package:netclaw_mobile/screens/endpoint_recovery_screen.dart';
import 'edge_client_lifecycle_test.dart' show TestChannel;

const installation = '11111111-1111-4111-8111-111111111111';
const subject = '22222222-2222-4222-8222-222222222222';

class Identity extends EdgeIdentity {
  @override
  Future<String> publicKeyFingerprint() async => 'a' * 64;
}

StoredEnrollment retained({bool protected = true, int revision = 0}) =>
    StoredEnrollment(
      memberId: 'risk/retained',
      keyFingerprint: 'a' * 64,
      borderHost: 'border.example.test',
      borderPort: 8443,
      clawDomain: 'border.example.test',
      installationId: installation,
      wsPath: protected ? '/mobile/ws' : '/',
      deviceSubject: protected ? subject : null,
      protectedOrigin: protected ? 'https://border.example.test' : null,
      endpointRevision: revision,
    );
EdgeClient probe(
  StoredEnrollment enrollment, {
  String? otherInstallation,
  String? otherSubject,
  String? otherOrigin,
}) {
  final channel = TestChannel();
  final client = EdgeClient.forTesting(channel)
    ..enrollFingerprint = enrollment.keyFingerprint
    ..border = {'installation_id': otherInstallation ?? installation};
  if (enrollment.protected) {
    client.protectedDevice = ProtectedDeviceDescriptor(
      otherInstallation ?? installation,
      otherOrigin ?? enrollment.protectedOrigin!,
      {
        'issuer': 'device-key',
        'subject': otherSubject ?? subject,
        'display_name': 'Retained phone',
        'roles': ['device-operator'],
      },
    );
  }
  addTearDown(() async {
    await client.close();
    await channel.input.close();
  });
  return client;
}

void main() {
  late Directory directory;
  late EnrollmentStore store;
  setUp(() async {
    directory = await Directory.systemTemp.createTemp('r07-mobile-');
    store = EnrollmentStore(directory);
  });
  tearDown(() => directory.delete(recursive: true));
  for (final protected in [true, false]) {
    test(
      'verified ${protected ? 'protected' : 'ordinary'} port update changes only routing/revision',
      () async {
        final original = retained(protected: protected);
        await store.save(original);
        final reference = File('${directory.path}/unchanged-reference.json');
        await reference.writeAsString(
          '{"operation_id":"original","decision_sent":true}',
        );
        final before = await reference.readAsString();
        var calls = 0;
        final client = probe(original);
        final updated = await replaceEnrollmentPort(
          store: store,
          expected: original,
          port: 9443,
          identity: Identity(),
          reconnect:
              (
                payload, {
                required memberId,
                required keyFingerprint,
                required identity,
              }) async {
                calls++;
                expect(
                  payload.websocketUri.toString(),
                  'wss://border.example.test:9443${original.wsPath}',
                );
                expect(payload.enrollmentToken, isEmpty);
                expect(memberId, original.memberId);
                expect(keyFingerprint, original.keyFingerprint);
                return client;
              },
        );
        expect(calls, 1);
        expect(client.isClosed, isTrue);
        expect(updated.toJson(), {
          ...original.toJson(),
          'border_port': 9443,
          'endpoint_revision': 1,
        });
        expect((await store.load())!.toJson(), updated.toJson());
        expect(await reference.readAsString(), before);
      },
    );
  }
  for (final refusal in [
    'installation',
    'principal',
    'origin',
    'revoked',
    'tls',
    'suspended',
    'stale',
  ]) {
    test('$refusal refuses without replacing saved enrollment', () async {
      final original = retained();
      await store.save(original);
      var current = true;
      final unchanged = jsonEncode(original.toJson());
      await expectLater(
        replaceEnrollmentPort(
          store: store,
          expected: original,
          port: 9443,
          identity: Identity(),
          isCurrent: () => current,
          reconnect:
              (
                payload, {
                required memberId,
                required keyFingerprint,
                required identity,
              }) async {
                if (refusal == 'revoked') {
                  throw EdgeClientException('-32023', 'refused');
                }
                if (refusal == 'tls') {
                  throw const HandshakeException('untrusted');
                }
                if (refusal == 'suspended') current = false;
                if (refusal == 'stale') await store.save(retained(revision: 5));
                return probe(
                  original,
                  otherInstallation: refusal == 'installation'
                      ? '33333333-3333-4333-8333-333333333333'
                      : null,
                  otherSubject: refusal == 'principal'
                      ? '44444444-4444-4444-8444-444444444444'
                      : null,
                  otherOrigin: refusal == 'origin'
                      ? 'https://border.example.test:9443'
                      : null,
                );
              },
        ),
        throwsA(anything),
      );
      expect(
        jsonEncode((await store.load())!.toJson()),
        refusal == 'stale'
            ? jsonEncode(retained(revision: 5).toJson())
            : unchanged,
      );
    });
  }
  test('two probes cannot overwrite each other with stale revision', () async {
    final original = retained();
    await store.save(original);
    final gate = Completer<void>();
    var called = 0;
    Future<StoredEnrollment> update(int port) => replaceEnrollmentPort(
      store: store,
      expected: original,
      port: port,
      identity: Identity(),
      reconnect:
          (
            payload, {
            required memberId,
            required keyFingerprint,
            required identity,
          }) async {
            if (++called == 2) gate.complete();
            await gate.future;
            return probe(original);
          },
    );
    final outcomes = await Future.wait([
      update(9443).then<Object>((v) => v).catchError((Object e) => e),
      update(10443).then<Object>((v) => v).catchError((Object e) => e),
    ]);
    expect(outcomes.whereType<StoredEnrollment>(), hasLength(1));
    expect(outcomes.whereType<StateError>(), hasLength(1));
    expect((await store.load())!.endpointRevision, 1);
  });
  test(
    'suspension after temporary write prevents atomic endpoint commit',
    () async {
      final original = retained();
      await store.save(original);
      final replacement = StoredEnrollment.fromJson({
        ...original.toJson(),
        'border_port': 9443,
        'endpoint_revision': 1,
      });
      var checks = 0;
      await expectLater(
        store.replaceEndpoint(
          original,
          replacement,
          isCurrent: () => ++checks == 1,
        ),
        throwsStateError,
      );
      expect((await store.load())!.toJson(), original.toJson());
      expect(
        File('${directory.path}/ncfed_enrollment.json.pending').existsSync(),
        isFalse,
      );
      expect(checks, 2);
    },
  );
  test(
    'suspended writer queued behind another update cannot replace endpoint',
    () async {
      final original = retained();
      await store.save(original);
      final blocked = BlockingStore(directory);
      final first = blocked.replaceEndpoint(original, retained(revision: 1));
      await blocked.started.future;
      var active = true;
      final second = expectLater(
        store.replaceEndpoint(
          original,
          retained(revision: 2),
          isCurrent: () => active,
        ),
        throwsStateError,
      );
      active = false;
      blocked.release.complete();
      await first;
      await second;
      expect((await store.load())!.endpointRevision, 1);
    },
  );
  testWidgets('cold reconnect cannot overwrite a newer committed endpoint', (
    tester,
  ) async {
    final original = retained();
    await tester.runAsync(() => store.save(original));
    final reply = Completer<EdgeClient>();
    var dialed = false;
    final oldClient = probe(original);
    await tester.pumpWidget(
      MaterialApp(
        home: EnrollmentGate(
          documentsDirectory: () async => directory,
          reconnect:
              (
                payload, {
                required memberId,
                required keyFingerprint,
                required identity,
              }) {
                dialed = true;
                return reply.future;
              },
        ),
      ),
    );
    for (var n = 0; n < 50 && !dialed; n++) {
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      await tester.pump();
    }
    expect(dialed, isTrue);
    final updated = StoredEnrollment.fromJson({
      ...original.toJson(),
      'border_port': 9443,
      'endpoint_revision': 1,
    });
    await tester.runAsync(() => store.replaceEndpoint(original, updated));
    reply.complete(oldClient);
    for (var n = 0; n < 50 && !oldClient.isClosed; n++) {
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      await tester.pump();
    }
    expect(oldClient.isClosed, isTrue);
    expect(
      (await tester.runAsync(() => store.load()))!.toJson(),
      updated.toJson(),
    );
    for (
      var n = 0;
      n < 50 && find.textContaining('preserved').evaluate().isEmpty;
      n++
    ) {
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      await tester.pump();
    }
    expect(find.textContaining('preserved'), findsOneWidget);
  });
  testWidgets('native form accepts only an explicit verified port', (
    tester,
  ) async {
    final original = retained();
    final memory = MemoryEnrollmentStore(directory, original);
    final ready = probe(original);
    var done = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: EndpointRecoveryScreen(
          store: memory,
          enrollment: original,
          identity: Identity(),
          onReconnect: () => done++,
          reconnect:
              (
                payload, {
                required memberId,
                required keyFingerprint,
                required identity,
              }) async => ready,
        ),
      ),
    );
    expect(done, 0);
    await tester.enterText(find.byType(TextField), '9443');
    await tester.runAsync(() async {
      await tester.tap(find.text('Verify and update port'));
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await tester.pumpAndSettle();
    expect(
      done,
      1,
      reason: tester
          .widgetList<Text>(find.byType(Text))
          .map((e) => e.data)
          .join('|'),
    );
    expect(memory.value.borderPort, 9443);
  });
}

class BlockingStore extends EnrollmentStore {
  final started = Completer<void>(), release = Completer<void>();
  BlockingStore(super.directory);
  @override
  Future<StoredEnrollment?> load() async {
    started.complete();
    await release.future;
    return super.load();
  }
}

class MemoryEnrollmentStore extends EnrollmentStore {
  StoredEnrollment value;
  MemoryEnrollmentStore(super.directory, this.value);
  @override
  Future<void> replaceEndpoint(
    StoredEnrollment expected,
    StoredEnrollment next, {
    bool Function()? isCurrent,
  }) async {
    if (isCurrent?.call() == false) throw StateError('suspended');
    value = next;
  }
}
