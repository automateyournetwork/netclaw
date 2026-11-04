import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:path_provider/path_provider.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/ncfed/protected_device_client.dart';
import 'package:netclaw_mobile/screens/cloud_owner_screen.dart';
import 'package:netclaw_mobile/screens/enrollment_screen.dart';

dynamic ordered(dynamic x) => x is Map
    ? {
        for (final k in (x.keys.cast<String>().toList()..sort()))
          k: ordered(x[k]),
      }
    : x is List
    ? x.map(ordered).toList()
    : x;
void require(bool ok, String reason) {
  if (!ok) throw StateError(reason);
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'actual QR image to enrolled device and protected operations',
    (tester) async {
      late Directory directory;
      late Json config;
      await tester.runAsync(() async {
        directory = await getApplicationDocumentsDirectory();
        final file = File('${directory.path}/r04b-qualification.json');
        final deadline = DateTime.now().add(const Duration(minutes: 5));
        while (!await file.exists()) {
          require(
            DateTime.now().isBefore(deadline),
            'Private configuration not supplied',
          );
          await Future<void>.delayed(const Duration(milliseconds: 250));
        }
        final bytes = await file.readAsBytes();
        await file.delete();
        require(bytes.length <= 65536, 'Configuration bound exceeded');
        config = jsonDecode(utf8.decode(bytes)) as Json;
      });
      final phase = config['phase'];
      require(
        ['enroll', 'prepare', 'approve', 'recover'].contains(phase),
        'Invalid phase',
      );
      final profileName = config['profile'];
      require(
        profileName is String &&
            RegExp(r'^[a-z0-9-]{1,64}$').hasMatch(profileName),
        'Invalid private profile',
      );
      final profileDir = Directory('${directory.path}/$profileName');
      await tester.runAsync(() => profileDir.create(recursive: true));
      final store = EnrollmentStore(profileDir);
      EdgeClient? edge;
      Json? decoder;
      if (phase == 'enroll') {
        await tester.runAsync(() async {
          require(
            await store.load() == null,
            'Existing enrollment must be preserved',
          );
        });
        final complete = Completer<EdgeClient>();
        await tester.pumpWidget(
          MaterialApp(
            home: EnrollmentScreen(
              memberId: config['member_id'] as String,
              store: store,
              onEnrolled: (client, payload) {
                complete.complete(client);
              },
              scannerBuilder: (onDetected) => Center(
                child: FilledButton(
                  onPressed: () async {
                    final decoded =
                        await const MethodChannel(
                          'netclaw.r04b/qr_image',
                        ).invokeMapMethod<String, dynamic>('decodeQrImage', {
                          'path': '${directory.path}/${config['image_file']}',
                        });
                    require(
                      decoded != null && decoded['raw'] is String,
                      'Actual image did not decode',
                    );
                    decoder = {...decoded!}..remove('raw');
                    await onDetected(
                      BarcodeCapture(
                        barcodes: [
                          Barcode(
                            rawValue: decoded['raw'],
                            format: BarcodeFormat.qrCode,
                          ),
                        ],
                      ),
                    );
                  },
                  child: const Text('Scan QR image'),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.text('Scan QR image'));
        await tester.runAsync(() async {
          edge = await complete.future.timeout(const Duration(seconds: 45));
        });
        await tester.pumpAndSettle();
      } else {
        await tester.runAsync(() async {
          final saved = await store.load();
          require(
            saved != null,
            'Enrollment missing; never reenroll during recovery',
          );
          edge = await EdgeClient.reconnect(
            saved!.toPayload(),
            memberId: saved.memberId,
            keyFingerprint: saved.keyFingerprint,
            identity: const EdgeIdentity(),
          );
        });
      }
      final client = edge!;
      StoredEnrollment? saved;
      await tester.runAsync(() async {
        saved = await store.load();
      });
      require(
        saved != null && client.enrollFingerprint == saved!.keyFingerprint,
        'Retained identity mismatch',
      );
      if (config['installation_id'] != null) {
        require(
          client.border['installation_id'] == config['installation_id'],
          'Wrong installation',
        );
      }
      Json? operation;
      if (client.protectedDevice != null) {
        final operations = protectedDeviceClient(client);
        await tester.runAsync(operations.initialize);
        await tester.pumpWidget(
          MaterialApp(
            home: CloudOwnerScreen(initialClient: operations, deviceMode: true),
          ),
        );
        await tester.pumpAndSettle();
        Future<void> tap(String label) async {
          final finder = find.text(label);
          require(
            finder.evaluate().length == 1,
            'Required native action missing',
          );
          await tester.ensureVisible(finder);
          await tester.tap(finder);
          await tester.pump();
          final deadline = DateTime.now().add(const Duration(seconds: 90));
          while (operations.busy) {
            require(DateTime.now().isBefore(deadline), 'Native action timeout');
            await tester.runAsync(
              () => Future<void>.delayed(const Duration(milliseconds: 100)),
            );
            await tester.pump();
          }
          await tester.pumpAndSettle();
        }

        if (phase == 'prepare') {
          require(
            operations.reference == null,
            'Existing operation must be recovered',
          );
          final members = operations.catalog!['members'] as List;
          final wanted = config['member_id'];
          final index = members.indexWhere(
            (m) => m['member']['member_id'] == wanted,
          );
          require(index >= 0, 'Selected member missing');
          // Native dropdowns choose only the exact independently selected catalog profile.
          final memberKey = ValueKey('members-${operations.profile.key}');
          await tester.tap(find.byKey(memberKey));
          await tester.pumpAndSettle();
          await tester.tap(find.text(wanted).last);
          await tester.pumpAndSettle();
          final models = members[index]['model_profiles'] as List,
              tools = members[index]['tools'] as List;
          final mi = models.indexWhere(
            (m) => m['profile_id'] == config['model_profile_id'],
          );
          final ti = tools.indexWhere(
            (t) =>
                t['tool'] == config['tool'] &&
                jsonEncode(ordered(t['arguments'])) ==
                    jsonEncode(ordered(config['arguments'])),
          );
          require(mi >= 0 && ti >= 0, 'Exact selected model/tool missing');
          if (mi != 0) {
            await tester.tap(find.byKey(ValueKey('models-$index')));
            await tester.pumpAndSettle();
            await tester.tap(
              find
                  .text(
                    '${models[mi]['profile_id']} · ${models[mi]['provider']} / ${models[mi]['model']}',
                  )
                  .last,
            );
            await tester.pumpAndSettle();
          }
          if (ti != 0) {
            await tester.tap(find.byKey(ValueKey('tools-$index')));
            await tester.pumpAndSettle();
            await tester.tap(
              find
                  .text('${tools[ti]['tool']} · ${tools[ti]['device_ref']}')
                  .last,
            );
            await tester.pumpAndSettle();
          }
          await tap('Prepare review');
          require(
            operations.operation != null,
            'Prepare returned no retained review',
          );
        } else if (phase == 'approve' || phase == 'recover') {
          final op = operations.operation;
          require(
            op != null &&
                op['operation_id'] == config['operation_id'] &&
                op['review_digest'] == config['review_digest'] &&
                jsonEncode(ordered(op['review'])) ==
                    jsonEncode(ordered(config['review'])),
            'Exact reviewed operation mismatch',
          );
          if (phase == 'approve') {
            final checkbox = find.byKey(
              const ValueKey('cloud-review-confirmation'),
            );
            await tester.ensureVisible(checkbox);
            await tester.tap(checkbox);
            await tester.pumpAndSettle();
            await tap('Approve once');
            final deadline = DateTime.now().add(const Duration(minutes: 3));
            while (operations.operation?['result']?['durable_ack'] != true ||
                operations.operation?['result']?['ack_delivery_pending'] ==
                    true) {
              require(
                DateTime.now().isBefore(deadline),
                'Signed result/ACK wait expired; recover same operation',
              );
              await tester.runAsync(
                () => Future<void>.delayed(const Duration(seconds: 2)),
              );
              await tap('Reconcile existing operation');
            }
          } else {
            require(
              op!['result']?['verified'] == true &&
                  op['result']?['durable_ack'] == true &&
                  op['result']?['ack_delivery_pending'] == false,
              'Recovered result/ACK not complete',
            );
          }
        }
        operation = operations.operation;
      }
      // A real reconnect on the same socket owner/key, never another enrollment.
      await tester.runAsync(() async {
        await client.close();
        await client.reconnectInPlace(
          saved!.toPayload(),
          memberId: saved!.memberId,
          keyFingerprint: saved!.keyFingerprint,
        );
      });
      require(
        client.enrollFingerprint == saved!.keyFingerprint,
        'Reconnect changed identity',
      );
      binding.reportData = {
        'r04b_evidence': {
          'phase': phase,
          'profile': profileName,
          'enrollment': saved!.toJson(),
          'border': client.border,
          'decoder': decoder,
          'operation': operation,
          'same_key_reconnect': true,
          'simulator': true,
          'camera_hardware': false,
          'secure_enclave': false,
          'observed_at': DateTime.now().toUtc().toIso8601String(),
        },
      };
      await tester.runAsync(client.close);
    },
    timeout: const Timeout(Duration(minutes: 10)),
  );
}
