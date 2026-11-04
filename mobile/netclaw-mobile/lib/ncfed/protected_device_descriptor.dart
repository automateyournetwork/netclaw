import 'dart:convert';
import 'enrollment_qr_payload.dart';

const protectedDeviceMethods = [
  'n2n/edge/operations/catalog',
  'n2n/edge/operations/prepare',
  'n2n/edge/operations/status',
  'n2n/edge/operations/decision',
  'n2n/edge/operations/reconcile',
];

/// Only accepted from a completed device-key handshake on trusted WSS.
class ProtectedDeviceDescriptor {
  final String installationId;
  final String origin;
  final Map<String, dynamic> principal;
  const ProtectedDeviceDescriptor(
    this.installationId,
    this.origin,
    this.principal,
  );

  static ProtectedDeviceDescriptor? fromBorder(
    Map<String, dynamic> border,
    EnrollmentQrPayload payload,
  ) {
    final capabilities = border['capabilities'];
    final descriptor = capabilities is Map
        ? capabilities['protected_operations']
        : null;
    if (descriptor == null) {
      if (payload.wsPath == '/mobile/ws' ||
          payload.expectedDeviceSubject != null) {
        throw const FormatException('Protected device capability is missing');
      }
      if (payload.installationId != null &&
          border['installation_id'] != payload.installationId) {
        throw const FormatException('Border installation changed');
      }
      return null;
    }
    if (descriptor is! Map<String, dynamic>) {
      throw const FormatException('Invalid protected device capability');
    }
    final principal = descriptor['principal'];
    final origin = descriptor['origin'];
    final uri = origin is String ? Uri.tryParse(origin) : null;
    if (descriptor['schema'] != 1 ||
        payload.installationId == null ||
        border['installation_id'] != payload.installationId ||
        descriptor['installation_id'] != payload.installationId ||
        uri == null ||
        uri.scheme != 'https' ||
        uri.host != payload.clawDomain ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.path.isNotEmpty ||
        uri.origin != origin ||
        jsonEncode(descriptor['methods']) !=
            jsonEncode(protectedDeviceMethods) ||
        principal is! Map<String, dynamic> ||
        !validDevicePrincipal(principal) ||
        (payload.expectedDeviceSubject != null &&
            principal['subject'] != payload.expectedDeviceSubject) ||
        [
          'text',
          'voice_text',
          'attachments',
          'task_outcomes_v1',
          'request_recovery',
        ].any((key) => capabilities[key] != false)) {
      throw const FormatException(
        'Protected device identity or capability changed',
      );
    }
    return ProtectedDeviceDescriptor(
      payload.installationId!,
      origin as String,
      Map<String, dynamic>.unmodifiable(principal),
    );
  }
}

bool validDevicePrincipal(dynamic value) =>
    value is Map<String, dynamic> &&
    value.length == 4 &&
    value['issuer'] == 'device-key' &&
    value['subject'] is String &&
    RegExp(
      r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
    ).hasMatch(value['subject']) &&
    value['display_name'] is String &&
    (value['display_name'] as String).isNotEmpty &&
    (value['display_name'] as String).length <= 200 &&
    jsonEncode(value['roles']) == '["device-operator"]';
