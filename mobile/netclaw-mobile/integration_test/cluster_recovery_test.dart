import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:netclaw_mobile/main.dart' as production;
import 'package:netclaw_mobile/ncfed/cluster_trust.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';
import 'package:netclaw_mobile/screens/cloud_owner_screen.dart';
import 'package:netclaw_mobile/screens/endpoint_recovery_screen.dart';
import 'package:netclaw_mobile/screens/protected_device_screen.dart';
import 'mobile_qr_test.dart' show NativeLifecycleWitness, require, ordered;

/// Coordinator-driven native recovery. This driver never prepares or approves.
/// The actual approved operation comes from mobile_qr_test's approve-once phase.
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('retained cluster device recovers without another execution', (
    tester,
  ) async {
    late Directory directory;
    late Map<String, dynamic> config;
    Future<void> waitFile(File file) async {
      final deadline = DateTime.now().add(const Duration(seconds: 60));
      while (!await file.exists()) {
        require(
          DateTime.now().isBefore(deadline),
          'Coordinator phase marker timed out',
        );
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
    }

    await tester.runAsync(() async {
      directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}/r08-qualification.json');
      await waitFile(file);
      require(await file.length() <= 65536, 'Configuration too large');
      config = clusterDecode(await file.readAsString()) as Map<String, dynamic>;
      await file.delete();
    });
    final phase = config['phase'], profile = config['profile'];
    require(
      [
        'select-node',
        'no-quorum',
        'stale-review',
        'cold-recover',
        'background-recover',
      ].contains(phase),
      'Unknown phase',
    );
    require(
      profile is String && RegExp(r'^[a-z0-9-]{1,64}$').hasMatch(profile),
      'Invalid profile',
    );
    final store = EnrollmentStore(Directory('${directory.path}/$profile'));
    late StoredEnrollment before;
    await tester.runAsync(() async {
      final saved = await store.load();
      require(saved != null && !saved.pending, 'Confirmed identity required');
      before = saved!;
    });
    require(
      before.clusterPin != null &&
          before.deviceSubject != null &&
          before.clusterDescriptor != null,
      'Cluster enrollment required',
    );
    require(
      before.clusterPin!.clusterId == config['cluster_id'] &&
          before.clusterPin!.generation == config['generation'] &&
          before.keyFingerprint == config['key_fingerprint'] &&
          before.deviceSubject == config['device_subject'],
      'Reviewed identity changed',
    );
    final lifecycle = NativeLifecycleWitness();
    WidgetsBinding.instance.addObserver(lifecycle);
    addTearDown(() => WidgetsBinding.instance.removeObserver(lifecycle));
    Future<void> waitUi(bool Function() ready) async {
      final deadline = DateTime.now().add(const Duration(seconds: 60));
      while (!ready()) {
        require(
          DateTime.now().isBefore(deadline),
          'Native recovery UI timed out',
        );
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 100)),
        );
        await tester.pump(const Duration(milliseconds: 100));
      }
    }

    Future<void> tap(String label) async {
      final found = find.text(label);
      require(found.evaluate().length == 1, 'Native recovery action missing');
      await tester.ensureVisible(found);
      await tester.tap(found);
      await tester.pump();
    }

    await tester.pumpWidget(
      MaterialApp(
        home: production.EnrollmentGate(
          documentsDirectory: () async => store.directory,
          recoverConnection: phase == 'select-node',
        ),
      ),
    );
    if (phase == 'select-node') {
      await waitUi(
        () => find.byType(EndpointRecoveryScreen).evaluate().isNotEmpty,
      );
      final nodes =
          before.clusterDescriptor!['manifest']['manifest']['nodes'] as List;
      final target = nodes.singleWhere(
        (n) => n['node_id'] == config['target_node_id'],
      );
      require(
        target['node_id'] != before.clusterNodeId,
        'Alternate node required',
      );
      await waitUi(
        () =>
            find.byType(DropdownButtonFormField<String>).evaluate().isNotEmpty,
      );
      // The retained manifest verifies through real (non-fake-async) platform
      // futures; give them real time so the dropdown has its items.
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(seconds: 3)),
      );
      await tester.pump();
      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text(target['endpoints']['https']).last);
      await tester.pumpAndSettle();
      await tap('Verify and select Border');
    }
    await waitUi(() => find.byType(CloudOwnerScreen).evaluate().isNotEmpty);
    final operations = tester
        .widget<CloudOwnerScreen>(find.byType(CloudOwnerScreen))
        .initialClient!;
    final edge = tester
        .widget<ProtectedDeviceScreen>(find.byType(ProtectedDeviceScreen))
        .edge;
    require(
      operations.clusterMode &&
          operations.reference?['operation_id'] == config['operation_id'] &&
          operations.reference?['client_nonce'] == config['client_nonce'],
      'Original operation reference missing',
    );
    final retainedReference =
        jsonDecode(jsonEncode(operations.reference)) as Map<String, dynamic>;
    final retainedReview = jsonDecode(
      jsonEncode(operations.operation?['review']),
    );
    require(
      operations.operation?['review_digest'] == config['review_digest'],
      'Original review digest changed',
    );
    if (['no-quorum', 'stale-review', 'background-recover'].contains(phase)) {
      await tester.runAsync(() async {
        final ready = File('${directory.path}/r08-ready-$phase.json');
        require(
          !await ready.exists(),
          'Phase marker already exists; inspect earlier run',
        );
        await ready.writeAsString(
          jsonEncode({
            'phase': phase,
            'reference': retainedReference,
            'node_id': edge.clusterBinding!.nodeId,
            'epoch': edge.clusterBinding!.epoch,
          }),
          flush: true,
        );
        await waitFile(File('${directory.path}/r08-fault-ready.json'));
      });
      await tap('Check same operation');
      await waitUi(() => !operations.busy);
      require(
        jsonEncode(ordered(operations.reference)) ==
            jsonEncode(ordered(retainedReference)),
        'Reference or sent marker changed',
      );
      require(
        jsonEncode(ordered(operations.operation?['review'])) ==
            jsonEncode(ordered(retainedReview)),
        'Original review was replaced',
      );
      if (phase != 'background-recover') {
        require(
          !operations.canDecide('approve') && !operations.canPrepare,
          'Fault allowed a new approval',
        );
      }
      if (phase == 'background-recover') {
        require(
          lifecycle.states.contains('paused') &&
              lifecycle.states.contains('resumed'),
          'No actual OS background/resume was observed',
        );
      }
    }
    late StoredEnrollment after;
    await tester.runAsync(() async {
      after = (await store.load())!;
    });
    require(
      after.memberId == before.memberId &&
          after.keyFingerprint == before.keyFingerprint &&
          after.deviceSubject == before.deviceSubject &&
          after.enrollmentGeneration == before.enrollmentGeneration &&
          after.clusterPin!.sameAudience(before.clusterPin!),
      'Retained native identity changed',
    );
    if (phase == 'select-node') {
      require(
        after.clusterNodeId == config['target_node_id'] &&
            after.endpointRevision == before.endpointRevision + 1,
        'Alternate endpoint was not committed',
      );
    }
    if (config['result_digest'] != null) {
      require(
        operations.operation?['result']?['digest'] == config['result_digest'] &&
            operations.operation?['result']?['verified'] == true &&
            operations.operation?['result']?['durable_ack'] == true,
        'Original signed result/ACK not recovered',
      );
    }
    binding.reportData = {
      'r08_evidence': {
        'schema': 1,
        'classification': 'REAL_NATIVE_REQUIRES_BACKEND_CORRELATION',
        'phase': phase,
        'cluster_id': after.clusterPin!.clusterId,
        'generation': after.clusterPin!.generation,
        'manifest_revision': after.clusterPin!.revision,
        'node_id': after.clusterNodeId,
        'member_id': after.memberId,
        'key_fingerprint': after.keyFingerprint,
        'device_subject': after.deviceSubject,
        'enrollment_generation': after.enrollmentGeneration,
        'reference': operations.reference,
        'operation': operations.operation,
        'native_lifecycle': lifecycle.states,
        'prepare_calls': 0,
        'decision_calls': 0,
        'reconcile_calls': 0,
        'backend_record': config['backend_record'],
        'limits': {
          'physical_camera': false,
          'secure_enclave': false,
          'actual_os_cold_restart_requires_host_receipt': true,
        },
      },
    };
    await edge.close();
  });
}
