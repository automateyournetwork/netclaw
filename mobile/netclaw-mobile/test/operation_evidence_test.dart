import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/cloud/owner_client.dart';
import 'package:netclaw_mobile/screens/operation_evidence.dart';

void main() {
  final fixtures =
      (jsonDecode(
                File(
                  '../../ui/netclaw-visual/src/shared/operation-evidence.fixture.json',
                ).readAsStringSync(),
              )
              as List)
          .map((v) => Map<String, dynamic>.from(v))
          .toList();
  for (var i = 0; i < 2; i++) {
    testWidgets(
      'IPv${i == 0 ? 4 : 6} displays authoritative facts and preserves unverified commentary separately',
      (tester) async {
        final op = fixtures[i], before = jsonEncode(fixtures);
        final expected = i == 0
            ? '192.0.2.0/26 · 62 usable hosts'
            : '2001:db8::/48 · 1208925819614629174706176 addresses';
        expect(operationEvidence(op)['summary'], expected);
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: OperationEvidence(operation: op),
              ),
            ),
          ),
        );
        expect(find.text('Authoritative tool facts'), findsOneWidget);
        expect(find.text(expected), findsOneWidget);
        expect(find.text('Unverified model commentary'), findsOneWidget);
        final facts = tester
            .widget<SelectableText>(
              find.byKey(const ValueKey('authoritative-tool-facts')),
            )
            .data!;
        expect(facts, isNot(contains('model_answer')));
        expect(
          tester
              .widget<SelectableText>(
                find.byKey(const ValueKey('unverified-model-commentary')),
              )
              .data,
          op['result']['evidence']['output']['model_answer'],
        );
        expect(jsonEncode(fixtures), before);
      },
    );
  }
  test(
    'normalized facts require verified receipt, exact call and independent verification',
    () {
      for (final void Function(Json) change in [
        (v) => v['result']['verified'] = false,
        (v) =>
            v['result']['evidence']['output']['tool']['independent_verification'] =
                false,
        (v) =>
            v['result']['evidence']['output']['tool']['output']['usable_count'] =
                '64',
        (v) => v['result']['evidence']['output']['tool']['arguments']['cidr'] =
            'other',
      ]) {
        final op = jsonDecode(jsonEncode(fixtures[0])) as Json;
        change(op);
        expect(operationEvidence(op)['facts'], isNull);
      }
    },
  );
}
