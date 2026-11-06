import 'dart:io';

import 'edge_client.dart';
import 'edge_identity.dart';
import 'enrollment_qr_payload.dart';
import 'enrollment_store.dart';

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
  final bool pending;
  EnrollmentFailure(this.message, {this.pending = false});
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
  final tail = memberId.length >= 4
      ? memberId.substring(memberId.length - 4)
      : memberId;
  return '$platform · $tail';
}

Future<EnrollmentOutcome> attemptEnrollmentFromQr(
  String raw, {
  required String memberId,
  required EdgeIdentity identity,

  /// Optional operator-supplied device name. When null or blank, a derived
  /// label is sent instead — the Border must never receive a null again.
  String? displayName,
  EnrollmentStore? store,
  Future<EdgeClient> Function(
    EnrollmentQrPayload, {
    required String memberId,
    required EdgeIdentity identity,
    String? displayName,
  })?
  enroll,
}) async {
  var submitted = false;
  String? preparedFingerprint;
  try {
    final payload = EnrollmentQrPayload.parse(raw);
    final label = (displayName == null || displayName.trim().isEmpty)
        ? defaultDeviceLabel(memberId)
        : displayName.trim();
    String? fingerprint;
    if (store != null) {
      if (await store.load() != null) {
        return EnrollmentFailure(
          'An enrollment is already retained. Reconnect to the same device before scanning another code.',
          pending: true,
        );
      }
      fingerprint = await identity.publicKeyFingerprint();
      preparedFingerprint = fingerprint;
      await store.save(
        StoredEnrollment(
          memberId: memberId,
          keyFingerprint: fingerprint,
          borderHost: payload.borderHost,
          borderPort: payload.borderPort,
          clawDomain: payload.clawDomain,
          wsPath: payload.wsPath,
          installationId: payload.installationId,
          pending: true,
        ),
      );
    }
    submitted = store != null;
    final client = await (enroll ?? EdgeClient.enroll)(
      payload,
      memberId: memberId,
      identity: identity,
      displayName: label,
    );
    try {
      if (store != null) {
        if (client.enrollFingerprint != fingerprint) {
          throw const FormatException('Border returned a different device key');
        }
        await store.save(
          StoredEnrollment(
            memberId: memberId,
            keyFingerprint: fingerprint!,
            borderHost: payload.borderHost,
            borderPort: payload.borderPort,
            clawDomain: payload.clawDomain,
            wsPath: payload.wsPath,
            installationId: payload.installationId,
            deviceSubject:
                client.protectedDevice?.principal['subject'] as String?,
            protectedOrigin: client.protectedDevice?.origin,
          ),
        );
      }
      return EnrollmentSuccess(client, payload);
    } catch (_) {
      await client.close();
      rethrow;
    }
  } on ClawDomainMismatchException catch (e) {
    return EnrollmentFailure(
      'This QR points at the wrong Border.\n${e.toString()}',
    );
  } on EdgeClientException catch (e) {
    if (submitted) {
      final proof = e.data;
      if (store != null && proof?['admission'] == 'not_enrolled' &&
          proof?['code'] == 'enrollment_refused' && proof?['status'] == 400 &&
          proof?['member_id'] == memberId &&
          proof?['key_fingerprint'] == preparedFingerprint) {
        final retained = await store.load();
        if (retained?.pending == true && retained?.memberId == memberId &&
            retained?.keyFingerprint == preparedFingerprint) {
          await store.clear();
          return EnrollmentFailure('This enrollment code expired or was already used. Generate a new QR code and scan it.',
          );
        }
      }
      return EnrollmentFailure(
        'Enrollment is unconfirmed. Check the retained device; do not scan or reuse this code.',
        pending: true,
      );
    }
    final msg = e.message.toLowerCase();
    return EnrollmentFailure(
      msg.contains('token')
          ? 'This enrollment code has expired or already been used — ask for a new QR code.'
          : 'Could not enroll: ${e.message}',
    );
  } catch (_) {
    return EnrollmentFailure(
      submitted
          ? 'Enrollment is unconfirmed. Check the retained device; nothing will be resent.'
          : 'Could not read or enroll with that QR code.',
      pending: submitted,
    );
  }
}
