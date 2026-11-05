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
import 'package:netclaw_mobile/main.dart' as production;
import 'package:netclaw_mobile/screens/protected_device_screen.dart';
import 'package:netclaw_mobile/ncfed/heartbeat.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/screens/cloud_owner_screen.dart';

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

class NativeLifecycleWitness extends WidgetsBindingObserver {
  final states = <String>[];
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    states.add(state.name);
  }
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
        [
          'enroll',
          'recover-enrollment',
          'prepare',
          'approve',
          'recover',
        ].contains(phase),
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
      await tester.runAsync(() async {
        final retained = await store.load();
        require(
          phase == 'enroll' ? retained == null : retained != null,
          phase == 'enroll'
              ? 'Existing enrollment must be preserved'
              : 'Enrollment missing; never reenroll during recovery',
        );
      });
      Future<void> waitFor(bool Function() ready, String reason) async {
        final deadline = DateTime.now().add(const Duration(seconds: 60));
        while (!ready()) {
          require(DateTime.now().isBefore(deadline), reason);
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 100)),
          );
          await tester.pump(const Duration(milliseconds: 100));
        }
      }

      await tester.pumpWidget(
        MaterialApp(
          home: production.EnrollmentGate(
            documentsDirectory: () async => profileDir,
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
      if (phase == 'enroll') {
        await waitFor(
          () => find.byType(CheckboxListTile).evaluate().isNotEmpty,
          'Onboarding did not appear',
        );
        await tester.ensureVisible(find.byType(CheckboxListTile));
        await tester.tap(find.byType(CheckboxListTile));
        await tester.pump();
        await tester.ensureVisible(find.text('Agree and Continue'));
        await tester.tap(find.text('Agree and Continue'));
        await tester.pump();
        await tester.tap(find.text('Scan QR image'));
      }
      await waitFor(
        () =>
            find.byType(production.HomeShell).evaluate().isNotEmpty ||
            find.byType(ProtectedDeviceScreen).evaluate().isNotEmpty,
        'Enrollment gate did not navigate to the enrolled home',
      );
      final protected = find
          .byType(ProtectedDeviceScreen)
          .evaluate()
          .isNotEmpty;
      edge = protected
          ? tester
                .widget<ProtectedDeviceScreen>(
                  find.byType(ProtectedDeviceScreen),
                )
                .edge
          : tester
                .widget<production.HomeShell>(find.byType(production.HomeShell))
                .client;
      final client = edge;
      wireHeartbeat(client);
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
      var visualFrames = 0;
      final nativeLifecycle = <String>[];
      if (client.protectedDevice != null) {
        await waitFor(
          () => find.byType(CloudOwnerScreen).evaluate().isNotEmpty,
          'Protected enrolled home did not load operations',
        );
        final operations = tester
            .widget<CloudOwnerScreen>(find.byType(CloudOwnerScreen))
            .initialClient!;
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
        if (config['lifecycle_evidence'] == true) {
          require(
            phase == 'recover',
            'Lifecycle proof only recovers a terminal operation',
          );
          final before = operations.operation!;
          final witness = NativeLifecycleWitness();
          WidgetsBinding.instance.addObserver(witness);
          try {
            final ready = File('${directory.path}/r04b-lifecycle-ready.json');
            final resumed = File('${directory.path}/r04b-lifecycle-continue');
            final lifecycleFinished = await tester.runAsync<bool>(() async {
              require(
                !await ready.exists() && !await resumed.exists(),
                'Stale lifecycle handshake',
              );
              await ready.writeAsString(
                jsonEncode({'profile': profileName}),
                flush: true,
              );
              final deadline = DateTime.now().add(const Duration(seconds: 180));
              while (!await resumed.exists()) {
                require(
                  DateTime.now().isBefore(deadline),
                  'Native lifecycle driver did not return',
                );
                await Future<void>.delayed(const Duration(milliseconds: 100));
              }
              await ready.delete();
              await resumed.delete();
              return true;
            });
            require(
              lifecycleFinished == true,
              'Native lifecycle qualification failed',
            );
            await waitFor(
              () =>
                  !operations.busy &&
                  operations.operationsReady &&
                  !client.isClosed,
              'Same-device foreground recovery did not finish',
            );
            require(
              witness.states.contains('paused') &&
                  witness.states.contains('resumed'),
              'Actual native background/resume events missing',
            );
            require(
              operations.operation?['operation_id'] == before['operation_id'] &&
                  operations.operation?['result']?['digest'] ==
                      before['result']['digest'] &&
                  operations.operation?['attempt_count'] ==
                      before['attempt_count'],
              'Lifecycle recovery changed the retained operation',
            );
            nativeLifecycle.addAll(witness.states);
          } finally {
            WidgetsBinding.instance.removeObserver(witness);
          }
        }
        operation = operations.operation;
      }
      if (config['visual_evidence'] == true) {
        final visualLabel =
            config['visual_label'] as String? ?? '$profileName-$phase';
        require(
          RegExp(r'^[a-z0-9-]{1,100}$').hasMatch(visualLabel),
          'Invalid visual label',
        );
        await tester.pump(const Duration(milliseconds: 200));
        require(
          find.byType(Scrollable).evaluate().isNotEmpty,
          'Native screen is no longer mounted',
        );
        var scroll = tester.state<ScrollableState>(
          find.byType(Scrollable).first,
        );
        scroll.position.jumpTo(0);
        await tester.pump(const Duration(milliseconds: 200));
        while (true) {
          require(visualFrames < 40, 'Visual evidence bound exceeded');
          final ready = File('${directory.path}/r04b-visual-ready.json');
          final resume = File('${directory.path}/r04b-visual-continue');
          final captured = await tester.runAsync<bool>(() async {
            require(
              !await ready.exists() && !await resume.exists(),
              'Stale visual handshake; inspect before continuing',
            );
            await ready.writeAsString(
              jsonEncode({'label': visualLabel, 'frame': visualFrames}),
              flush: true,
            );
            final deadline = DateTime.now().add(const Duration(seconds: 45));
            while (!await resume.exists()) {
              require(
                DateTime.now().isBefore(deadline),
                'Native screenshot not acknowledged',
              );
              await Future<void>.delayed(const Duration(milliseconds: 100));
            }
            await ready.delete();
            await resume.delete();
            return true;
          });
          require(captured == true, 'Native visual qualification failed');
          await tester.pump(const Duration(milliseconds: 100));
          require(
            find.byType(Scrollable).evaluate().isNotEmpty,
            'Native screen disposed during capture',
          );
          scroll = tester.state<ScrollableState>(find.byType(Scrollable).first);
          visualFrames++;
          if (scroll.position.pixels >= scroll.position.maxScrollExtent - 1) {
            break;
          }
          final next =
              (scroll.position.pixels + scroll.position.viewportDimension * .75)
                  .clamp(0.0, scroll.position.maxScrollExtent);
          scroll.position.jumpTo(next);
          await tester.pump(const Duration(milliseconds: 200));
        }
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
          'production_enrollment_gate': true,
          'native_visual_frames': visualFrames,
          'native_lifecycle_events': nativeLifecycle,
          'landing': protected ? 'ProtectedDeviceScreen' : 'HomeShell',
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
