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
          'combined-prepare',
          'combined-decision',
          'combined-recover',
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
      Json? operation,
          combined,
          combinedReference,
          archivedOperation,
          archivedCombined;
      bool? combinedUncertain;
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
        if (phase == 'combined-prepare') {
          final retained = config['archive_resolved_reference'];
          if (retained != null) {
            final old = operations.operation;
            require(
              retained is Map &&
                  old != null &&
                  operations.canRemove &&
                  old['state'] == 'completed' &&
                  old['operation_id'] == retained['operation_id'] &&
                  old['review_digest'] == retained['review_digest'] &&
                  old['result']?['digest'] == retained['result_digest'] &&
                  old['result']?['verified'] == true &&
                  old['result']?['durable_ack'] == true &&
                  old['result']?['ack_delivery_pending'] == false,
              'Only the exact inspected completed receipt may be archived',
            );
            archivedOperation = old;
            await tester.runAsync(() async {
              final archive = File(
                '${profileDir.path}/r05-resolved-${old!['operation_id']}.json',
              );
              require(
                !await archive.exists(),
                'Archive already exists; inspect outcome',
              );
              await archive.writeAsString(jsonEncode(old), flush: true);
            });
            await tap('Remove resolved reference');
          }
          final retainedPair = config['archive_combined'];
          if (retainedPair != null) {
            final old = operations.combined;
            require(
              retainedPair is Map &&
                  old != null &&
                  operations.canRemoveCombined &&
                  old['state'] == 'complete' &&
                  old['parent_id'] == retainedPair['parent_id'] &&
                  old['client_nonce'] == retainedPair['client_nonce'],
              'Only the exact inspected completed pair may be archived',
            );
            for (final index in [0, 1]) {
              final child = old!['children'][index],
                  expected = retainedPair['children'][index];
              require(
                child['operation_id'] == expected['operation_id'] &&
                    child['review_digest'] == expected['review_digest'] &&
                    jsonEncode(ordered(child['review'])) ==
                        jsonEncode(ordered(expected['review'])) &&
                    child['result']?['digest'] ==
                        expected['result']?['digest'] &&
                    child['result']?['verified'] == true &&
                    child['result']?['durable_ack'] == true &&
                    child['result']?['ack_delivery_pending'] == false,
                'Completed child evidence changed; retain reference',
              );
            }
            archivedCombined = old;
            await tester.runAsync(() async {
              final archive = File(
                '${profileDir.path}/r05-combined-${old!['parent_id']}.json',
              );
              require(
                !await archive.exists(),
                'Pair archive already exists; inspect outcome',
              );
              await archive.writeAsString(jsonEncode(old), flush: true);
            });
            await tap('Remove resolved combined reference');
          }
          require(
            operations.combinedReference == null &&
                operations.reference == null,
            'Retained work must be preserved and resolved before preparing',
          );
          final children = config['children'];
          require(
            children is List && children.length == 2,
            'Two exact catalog selections required',
          );
          final choices = operations.combinedChoices();
          for (final index in [0, 1]) {
            final family = [4, 6][index], expected = children[index];
            final matches = choices[family]!
                .where(
                  (choice) =>
                      jsonEncode(ordered(choice)) ==
                      jsonEncode(ordered(expected)),
                )
                .toList();
            require(
              matches.length == 1,
              'Exact calculator profile is unavailable',
            );
            final selector = find.byKey(ValueKey('combined-ipv$family'));
            await tester.ensureVisible(selector);
            await tester.tap(selector);
            await tester.pumpAndSettle();
            await tester.tap(
              find.text('${expected['member_id']} · ${expected['cidr']}').last,
            );
            await tester.pumpAndSettle();
          }
          await tap('Prepare both reviews');
          require(
            operations.combined != null,
            'Pair admission unconfirmed; recover same nonce',
          );
          for (final family in [4, 6]) {
            require(
              find
                      .byKey(ValueKey('IPv$family immutable review'))
                      .evaluate()
                      .length ==
                  1,
              'Both immutable native reviews must be displayed',
            );
          }
        } else if (phase == 'combined-decision' ||
            phase == 'combined-recover') {
          final actual = operations.combined, expected = config['combined'];
          require(
            actual != null &&
                expected is Map &&
                actual['parent_id'] == expected['parent_id'] &&
                actual['client_nonce'] == expected['client_nonce'],
            'Exact retained parent mismatch',
          );
          for (final index in [0, 1]) {
            final child = actual!['children'][index],
                old = expected['children'][index];
            require(
              child['operation_id'] == old['operation_id'] &&
                  child['family'] == [4, 6][index] &&
                  child['review_digest'] == old['review_digest'] &&
                  jsonEncode(ordered(child['review'])) ==
                      jsonEncode(ordered(old['review'])),
              'Exact independently inspected child review mismatch',
            );
          }
          if (phase == 'combined-decision') {
            final index = config['child_index'], decision = config['decision'];
            require(
              [0, 1].contains(index) && ['approve', 'deny'].contains(decision),
              'One explicit child decision required',
            );
            final child = actual!['children'][index];
            require(
              child['revision'] == expected['children'][index]['revision'] &&
                  operations.canDecideCombined(index, decision),
              'Reviewed revision unavailable; nothing repeated',
            );
            if (decision == 'approve') {
              final checkbox = find.byKey(ValueKey('combined-review-$index'));
              await tester.ensureVisible(checkbox);
              await tester.tap(checkbox);
              await tester.pumpAndSettle();
            }
            await tap(
              decision == 'approve'
                  ? 'Approve IPv${child['family']} once'
                  : 'Deny IPv${child['family']}',
            );
          } else {
            await tap('Check combined status');
            if (config['cancel_unapproved'] == true) {
              require(
                (operations.combined!['children'] as List).every(
                  (child) =>
                      child['approval'] == null && child['attempt_count'] == 0,
                ),
                'Only a proven unapproved zero-attempt pair may be cancelled',
              );
              await tap('Cancel remaining children');
              final cancelled = operations.combined!;
              require(
                cancelled['cancelled'] == true &&
                    operations.canRemoveCombined &&
                    (cancelled['children'] as List).every(
                      (child) => child['attempt_count'] == 0,
                    ),
                'Cancellation not confirmed; retain the same reference',
              );
              archivedCombined = cancelled;
              await tester.runAsync(() async {
                final archive = File(
                  '${profileDir.path}/r05-cancelled-${cancelled['parent_id']}.json',
                );
                require(
                  !await archive.exists(),
                  'Cancelled archive exists; inspect outcome',
                );
                await archive.writeAsString(jsonEncode(cancelled), flush: true);
              });
              await tap('Remove resolved combined reference');
            }
          }
          final wantedStates = config['expected_states'];
          if (wantedStates != null) {
            require(
              wantedStates is List &&
                  wantedStates.isNotEmpty &&
                  wantedStates.every(
                    (state) => [
                      'awaiting_decisions',
                      'running',
                      'complete',
                      'partial',
                      'failed',
                      'cancelled',
                      'unknown',
                    ].contains(state),
                  ),
              'Invalid bounded state expectation',
            );
            final deadline = DateTime.now().add(const Duration(minutes: 3));
            while (!wantedStates.contains(operations.combined?['state'])) {
              require(
                DateTime.now().isBefore(deadline),
                'Parent still pending; recover same parent without another decision',
              );
              await tester.runAsync(
                () => Future<void>.delayed(const Duration(seconds: 2)),
              );
              await tap('Check combined status');
            }
          }
        }
        if (phase == 'combined-recover' && config['preserve_effects'] == true) {
          for (final index in [0, 1]) {
            final actual = operations.combined!['children'][index],
                expected = config['combined']['children'][index];
            require(
              actual['attempt_count'] == expected['attempt_count'],
              'Recovery changed child attempts',
            );
            for (final key in [
              'digest',
              'verified',
              'durable_ack',
              'ack_delivery_pending',
            ]) {
              require(
                actual['result']?[key] == expected['result']?[key],
                'Recovery changed retained receipt',
              );
            }
          }
        }
        combined = operations.combined;
        combinedReference = operations.combinedReference;
        combinedUncertain = operations.combinedUncertain;
        if (phase.toString().startsWith('combined-')) {
          final label = config['visual_label'];
          require(
            label is String && RegExp(r'^[a-z0-9-]{1,100}$').hasMatch(label),
            'Combined evidence requires a fresh bounded label',
          );
          await tester.runAsync(() async {
            final checkpoint = File(
              '${directory.path}/r05-checkpoint-$label.json',
            );
            await checkpoint.create(exclusive: true);
            await checkpoint.writeAsString(
              jsonEncode({
                'phase': phase,
                'profile': profileName,
                'combined': combined,
                'combined_reference': combinedReference,
                'combined_uncertain': combinedUncertain,
                'archived_combined': archivedCombined,
              }),
              flush: true,
            );
          });
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
          'archived_operation': archivedOperation,
          'archived_combined': archivedCombined,
          'combined': combined,
          'combined_reference': combinedReference,
          'combined_uncertain': combinedUncertain,
          'decision_child': phase == 'combined-decision'
              ? config['child_index']
              : null,
          'decision': phase == 'combined-decision' ? config['decision'] : null,
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
