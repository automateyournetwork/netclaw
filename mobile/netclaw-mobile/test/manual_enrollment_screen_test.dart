import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_qr_payload.dart';
import 'package:netclaw_mobile/screens/manual_enrollment_screen.dart';

void main() {
  test('buildManualEnrollmentQr produces the exact shape a scanned QR would', () {
    final raw = buildManualEnrollmentQr(
      domain: 'netclaw.example.com',
      port: 8443,
      token: 'in2n_abc123',
    );

    final decoded = jsonDecode(raw) as Map<String, dynamic>;
    expect(decoded['border_host'], 'netclaw.example.com');
    expect(decoded['claw_domain'], 'netclaw.example.com'); // same value, D7 never violated
    expect(decoded['border_port'], 8443);
    expect(decoded['enrollment_token'], 'in2n_abc123');
  });

  Future<void> pump(WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: ManualEnrollmentScreen(
        memberId: 'risk/test',
        identity: const EdgeIdentity(),
        onEnrolled: (EdgeClient client, EnrollmentQrPayload payload) {},
      ),
    ));
  }

  testWidgets('empty fields are refused before any enrollment attempt', (tester) async {
    await pump(tester);
    await tester.tap(find.text('Enroll'));
    await tester.pump();

    expect(find.textContaining('are both required'), findsOneWidget);
  });

  testWidgets('a non-numeric port is refused with a clear message', (tester) async {
    await pump(tester);
    await tester.enterText(find.widgetWithText(TextField, 'Border domain'), 'netclaw.example.com');
    await tester.enterText(find.widgetWithText(TextField, 'Port'), 'not-a-number');
    await tester.enterText(find.widgetWithText(TextField, 'Enrollment token'), 'in2n_abc123');
    await tester.tap(find.text('Enroll'));
    await tester.pump();

    expect(find.text('Port must be a number.'), findsOneWidget);
  });
}
