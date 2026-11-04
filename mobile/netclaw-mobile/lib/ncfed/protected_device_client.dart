import 'dart:convert';
import '../cloud/owner_client.dart';
import 'edge_client.dart';
import 'protected_device_descriptor.dart';

/// Device operations never share owner sessions or references, including when
/// the same installation is also connected in the historical owner screen.
class ProtectedDeviceStore extends CloudOwnerStore {
  final String scope;
  ProtectedDeviceStore(ProtectedDeviceDescriptor descriptor)
    : scope = '${descriptor.installationId}.${descriptor.principal['subject']}';
  @override
  Future<String?> read(String key) =>
      storage.read(key: 'netclaw.device.v1.$scope.$key');
  @override
  Future<void> write(String key, String? value) => value == null
      ? storage.delete(key: 'netclaw.device.v1.$scope.$key')
      : storage.write(key: 'netclaw.device.v1.$scope.$key', value: value);
  @override
  Future<List<CloudProfile>> profiles() async => [];
  @override
  Future<void> saveProfile(CloudProfile profile) async {}
}

/// Narrow adaptation of the reviewed operation state machine to the enrolled,
/// key-proven WSS connection. No HTTP session, token, generic proxy or fallback.
class ProtectedDeviceTransport implements OwnerTransport {
  final EdgeClient edge;
  final ProtectedDeviceDescriptor binding;
  ProtectedDeviceTransport(this.edge, this.binding);

  void _validate() {
    final current = edge.protectedDevice;
    if (edge.isClosed ||
        current == null ||
        current.origin != binding.origin ||
        current.installationId != binding.installationId ||
        jsonEncode(current.principal) != jsonEncode(binding.principal)) {
      throw const CloudOwnerError('identity_changed');
    }
  }

  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  ) async {
    _validate();
    if (uri.origin != binding.origin ||
        uri.hasFragment ||
        uri.userInfo.isNotEmpty ||
        headers['X-NetClaw-Installation'] != binding.installationId ||
        headers.containsKey('Cookie') ||
        headers.containsKey('X-NetClaw-CSRF')) {
      throw const CloudOwnerError('identity_changed');
    }
    if (method == 'GET' && uri.path == '/api/runtime' && !uri.hasQuery) {
      // This descriptor arrived through the real authenticated hello/enroll.
      return OwnerResponse(200, {
        'installationId': binding.installationId,
        'role': 'border',
        'access': {'mode': 'device-key', 'principal': binding.principal},
        'capabilities': {
          'protectedProfile': true,
          'protectedOperations': true,
          'protectedProduction': true,
        },
      });
    }
    final params = <String, dynamic>{'installation_id': binding.installationId};
    String operation;
    if (uri.path == '/api/hud/operations/catalog' &&
        method == 'GET' &&
        !uri.hasQuery) {
      operation = 'catalog';
    } else if (uri.path == '/api/hud/operations' &&
        method == 'POST' &&
        !uri.hasQuery &&
        body != null) {
      operation = 'prepare';
      params.addAll(body);
    } else if (uri.path == '/api/hud/operations' &&
        method == 'GET' &&
        uri.queryParameters.length == 1 &&
        uri.queryParameters.containsKey('client_nonce')) {
      operation = 'status';
      params['client_nonce'] = uri.queryParameters['client_nonce'];
    } else {
      final path = uri.pathSegments;
      if (uri.hasQuery ||
          path.length < 4 ||
          path.length > 5 ||
          path.take(3).join('/') != 'api/hud/operations' ||
          !RegExp(r'^[A-Za-z0-9_.:-]{1,200}$').hasMatch(path[3])) {
        throw const CloudOwnerError('request_refused');
      }
      params['operation_id'] = path[3];
      if (path.length == 4 && method == 'GET') {
        operation = 'status';
      } else if (path.length == 5 &&
          method == 'POST' &&
          ['decision', 'reconcile'].contains(path[4])) {
        operation = path[4];
        params.addAll(body ?? {});
      } else {
        throw const CloudOwnerError('request_refused');
      }
    }
    if (params['installation_id'] != binding.installationId ||
        params.containsKey('auth_context') ||
        params.containsKey('principal')) {
      throw const CloudOwnerError('request_refused');
    }
    try {
      final result = await edge.call('n2n/edge/operations/$operation', params);
      _validate();
      return OwnerResponse(200, result);
    } on EdgeClientException catch (error) {
      final data = error.data;
      if (data != null && data['status'] is int && data['code'] is String) {
        return OwnerResponse(data['status'], {
          'code': data['code'],
          if (operation == 'prepare' && data['admission'] == 'not_submitted')
            'admission': 'not_submitted',
        });
      }
      throw const CloudOwnerError('request_refused');
    }
  }
}

CloudOwnerClient protectedDeviceClient(
  EdgeClient edge, {
  CloudOwnerStore? store,
}) {
  final descriptor = edge.protectedDevice;
  if (descriptor == null) throw const CloudOwnerError('identity_changed');
  return CloudOwnerClient(
    CloudProfile(descriptor.origin, descriptor.installationId),
    expectedDevicePrincipal: descriptor.principal,
    store: store ?? ProtectedDeviceStore(descriptor),
    transport: ProtectedDeviceTransport(edge, descriptor),
  );
}
