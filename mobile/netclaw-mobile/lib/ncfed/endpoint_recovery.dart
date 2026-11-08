import 'edge_client.dart';
import 'edge_identity.dart';
import 'enrollment_qr_payload.dart';
import 'enrollment_store.dart';
import 'cluster_trust.dart';

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
      expected.clusterPin != null ||
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

/// Verify the retained signed manifest before showing or selecting alternatives.
Future<ClusterBinding> retainedCluster(
  StoredEnrollment expected, {
  PublicCrypto crypto = publicCrypto,
}) async {
  if (expected.clusterPin == null ||
      expected.clusterDescriptor == null ||
      expected.protectedOrigin == null ||
      expected.installationId == null) {
    throw const FormatException('Retained cluster manifest required');
  }
  return ClusterBinding.verify(
    expected.clusterDescriptor,
    expected.clusterPin!,
    origin: expected.protectedOrigin!,
    installationId: expected.installationId!,
    nodeId: expected.clusterNodeId,
    crypto: crypto,
  );
}

/// Explicit selection among at most three verified manifest endpoints. Only a
/// retained-key hello is sent; pending approvals and saved references stay put.
Future<StoredEnrollment> replaceClusterEndpoint({
  required EnrollmentStore store,
  required StoredEnrollment expected,
  required String nodeId,
  EdgeIdentity identity = const EdgeIdentity(),
  RetainedDeviceReconnect reconnect = EdgeClient.reconnect,
  PublicCrypto crypto = publicCrypto,
  bool Function()? isCurrent,
}) async {
  if (expected.pending ||
      expected.deviceSubject == null ||
      expected.enrollmentGeneration == null ||
      expected.endpointRevision < 0 ||
      expected.endpointRevision >= 2147483647 ||
      expected.clusterNodeId == nodeId) {
    throw const FormatException('Confirmed cluster identity required');
  }
  final trusted = await retainedCluster(expected, crypto: crypto);
  final target = trusted.node(nodeId),
      rawUri = Uri.parse(trusted.node(nodeId)['endpoints']['wss']);
  final uri = rawUri.replace(port: rawUri.hasPort ? rawUri.port : 443);
  final origin = Uri.parse(target['endpoints']['https']).origin;
  if (uri.replace(scheme: 'https', path: '').origin != origin ||
      await identity.publicKeyFingerprint() != expected.keyFingerprint) {
    throw const FormatException('Cluster endpoint or retained key changed');
  }
  if (isCurrent?.call() == false) throw StateError('Recovery suspended');
  final payload = EnrollmentQrPayload(
    borderHost: uri.host,
    borderPort: uri.port,
    clawDomain: uri.host,
    enrollmentToken: '',
    wsPath: uri.path,
    installationId: target['installation_id'],
    expectedDeviceSubject: expected.deviceSubject,
    expectedEnrollmentGeneration: expected.enrollmentGeneration,
    clusterPin: trusted.pin,
    clusterNodeId: nodeId,
  );
  EdgeClient? probe;
  try {
    probe = await reconnect(
      payload,
      memberId: expected.memberId,
      keyFingerprint: expected.keyFingerprint,
      identity: identity,
    );
    final device = probe.protectedDevice, cluster = probe.clusterBinding;
    if (probe.isClosed ||
        probe.enrollFingerprint != expected.keyFingerprint ||
        device == null ||
        cluster == null ||
        !cluster.pin.sameAudience(trusted.pin) ||
        cluster.pin.revision < trusted.pin.revision ||
        cluster.nodeId != nodeId ||
        device.principal['subject'] != expected.deviceSubject ||
        device.enrollmentGeneration != expected.enrollmentGeneration ||
        device.origin != origin) {
      throw const FormatException('Cluster device identity changed');
    }
    final replacement = StoredEnrollment(
      memberId: expected.memberId,
      keyFingerprint: expected.keyFingerprint,
      borderHost: uri.host,
      borderPort: uri.port,
      clawDomain: uri.host,
      wsPath: uri.path,
      installationId: cluster.installationId,
      deviceSubject: expected.deviceSubject,
      protectedOrigin: device.origin,
      endpointRevision: expected.endpointRevision + 1,
      clusterPin: cluster.pin,
      clusterNodeId: cluster.nodeId,
      clusterDescriptor: cluster.descriptor,
      enrollmentGeneration: expected.enrollmentGeneration,
    );
    await store.replaceEndpoint(expected, replacement, isCurrent: isCurrent);
    return replacement;
  } finally {
    await probe?.close();
  }
}
