import 'edge_client.dart';
import 'edge_identity.dart';
import 'enrollment_qr_payload.dart';
import 'enrollment_store.dart';

typedef RetainedDeviceReconnect =
    Future<EdgeClient> Function(
      EnrollmentQrPayload payload, {
      required String memberId,
      required String keyFingerprint,
      required EdgeIdentity identity,
    });

String recoveryFailureMessage(Object error) {
  if (isRevokedByBorder(error)) {
    return 'The Border refused this retained device key. Access may have been revoked. '
        'Your enrollment and operation references are preserved; nothing was resent.';
  }
  if (error is FormatException) {
    return 'The replacement did not match the retained Border identity or secure endpoint. '
        'The saved connection and operation references are unchanged.';
  }
  return 'The connection could not be verified. Your enrollment and operation references '
      'are preserved; nothing was resent.';
}

/// A routing update, never a new enrollment or a transfer to another trust name.
/// The probe only proves the retained device key through the existing hello.
/// Operations, approvals, sessions and results are neither read nor submitted.
Future<StoredEnrollment> replaceEnrollmentPort({
  required EnrollmentStore store,
  required StoredEnrollment expected,
  required int port,
  EdgeIdentity identity = const EdgeIdentity(),
  RetainedDeviceReconnect reconnect = EdgeClient.reconnect,
  bool Function()? isCurrent,
}) async {
  if (expected.pending ||
      expected.installationId == null ||
      expected.endpointRevision < 0 ||
      expected.endpointRevision >= 2147483647 ||
      port < 1 ||
      port > 65535 ||
      port == expected.borderPort ||
      !RegExp(r'^[a-f0-9]{64}$').hasMatch(expected.keyFingerprint) ||
      (expected.protected &&
          (expected.deviceSubject == null ||
              expected.protectedOrigin == null))) {
    throw const FormatException('Confirmed identity-bound enrollment required');
  }
  final replacement = StoredEnrollment(
    memberId: expected.memberId,
    keyFingerprint: expected.keyFingerprint,
    borderHost: expected.borderHost,
    borderPort: port,
    clawDomain: expected.clawDomain,
    wsPath: expected.wsPath,
    installationId: expected.installationId,
    deviceSubject: expected.deviceSubject,
    protectedOrigin: expected.protectedOrigin,
    endpointRevision: expected.endpointRevision + 1,
  );
  verifyClawDomainBeforeDial(replacement.toPayload());
  if (await identity.publicKeyFingerprint() != expected.keyFingerprint) {
    throw const FormatException('Retained device key changed');
  }
  if (isCurrent?.call() == false) throw StateError('Recovery was suspended');
  EdgeClient? probe;
  try {
    probe = await reconnect(
      replacement.toPayload(),
      memberId: expected.memberId,
      keyFingerprint: expected.keyFingerprint,
      identity: identity,
    );
    final descriptor = probe.protectedDevice;
    if (probe.isClosed ||
        probe.enrollFingerprint != expected.keyFingerprint ||
        probe.border['installation_id'] != expected.installationId ||
        (expected.protected
            ? descriptor == null ||
                  descriptor.installationId != expected.installationId ||
                  descriptor.principal['subject'] != expected.deviceSubject ||
                  descriptor.origin != expected.protectedOrigin
            : descriptor != null)) {
      throw const FormatException('Retained Border identity changed');
    }
    if (isCurrent?.call() == false) throw StateError('Recovery was suspended');
    await store.replaceEndpoint(expected, replacement, isCurrent: isCurrent);
    return replacement;
  } finally {
    await probe?.close();
  }
}
