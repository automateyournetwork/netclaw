import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_qr_payload.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/ncfed/heartbeat.dart';

/// Read-only binding/scope probes on an already enrolled native device.
/// Never issues or consumes enrollment, generates a key, or prepares an operation.
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'native protected identity and method boundaries',
    (tester) async {
      await tester.runAsync(() async {
        final directory = await getApplicationDocumentsDirectory();
        final file = File('${directory.path}/r04b-qualification.json');
        final deadline = DateTime.now().add(const Duration(minutes: 5));
        while (!await file.exists()) {
          if (DateTime.now().isAfter(deadline)) {
            throw StateError('Missing private configuration');
          }
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        final config =
            jsonDecode(await file.readAsString()) as Map<String, dynamic>;
        await file.delete();
        final profile = config['profile'] as String;
        if (!RegExp(r'^[a-z0-9-]{1,64}$').hasMatch(profile)) {
          throw StateError('Invalid profile');
        }
        final profileDirectory = Directory('${directory.path}/$profile');
        final retainedFile = File(
          '${profileDirectory.path}/ncfed_enrollment.json',
        );
        final before = await retainedFile.readAsString();
        final saved = (await EnrollmentStore(profileDirectory).load())!;
        if (!saved.protected || saved.pending) {
          throw StateError('A confirmed protected enrollment is required');
        }
        final results = <Map<String, dynamic>>[];
        Map<String, dynamic> refused(Object error) => {
          'type': error.runtimeType.toString(),
          if (error is EdgeClientException) ...{
            'rpc_code': error.code,
            'code': error.data?['code'],
            'status': error.data?['status'],
          },
        };
        for (final probe in ['wrong-installation', 'wrong-key-fingerprint']) {
          final payload = saved.toPayload();
          final wrong = EnrollmentQrPayload(
            borderHost: payload.borderHost,
            borderPort: payload.borderPort,
            clawDomain: payload.clawDomain,
            enrollmentToken: '',
            wsPath: payload.wsPath,
            installationId: probe == 'wrong-installation'
                ? '00000000-0000-4000-8000-000000000000'
                : payload.installationId,
            expectedDeviceSubject: payload.expectedDeviceSubject,
          );
          Object? error;
          EdgeClient? unexpected;
          try {
            unexpected = await EdgeClient.reconnect(
              wrong,
              memberId: saved.memberId,
              keyFingerprint: probe == 'wrong-key-fingerprint'
                  ? List.filled(64, '0').join()
                  : saved.keyFingerprint,
              identity: const EdgeIdentity(),
            );
          } catch (e) {
            error = e;
          } finally {
            await unexpected?.close();
          }
          expect(error, isNotNull, reason: 'Altered binding must refuse');
          expect(
            error is EdgeClientException || error is FormatException,
            isTrue,
          );
          results.add({'probe': probe, 'refusal': refused(error!)});
        }
        final edge = await EdgeClient.reconnect(
          saved.toPayload(),
          memberId: saved.memberId,
          keyFingerprint: saved.keyFingerprint,
          identity: const EdgeIdentity(),
        );
        wireHeartbeat(edge);
        try {
          expect(edge.protectedDevice, isNotNull);
          expect(edge.enrollFingerprint, saved.keyFingerprint);
          for (final method in [
            'n2n/edge/operations/revoke',
            'n2n/edge/qualification_forbidden',
          ]) {
            EdgeClientException? refusal;
            try {
              await edge.call(method, {
                'installation_id': saved.installationId,
              }, timeout: const Duration(seconds: 10));
            } on EdgeClientException catch (error) {
              refusal = error;
            }
            expect(refusal, isNotNull);
            expect(refusal!.code, isNot('timeout'));
            expect(refusal.code, isNot('connection_error'));
            results.add({'probe': method, 'refusal': refused(refusal)});
          }
        } finally {
          await edge.close();
        }
        await edge.reconnectInPlace(
          saved.toPayload(),
          memberId: saved.memberId,
          keyFingerprint: saved.keyFingerprint,
        );
        expect(edge.protectedDevice, isNotNull);
        expect(edge.enrollFingerprint, saved.keyFingerprint);
        await edge.close();
        expect(await retainedFile.readAsString(), before);
        binding.reportData = {
          'r04b_evidence': {
            'phase': 'binding-refusals',
            'profile': profile,
            'results': results,
            'successful_enrollment_unchanged': true,
            'valid_same_key_hello_recovered': true,
            'operation_requests': 0,
            'simulator': true,
            'camera_hardware': false,
            'secure_enclave': false,
            'observed_at': DateTime.now().toUtc().toIso8601String(),
          },
        };
      });
    },
    timeout: const Timeout(Duration(minutes: 8)),
  );
}
