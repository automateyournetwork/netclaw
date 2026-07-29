import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_flow.dart';
import 'package:netclaw_mobile/ncfed/enrollment_qr_payload.dart';

void main() {
  group('verifyClawDomainBeforeDial (research D7)', () {
    test('matching border_host/claw_domain passes', () {
      const payload = EnrollmentQrPayload(
        borderHost: 'netclaw.automateyournetwork.ca',
        borderPort: 8443,
        clawDomain: 'netclaw.automateyournetwork.ca',
        enrollmentToken: 'in2n_x',
      );
      expect(() => verifyClawDomainBeforeDial(payload), returnsNormally);
    });

    test('mismatched border_host/claw_domain throws before any dial', () {
      const payload = EnrollmentQrPayload(
        borderHost: 'evil.example.com',
        borderPort: 8443,
        clawDomain: 'netclaw.automateyournetwork.ca',
        enrollmentToken: 'in2n_x',
      );
      expect(() => verifyClawDomainBeforeDial(payload),
          throwsA(isA<ClawDomainMismatchException>()));
    });
  });

  group('attemptEnrollmentFromQr — the mismatched-domain QR aborts before dialing (T017)', () {
    test('never attempts a network call for a mismatched-domain QR', () async {
      final raw = jsonEncode({
        'border_host': 'evil.example.com',
        'border_port': 8443,
        'claw_domain': 'netclaw.automateyournetwork.ca',
        'enrollment_token': 'in2n_x',
      });
      // If this ever reached EdgeClient.enroll's IOWebSocketChannel.connect,
      // it would hang or throw a platform socket error (no such host in the
      // test sandbox) rather than complete promptly with a clean
      // EnrollmentFailure — so a fast, clean failure here is itself the
      // proof that no dial was attempted.
      final outcome = await attemptEnrollmentFromQr(
        raw,
        memberId: 'risk/phone1',
        identity: const EdgeIdentity(),
      ).timeout(const Duration(seconds: 2));
      expect(outcome, isA<EnrollmentFailure>());
      expect((outcome as EnrollmentFailure).message, contains('wrong Border'));
    });

    test('malformed QR payload fails cleanly, not as a domain mismatch', () async {
      final outcome = await attemptEnrollmentFromQr(
        'not json at all',
        memberId: 'risk/phone1',
        identity: const EdgeIdentity(),
      ).timeout(const Duration(seconds: 2));
      expect(outcome, isA<EnrollmentFailure>());
      expect((outcome as EnrollmentFailure).message, isNot(contains('wrong Border')));
    });
  });
}
