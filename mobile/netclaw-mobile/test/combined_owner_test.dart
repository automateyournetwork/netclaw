import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/screens/combined_operations_panel.dart';
import 'cloud_owner_test.dart'
    show FixtureTransport, MemoryOwnerStore, installation, profile, digest;

class CombinedFixture extends FixtureTransport {
  Json? parent;
  final combinedCalls = <({String method, String path, Json? body})>[];
  bool failPrepare = false, failDecision = false, failCancel = false;
  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  ) async {
    if (uri.path == '/api/hud/operations/catalog') {
      return OwnerResponse(200, {
        'revision': 'catalog1',
        'capabilities': ['calculator_combined_v1'],
        'members': [
          for (final family in [4, 6])
            {
              'member': {'member_id': 'risk/ipv$family'},
              'model_profiles': [
                {
                  'profile_id': 'ollama-cpu-ipv$family',
                  'profile_revision': 'revision$family',
                  'provider': 'ollama',
                  'model': 'qwen3:0.6b',
                },
              ],
              'tools': [
                {
                  'tool': family == 4
                      ? 'subnet_calculator'
                      : 'subnet_calculator_v6',
                  'device_ref': 'subnet',
                  'arguments': {
                    'cidr': family == 4 ? '192.0.2.0/26' : '2001:db8::/64',
                  },
                },
              ],
            },
        ],
      });
    }
    if (uri.path.startsWith('/api/hud/operations/combined') ||
        uri.path.endsWith('/decision')) {
      combinedCalls.add((method: method, path: uri.toString(), body: body));
      if (uri.path == '/api/hud/operations/combined' && method == 'POST') {
        if (refusePrepare) {
          return OwnerResponse(403, {'admission': 'not_submitted'});
        }
        parent = {
          'schemaVersion': 1,
          'parent_id': 'parent1',
          'client_nonce': body!['client_nonce'],
          'state': 'awaiting_decisions',
          'expires_at_ms': DateTime.now().millisecondsSinceEpoch + 300000,
          'children': [
            for (var index = 0; index < 2; index++)
              {
                'index': index,
                'family': [4, 6][index],
                'operation_id': 'child$index',
                'client_nonce': 'nonce$index',
                'revision': 1,
                'review_digest': digest,
                'state': 'review_pending',
                'allowed_actions': index == 0 ? ['approve', 'deny'] : [],
                'reconciliation_required': false,
                'may_have_executed': false,
                'review': {
                  'principal': labPrincipal,
                  'border': {'installation_id': installation},
                  'member': {
                    'member_id': 'risk/ipv${[4, 6][index]}',
                  },
                  'model_profile': {
                    'provider': 'ollama',
                    'model': 'qwen3:0.6b',
                  },
                  'tool_call': {
                    'arguments': {
                      'cidr': index == 0 ? '192.0.2.0/26' : '2001:db8::/64',
                    },
                  },
                  'limits': {
                    'expires_at_ms':
                        DateTime.now().millisecondsSinceEpoch + 300000,
                  },
                },
              },
          ],
        };
        if (failPrepare) throw const CloudOwnerError('transport_uncertain');
      } else if (uri.path.endsWith('/decision')) {
        final index = uri.path.contains('child0') ? 0 : 1;
        expect(body!['revision'], parent!['children'][index]['revision']);
        final child = parent!['children'][index];
        effects++;
        child['state'] = body['decision'] == 'deny' ? 'denied' : 'completed';
        child['revision'] = 2;
        child['allowed_actions'] = [];
        if (body['decision'] == 'approve') {
          child['may_have_executed'] = true;
          child['result'] = {
            'verified': true,
            'durable_ack': true,
            'ack_delivery_pending': false,
            'evidence': {'family': child['family']},
          };
        }
        if (index == 0) {
          parent!['children'][1]['allowed_actions'] = ['approve', 'deny'];
        } else {
          parent!['state'] = 'complete';
        }
        if (failDecision) throw const CloudOwnerError('transport_uncertain');
        return OwnerResponse(200, jsonDecode(jsonEncode(child)));
      } else if (uri.path.endsWith('/cancel')) {
        if (failCancel) throw const CloudOwnerError('transport_uncertain');
        parent!['state'] = 'cancelled';
        for (final c in parent!['children']) {
          c['allowed_actions'] = [];
          c['state'] = 'denied';
        }
      }
      return OwnerResponse(200, jsonDecode(jsonEncode(parent!)));
    }
    return super.send(uri, method, headers, body);
  }
}

Future<
  ({CloudOwnerClient client, CombinedFixture transport, MemoryOwnerStore store})
>
fixture() async {
  final transport = CombinedFixture()..openLab = true,
      store = MemoryOwnerStore();
  final client = CloudOwnerClient(profile, store: store, transport: transport);
  await client.initialize();
  return (client: client, transport: transport, store: store);
}

Future<void> prepare(CloudOwnerClient c) => c.prepareCombined([
  c.combinedChoices()[4]!.first,
  c.combinedChoices()[6]!.first,
]);
Future<void> approve(CloudOwnerClient c, int index) => c.decideCombined(
  index,
  'approve',
  revision: c.combined!['children'][index]['revision'],
  reviewDigest: c.combined!['children'][index]['review_digest'],
);
void main() {
  test(
    'combined prepare persists bounded identifiers and exact catalog profiles; separate ordered decisions',
    () async {
      final f = await fixture();
      await prepare(f.client);
      final saved = f.store.values.entries.singleWhere(
        (e) => e.key.startsWith('combined.'),
      );
      expect(saved.value, contains('parent1'));
      expect(saved.value, contains('child0'));
      expect(saved.value, isNot(contains('192.0.2')));
      expect(saved.value, isNot(contains('qwen')));
      expect(f.client.canDecideCombined(1, 'approve'), false);
      await expectLater(approve(f.client, 1), throwsA(isA<CloudOwnerError>()));
      await approve(f.client, 0);
      expect(f.transport.effects, 1);
      expect(f.client.canDecideCombined(1, 'approve'), true);
      await approve(f.client, 1);
      expect(f.transport.effects, 2);
      expect(f.client.combined!['state'], 'complete');
      expect(f.client.canRemoveCombined, true);
    },
  );
  test(
    'lost prepare resumes via GET only with original parent and nonce',
    () async {
      final f = await fixture();
      f.transport.failPrepare = true;
      await expectLater(prepare(f.client), throwsA(isA<CloudOwnerError>()));
      final nonce = f.client.combinedReference!['client_nonce'];
      final boundary = f.transport.combinedCalls.length;
      f.client.suspend();
      await f.client.resume();
      expect(f.client.combinedReference!['client_nonce'], nonce);
      expect(f.client.combined!['parent_id'], 'parent1');
      expect(
        f.transport.combinedCalls
            .skip(boundary)
            .every((c) => c.method == 'GET'),
        true,
      );
      expect(f.transport.effects, 0);
    },
  );
  test(
    'lost child response retains sent marker and recovery never retransmits',
    () async {
      final f = await fixture();
      await prepare(f.client);
      f.transport.failDecision = true;
      await expectLater(approve(f.client, 0), throwsA(isA<CloudOwnerError>()));
      expect(f.client.combinedUncertain, true);
      final boundary = f.transport.combinedCalls.length;
      await f.client.combinedStatus();
      expect(
        f.transport.combinedCalls
            .skip(boundary)
            .every((c) => c.method == 'GET'),
        true,
      );
      await expectLater(approve(f.client, 0), throwsA(isA<CloudOwnerError>()));
      expect(f.transport.effects, 1);
      expect(f.client.canDecideCombined(1, 'approve'), true);
    },
  );
  test(
    'foreign child identity is refused without replacing retained references',
    () async {
      final f = await fixture();
      await prepare(f.client);
      f.transport.parent!['children'][1]['operation_id'] = 'foreign';
      await expectLater(
        f.client.combinedStatus(),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(
        f.client.combinedReference!['children'][1]['operation_id'],
        'child1',
      );
      expect(f.client.combinedUncertain, true);
    },
  );
  test(
    'cancel marker persists before uncertain reply and prevents resend',
    () async {
      final f = await fixture();
      await prepare(f.client);
      f.transport.failCancel = true;
      await expectLater(
        f.client.cancelCombined(),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(f.client.combinedReference!['cancel_sent'], true);
      await expectLater(
        f.client.cancelCombined(),
        throwsA(isA<CloudOwnerError>()),
      );
      expect(
        f.transport.combinedCalls
            .where((c) => c.path.endsWith('/cancel'))
            .length,
        1,
      );
    },
  );
  test(
    'confirmed unsubmitted pair remains discardable after native resume',
    () async {
      final f = await fixture();
      f.transport.refusePrepare = true;
      await expectLater(prepare(f.client), throwsA(isA<CloudOwnerError>()));
      expect(f.client.canRemoveCombined, true);
      final boundary = f.transport.combinedCalls.length;
      f.client.suspend();
      await f.client.resume();
      expect(f.transport.combinedCalls.length, boundary);
      expect(f.client.canRemoveCombined, true);
      await f.client.removeCombinedReference();
      expect(f.client.combinedReference, isNull);
    },
  );
  testWidgets(
    'both reviews visible and each native approval has its own confirmation',
    (tester) async {
      final f = await fixture();
      await prepare(f.client);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: CombinedOperationsPanel(
                client: f.client,
                busy: false,
                run: (action) => action(),
              ),
            ),
          ),
        ),
      );
      expect(
        find.byKey(const ValueKey('IPv4 immutable review')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('IPv6 immutable review')),
        findsOneWidget,
      );
      FilledButton approval(String text) =>
          tester.widget<FilledButton>(find.widgetWithText(FilledButton, text));
      expect(approval('Approve IPv4 once').onPressed, isNull);
      expect(approval('Approve IPv6 once').onPressed, isNull);
      await tester.ensureVisible(
        find.byKey(const ValueKey('combined-review-0')),
      );
      await tester.tap(find.byKey(const ValueKey('combined-review-0')));
      await tester.pump();
      expect(approval('Approve IPv4 once').onPressed, isNotNull);
      expect(approval('Approve IPv6 once').onPressed, isNull);
    },
  );
}
