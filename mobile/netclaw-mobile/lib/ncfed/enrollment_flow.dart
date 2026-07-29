import 'dart:io';

import 'edge_client.dart';
import 'edge_identity.dart';
import 'enrollment_qr_payload.dart';

/// Result of one enrollment attempt from a scanned QR payload — pulled out
/// of enrollment_screen.dart so the actual decision logic (parse → domain
/// check → dial → friendly error mapping) is unit-testable without needing
/// the `mobile_scanner` widget or a real network/platform channel for the
/// failure paths (T017).
sealed class EnrollmentOutcome {}

class EnrollmentSuccess extends EnrollmentOutcome {
  final EdgeClient client;
  final EnrollmentQrPayload payload;
  EnrollmentSuccess(this.client, this.payload);
}

class EnrollmentFailure extends EnrollmentOutcome {
  final String message;
  EnrollmentFailure(this.message);
}

/// Parses `raw` as an enrollment QR payload and attempts enrollment.
/// Domain-mismatch (research D7) and single-use-token failures are caught
/// and mapped to a friendly message before any state changes — a
/// domain-mismatched payload never reaches `EdgeClient.enroll`'s network
/// call at all (`verifyClawDomainBeforeDial` throws first).
/// A never-null, human-distinguishable label for this device.
///
/// Every edge member used to enroll with `display_name: null`, because this is
/// the only caller of `EdgeClient.enroll` and it never passed one. Owner
/// attribution then had to be guessed from enrollment timestamps, which caused
/// a real misroute: a message intended for one operator's phone was delivered
/// to another's because the mesh carried no way to tell them apart.
///
/// Derived rather than prompted so it can never be skipped or left empty. The
/// memberId tail disambiguates two devices on the same platform (memberId is
/// `risk/<millis>`, so the tail is stable and unique per enrollment). An
/// operator-supplied name overrides it — see [attemptEnrollmentFromQr].
String defaultDeviceLabel(String memberId) {
  final platform = switch (Platform.operatingSystem) {
    'ios' => 'iPhone',
    'android' => 'Android',
    final other => other,
  };
  final tail = memberId.length >= 4 ? memberId.substring(memberId.length - 4) : memberId;
  return '$platform · $tail';
}

Future<EnrollmentOutcome> attemptEnrollmentFromQr(
  String raw, {
  required String memberId,
  required EdgeIdentity identity,
  /// Optional operator-supplied device name. When null or blank, a derived
  /// label is sent instead — the Border must never receive a null again.
  String? displayName,
}) async {
  try {
    final payload = EnrollmentQrPayload.parse(raw);
    final label = (displayName == null || displayName.trim().isEmpty)
        ? defaultDeviceLabel(memberId)
        : displayName.trim();
    final client = await EdgeClient.enroll(payload,
        memberId: memberId, identity: identity, displayName: label);
    return EnrollmentSuccess(client, payload);
  } on ClawDomainMismatchException catch (e) {
    return EnrollmentFailure('This QR points at the wrong Border.\n${e.toString()}');
  } on EdgeClientException catch (e) {
    final msg = e.message.toLowerCase();
    return EnrollmentFailure(msg.contains('token')
        ? 'This enrollment code has expired or already been used — ask for a new QR code.'
        : 'Could not enroll: ${e.message}');
  } catch (e) {
    return EnrollmentFailure('Could not read that QR code: $e');
  }
}
