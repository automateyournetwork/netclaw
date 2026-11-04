import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/screens/cloud_owner_screen.dart';

/// Import/copy this test into a private, separately identified native harness
/// with a path dependency on netclaw_mobile. It renders the production screen.
/// No credential is accepted through dart-define, source, logs or build assets.
/// After launch, inject Documents/r04a-qualification.json into that harness only.
/// The file is consumed and removed before networking. See the companion .md.
class QualificationTransport extends HttpsOwnerTransport {
  final calls = <Json>[];
  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  ) async {
    calls.add({'method': method, 'path': uri.path});
    return super.send(uri, method, headers, body);
  }
}

dynamic canonical(dynamic value) => value is Map
    ? {
        for (final key in (value.keys.cast<String>().toList()..sort()))
          key: canonical(value[key]),
      }
    : value is List
    ? value.map(canonical).toList()
    : value;

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'native cloud-owner exact review and same-operation recovery',
    (tester) async {
      late Directory directory;
      late Json config;
      await tester.runAsync(() async {
        directory = await getApplicationDocumentsDirectory();
        final file = File('${directory.path}/r04a-qualification.json');
        final deadline = DateTime.now().add(const Duration(minutes: 5));
        while (!await file.exists()) {
          if (DateTime.now().isAfter(deadline)) {
            throw StateError(
              'Private qualification configuration was not supplied',
            );
          }
          await Future<void>.delayed(const Duration(milliseconds: 500));
        }
        final bytes = await file.readAsBytes();
        await file
            .delete(); // Never retain the bootstrap ticket as an artifact.
        if (bytes.length > 65536) {
          throw StateError('Qualification configuration exceeds bound');
        }
        config = jsonDecode(utf8.decode(bytes)) as Json;
      });
      final phase = config['phase'];
      expect(['prepare', 'approve', 'recover'], contains(phase));
      final profile = CloudProfile(
        config['origin'] as String,
        config['installation_id'] as String,
      );
      final transport = QualificationTransport();
      final client = CloudOwnerClient(profile, transport: transport);
      await tester.runAsync(() async {
        await client.initialize();
      });
      await tester.pumpWidget(
        MaterialApp(home: CloudOwnerScreen(initialClient: client)),
      );
      await tester.pumpAndSettle();

      Future<void> tap(String label) async {
        final finder = find.widgetWithText(FilledButton, label);
        await tester.ensureVisible(finder);
        await tester.tap(finder);
        await tester.pump();
        await tester.runAsync(() async {
          final deadline = DateTime.now().add(const Duration(seconds: 40));
          while (client.busy) {
            if (DateTime.now().isAfter(deadline)) {
              throw StateError('Native request did not settle');
            }
            await Future<void>.delayed(const Duration(milliseconds: 100));
          }
        });
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('cloud-error')), findsNothing);
        expect(tester.takeException(), isNull);
      }

      String? ticket = config.remove('ticket') as String?;
      if (!client.operationsReady) {
        if (ticket == null) {
          throw StateError('A fresh owner ticket is required');
        }
        final field = find.byKey(const ValueKey('cloud-ticket'));
        await tester.ensureVisible(field);
        await tester.enterText(field, ticket);
        ticket = null;
        await tap('Sign in as owner');
      }
      ticket = null;
      expect(client.operationsReady, true);
      if (client.openLab) {
        expect(client.authenticated, false);
        expect(client.session, isNull);
        expect(find.byKey(const ValueKey('cloud-ticket')), findsNothing);
        expect(
          transport.calls.where(
            (call) => call['path'] == '/api/hud/owner/session',
          ),
          isEmpty,
        );
      }

      String? discardedResolvedOperationId;
      if (phase == 'prepare') {
        final discardId = config['discard_resolved_operation_id'];
        if (client.reference != null && discardId != null) {
          expect(discardId, isA<String>());
          expect(client.reference!['operation_id'], discardId);
          final retired = client.operation!;
          expect(retired['operation_id'], discardId);
          expect(retired['state'], 'refused');
          expect(retired['error_code'], 'owner_denied');
          expect(retired.containsKey('approval'), true);
          expect(retired['approval'], isNull);
          expect(retired['attempt_count'], 0);
          expect(retired['may_have_executed'], false);
          expect(retired.containsKey('result'), true);
          expect(retired['result'], isNull);
          expect(retired['reconciliation_required'], false);
          expect(client.canRemove, true);
          await tap('Remove resolved reference');
          expect(client.reference, isNull);
          discardedResolvedOperationId = discardId as String;
        }
        expect(
          client.reference,
          isNull,
          reason: 'Never replace a retained request',
        );
        final members = client.catalog!['members'] as List;
        final memberIndex = members.indexWhere(
          (row) => row['member']['member_id'] == config['member_id'],
        );
        expect(memberIndex, greaterThanOrEqualTo(0));
        final member = members[memberIndex];
        final models = member['model_profiles'] as List,
            tools = member['tools'] as List;
        final modelIndex = models.indexWhere(
          (row) => row['profile_id'] == config['model_profile_id'],
        );
        final toolIndex = tools.indexWhere(
          (row) =>
              row['tool'] == config['tool'] &&
              jsonEncode(canonical(row['arguments'])) ==
                  jsonEncode(canonical(config['arguments'])),
        );
        expect(modelIndex, greaterThanOrEqualTo(0));
        expect(toolIndex, greaterThanOrEqualTo(0));
        Future<void> select(ValueKey<String> key, String text) async {
          final field = find.byKey(key);
          await tester.ensureVisible(field);
          await tester.tap(field);
          await tester.pumpAndSettle();
          await tester.tap(find.text(text).last);
          await tester.pumpAndSettle();
        }

        if (memberIndex != 0) {
          await select(
            ValueKey('members-${profile.key}'),
            member['member']['member_id'],
          );
        }
        if (modelIndex != 0) {
          await select(
            ValueKey('models-$memberIndex'),
            '${models[modelIndex]['profile_id']} · ${models[modelIndex]['provider']} / ${models[modelIndex]['model']}',
          );
        }
        if (toolIndex != 0) {
          await select(
            ValueKey('tools-$memberIndex'),
            '${tools[toolIndex]['tool']} · ${tools[toolIndex]['device_ref']}',
          );
        }
        await tap('Prepare review');
        final review = client.operation!['review'];
        expect(review['border']['installation_id'], profile.installationId);
        expect(review['member']['member_id'], config['member_id']);
        expect(
          review['model_profile']['profile_id'],
          config['model_profile_id'],
        );
        expect(review['tool_call']['tool'], config['tool']);
        expect(
          jsonEncode(canonical(review['tool_call']['arguments'])),
          jsonEncode(canonical(config['arguments'])),
        );
        expect(
          find.byKey(const ValueKey('Complete immutable review')),
          findsOneWidget,
        );
        expect(
          tester
              .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Approve once'),
              )
              .onPressed,
          isNull,
        );
        expect(
          transport.calls.where((call) => call['path'].endsWith('/decision')),
          isEmpty,
        );
      } else {
        expect(client.reference!['operation_id'], config['operation_id']);
        expect(
          client.operation!['review_digest'],
          config['approved_review_digest'],
        );
        // Root/operator must inspect phase one's full review before supplying this
        // exact approval. A generic first-catalog choice never authorizes execution.
        expect(
          jsonEncode(canonical(client.operation!['review'])),
          jsonEncode(canonical(config['approved_review'])),
        );
        if (phase == 'approve') {
          expect(client.canDecide('approve'), true);
          expect(
            find.byKey(const ValueKey('Complete immutable review')),
            findsOneWidget,
          );
          await tester.ensureVisible(
            find.byKey(const ValueKey('cloud-review-confirmation')),
          );
          await tester.tap(
            find.byKey(const ValueKey('cloud-review-confirmation')),
          );
          await tester.pump();
          await tap('Approve once');
          // Approval dispatches the member but a status GET does not collect
          // its receipt. Exercise the native, same-operation reconciliation
          // control to retrieve verified evidence and durably acknowledge it.
          if (client.operation?['result']?['durable_ack'] != true) {
            await tap('Reconcile existing operation');
          }
        }
        for (
          var tries = 0;
          client.operation?['result']?['durable_ack'] != true && tries < 60;
          tries++
        ) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(seconds: 2)),
          );
          if (phase == 'approve' &&
              (client.operation?['allowed_actions'] as List?)?.contains(
                    'reconcile',
                  ) ==
                  true) {
            await tap('Reconcile existing operation');
          } else {
            await tap('Check same operation');
          }
        }
        expect(client.operation!['state'], 'completed');
        expect(client.operation!['attempt_count'], 1);
        expect(client.operation!['result']['verified'], true);
        expect(client.operation!['result']['durable_ack'], true);
        expect(find.byKey(const ValueKey('cloud-receipt')), findsOneWidget);
        expect(
          transport.calls
              .where((call) => call['path'].endsWith('/decision'))
              .length,
          phase == 'approve' ? 1 : 0,
        );
        if (phase == 'recover') {
          expect(
            transport.calls.every((call) => call['method'] == 'GET'),
            true,
          );
        }
      }
      final evidence = <String, dynamic>{
        'phase': phase,
        'platform': Platform.operatingSystem,
        'origin': profile.origin,
        'installation_id': profile.installationId,
        'reference': client.reference,
        'operation': client.operation,
        'requests': transport.calls,
        'native_screen_rendered': true,
        'discarded_resolved_operation_id': ?discardedResolvedOperationId,
        'scope':
            'Production cloud screen/client in isolated native qualification app; physical versus simulator supplied by host evidence',
      };
      // Deliver over Flutter's test protocol before the host uninstalls the
      // qualification app. Documents alone can disappear at test completion.
      binding.reportData = {'r04a_evidence': evidence};
      await tester.runAsync(() async {
        await File(
          '${directory.path}/r04a-evidence-$phase.json',
        ).writeAsString(jsonEncode(evidence), flush: true);
      });
      await tester.pumpWidget(const SizedBox());
    },
    timeout: const Timeout(Duration(minutes: 10)),
  );
}
