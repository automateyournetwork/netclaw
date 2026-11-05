import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_flow.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';

/// Uses an actual previously displayed QR image and the native device identity.
/// The owner supplies an isolated probe directory; successful profiles stay intact.
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'actual spent QR and mutated domain refuse without enrollment',
    (tester) async {
      await tester.runAsync(() async {
        final directory = await getApplicationDocumentsDirectory();
        final configFile = File('${directory.path}/r04b-qualification.json');
        final deadline = DateTime.now().add(const Duration(minutes: 5));
        while (!await configFile.exists()) {
          if (DateTime.now().isAfter(deadline)) {
            throw StateError('Missing private config');
          }
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        final config =
            jsonDecode(await configFile.readAsString()) as Map<String, dynamic>;
        await configFile.delete();
        final profile = config['profile'] as String;
        if (!RegExp(r'^[a-z0-9-]{1,64}$').hasMatch(profile)) {
          throw StateError('Invalid profile');
        }
        final retainedFile = File(
          '${directory.path}/$profile/ncfed_enrollment.json',
        );
        final retainedBefore = await retainedFile.readAsString();
        final decoded = await const MethodChannel('netclaw.r04b/qr_image')
            .invokeMapMethod<String, dynamic>('decodeQrImage', {
              'path': '${directory.path}/${config['image_file']}',
            });
        final raw = decoded!['raw'] as String;
        final mutated = jsonDecode(raw) as Map<String, dynamic>;
        mutated['border_host'] = 'mismatched.invalid';
        final results = <Map<String, dynamic>>[];
        for (final probe in ['spent-and-expired', 'wrong-domain-mutation']) {
          final dir = Directory('${directory.path}/refusal-$profile-$probe');
          if (await dir.exists()) {
            throw StateError('Probe already used; inspect instead of repeat');
          }
          await dir.create();
          final store = EnrollmentStore(dir);
          var dials = 0;
          Map<String, dynamic>? nativeError;
          final outcome = await attemptEnrollmentFromQr(
            probe == 'spent-and-expired' ? raw : jsonEncode(mutated),
            memberId: 'risk/refusal-$profile-$probe',
            identity: const EdgeIdentity(),
            store: store,
            enroll:
                (
                  payload, {
                  required memberId,
                  required identity,
                  displayName,
                }) async {
                  dials++;
                  try {
                    return await EdgeClient.enroll(
                      payload,
                      memberId: memberId,
                      identity: identity,
                      displayName: displayName,
                    );
                  } on EdgeClientException catch (error) {
                    nativeError = {
                      'rpc_code': error.code,
                      'code': error.data?['code'],
                      'status': error.data?['status'],
                      'admission': error.data?['admission'],
                      'member_id': error.data?['member_id'],
                      'key_fingerprint': error.data?['key_fingerprint'],
                    };
                    rethrow;
                  }
                },
          );
          if (outcome is EnrollmentSuccess) {
            await outcome.client.close();
            throw StateError('Unexpected enrollment success');
          }
          final failure = outcome as EnrollmentFailure;
          final retained = await store.load();
          expect(failure.pending, isFalse);
          expect(retained, isNull);
          expect(dials, probe == 'spent-and-expired' ? 1 : 0);
          if (probe == 'spent-and-expired') {
            expect(nativeError?['code'], 'enrollment_refused');
            expect(nativeError?['admission'], 'not_enrolled');
          } else {
            expect(failure.message, contains('wrong Border'));
          }
          results.add({
            'probe': probe,
            'native_error': nativeError,
            'dials': dials,
            'pending': failure.pending,
            'retained_probe_enrollment': false,
            'message': failure.message,
          });
        }
        expect(await retainedFile.readAsString(), retainedBefore);
        binding.reportData = {
          'r04b_evidence': {
            'phase': 'refusals',
            'profile': profile,
            'results': results,
            'successful_enrollment_unchanged': true,
            'decoder': {...decoded}..remove('raw'),
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
