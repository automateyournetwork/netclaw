import 'dart:convert';

/// The QR payload rendered by `netclaw risk token --edge`
/// (contracts/edge-enrollment-and-push.md §1).
class EnrollmentQrPayload {
  final String borderHost;
  final int borderPort;
  final String clawDomain;
  final String enrollmentToken;
  final String wsPath;
  final String? installationId;
  // Only populated from retained enrollment, never trusted from a scanned QR.
  final String? expectedDeviceSubject;

  Uri get websocketUri =>
      Uri(scheme: 'wss', host: clawDomain, port: borderPort, path: wsPath);

  const EnrollmentQrPayload({
    required this.borderHost,
    required this.borderPort,
    required this.clawDomain,
    required this.enrollmentToken,
    this.wsPath = '/',
    this.installationId,
    this.expectedDeviceSubject,
  });

  factory EnrollmentQrPayload.fromJson(Map<String, dynamic> json) {
    return EnrollmentQrPayload(
      borderHost: json['border_host'] as String,
      borderPort: json['border_port'] as int,
      clawDomain: json['claw_domain'] as String,
      enrollmentToken: json['enrollment_token'] as String,
      wsPath: json['ws_path'] as String? ?? '/',
      installationId: json['installation_id'] as String?,
    );
  }

  static EnrollmentQrPayload parse(String raw) {
    if (raw.length > 8192) throw const FormatException('QR is too large');
    final payload = EnrollmentQrPayload.fromJson(
      jsonDecode(raw) as Map<String, dynamic>,
    );
    verifyClawDomainBeforeDial(payload);
    if (payload.enrollmentToken.isEmpty ||
        payload.enrollmentToken.length > 2048) {
      throw const FormatException('Invalid enrollment code');
    }
    return payload;
  }
}

/// Raised when a QR's `border_host` does not match its own `claw_domain`
/// (research D7) — the client refuses to dial at all in this case.
class ClawDomainMismatchException implements Exception {
  final String clawDomain;
  final String borderHost;
  ClawDomainMismatchException(this.clawDomain, this.borderHost);

  @override
  String toString() =>
      'claw_domain "$clawDomain" does not match border_host "$borderHost" — refusing to dial';
}

/// D7: the ONLY verification this client performs before dialing is that
/// the host it is about to open a TLS connection to is the QR's own
/// certified domain — it NEVER manually inspects the peer certificate.
/// Standard TLS hostname verification, performed automatically by the
/// platform TLS stack when the socket dials `wss://<claw_domain>:<port>`,
/// does the actual cryptographic check; an untrusted or mismatched
/// certificate simply fails to connect on its own. This function only
/// guards against the QR itself pointing `border_host` somewhere other
/// than the domain it claims to certify, so that case is refused before
/// any network call is attempted at all.
void verifyClawDomainBeforeDial(EnrollmentQrPayload payload) {
  final host = payload.clawDomain;
  if (host.isEmpty ||
      host.length > 253 ||
      !RegExp(r'^[A-Za-z0-9.-]+$').hasMatch(host) ||
      host.startsWith('.') ||
      host.endsWith('.') ||
      host.contains('..') ||
      payload.borderPort < 1 ||
      payload.borderPort > 65535 ||
      !['/', '/mobile/ws'].contains(payload.wsPath) ||
      (payload.wsPath != '/' && payload.installationId == null) ||
      (payload.installationId != null &&
          !RegExp(
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
          ).hasMatch(payload.installationId!))) {
    throw const FormatException('Invalid Border destination');
  }
  if (payload.borderHost != payload.clawDomain) {
    throw ClawDomainMismatchException(payload.clawDomain, payload.borderHost);
  }
}
