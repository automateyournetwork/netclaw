import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../ncfed/protected_device_descriptor.dart';
import '../ncfed/cluster_trust.dart';

typedef Json = Map<String, dynamic>;
bool _id(dynamic value) =>
    value is String && RegExp(r'^[A-Za-z0-9_.:-]{1,200}$').hasMatch(value);
bool _token(dynamic value) =>
    value is String && RegExp(r'^[A-Za-z0-9_-]{43}$').hasMatch(value);
bool _digest(dynamic value) =>
    value is String && RegExp(r'^[a-f0-9]{64}$').hasMatch(value);
bool _uuid(dynamic value) =>
    value is String &&
    RegExp(
      r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
    ).hasMatch(value);
bool _principal(dynamic value, {required bool lab}) =>
    value is Json &&
    value.length == 4 &&
    value['issuer'] == (lab ? 'open-lab' : 'local') &&
    (lab ? _uuid(value['subject']) : _id(value['subject'])) &&
    value['display_name'] is String &&
    (!lab || value['display_name'] == 'Unauthenticated lab operator') &&
    jsonEncode(value['roles']) == (lab ? '["lab-operator"]' : '["owner"]');
bool _samePrincipal(dynamic left, dynamic right) =>
    left is Json &&
    right is Json &&
    left.length == right.length &&
    [
      'issuer',
      'subject',
      'display_name',
      'roles',
    ].every((key) => jsonEncode(left[key]) == jsonEncode(right[key]));
Json _map(dynamic value) {
  if (value is! Json) throw const CloudOwnerError('invalid_response');
  return value;
}

class CloudOwnerError implements Exception {
  final String code;
  final bool notSubmitted;
  const CloudOwnerError(this.code, {this.notSubmitted = false});
  @override
  String toString() => switch (code) {
    'session_required' =>
      'Sign in to this cloud Border to recover existing work.',
    'invalid_profile' =>
      'Enter an exact HTTPS origin and expected installation UUID.',
    'access_refused' =>
      'The cloud Border refused access. Check the same operation; nothing was resent.',
    'identity_changed' =>
      'The selected Border identity or protected capabilities do not match. Nothing was resent.',
    'invalid_cookie' =>
      'The Border did not return a valid secure owner session.',
    'reference_required' =>
      'Recover the retained operation before preparing another.',
    'review_unavailable' =>
      'The exact review is unavailable, expired or no longer actionable. Check status.',
    'not_submitted' =>
      'The review was refused before submission. Nothing was executed.',
    'busy' => 'An action is already in progress.',
    'storage_invalid' =>
      'Saved cloud references are invalid. Preserve them; nothing was submitted.',
    'capacity' =>
      'All eight cloud profile slots are occupied. Existing references are preserved.',
    _ =>
      'The response was not confirmed. Check the same operation; nothing was resent.',
  };
}

class CloudProfile {
  final String origin;
  final String installationId;
  final ClusterBinding? cluster;
  const CloudProfile._(this.origin, this.installationId, this.cluster);
  factory CloudProfile(
    String origin,
    String installationId, {
    ClusterBinding? cluster,
  }) {
    final uri = Uri.tryParse(origin);
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.path.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.origin != origin ||
        !RegExp(
          r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
        ).hasMatch(installationId)) {
      throw const CloudOwnerError('invalid_profile');
    }
    if (cluster != null &&
        (cluster.origin != origin ||
            cluster.installationId != installationId)) {
      throw const CloudOwnerError('invalid_profile');
    }
    return CloudProfile._(origin, installationId, cluster);
  }
  String get key => base64Url
      .encode(
        utf8.encode(
          cluster == null
              ? '$origin|$installationId'
              : 'cluster|${cluster!.pin.clusterId}|${cluster!.pin.generation}',
        ),
      )
      .replaceAll('=', '');
  Json toJson() => {'origin': origin, 'installation_id': installationId};
}

/// Sessions are stored only in native secure storage. Profile and operation
/// identifiers use a separate key; tickets, CSRF, reviews and results never persist.
class CloudOwnerStore {
  final FlutterSecureStorage storage;
  CloudOwnerStore({FlutterSecureStorage? storage})
    : storage = storage ?? const FlutterSecureStorage();
  Future<String?> read(String key) =>
      storage.read(key: 'netclaw.cloud.v1.$key');
  Future<void> write(String key, String? value) => value == null
      ? storage.delete(key: 'netclaw.cloud.v1.$key')
      : storage.write(key: 'netclaw.cloud.v1.$key', value: value);

  Future<List<CloudProfile>> profiles() async {
    final raw = await read('profiles');
    if (raw == null) return [];
    try {
      if (raw.length > 16384) throw const CloudOwnerError('storage_invalid');
      final rows = jsonDecode(raw) as List;
      if (rows.length > 8) throw const CloudOwnerError('storage_invalid');
      final profiles = rows
          .map(
            (row) => CloudProfile(
              row['origin'] as String,
              row['installation_id'] as String,
            ),
          )
          .toList();
      if (profiles.map((p) => p.key).toSet().length != profiles.length) {
        throw const CloudOwnerError('storage_invalid');
      }
      return profiles;
    } catch (_) {
      throw const CloudOwnerError('storage_invalid');
    }
  }

  Future<void> saveProfile(CloudProfile profile) async {
    final rows = await profiles();
    if (rows.any((row) => row.key == profile.key)) return;
    if (rows.length >= 8) throw const CloudOwnerError('capacity');
    await write(
      'profiles',
      jsonEncode([...rows, profile].map((p) => p.toJson()).toList()),
    );
  }

  Future<Json?> reference(CloudProfile profile) async {
    final raw = await read('reference.${profile.key}');
    if (raw == null) return null;
    try {
      if (raw.length > 1024) throw const CloudOwnerError('storage_invalid');
      final value = _map(jsonDecode(raw));
      if (value.keys.any(
            (key) => ![
              'client_nonce',
              'operation_id',
              'decision_sent',
              'not_submitted',
            ].contains(key),
          ) ||
          !_id(value['client_nonce']) ||
          value.containsKey('operation_id') && !_id(value['operation_id']) ||
          value.containsKey('decision_sent') &&
              value['decision_sent'] != true) {
        throw const CloudOwnerError('storage_invalid');
      }
      if (value.containsKey('not_submitted') &&
          (value['not_submitted'] != true ||
              value.containsKey('operation_id') ||
              value.containsKey('decision_sent'))) {
        throw const CloudOwnerError('storage_invalid');
      }
      return value;
    } catch (_) {
      throw const CloudOwnerError('storage_invalid');
    }
  }

  Future<void> saveReference(CloudProfile profile, Json? value) => write(
    'reference.${profile.key}',
    value == null ? null : jsonEncode(value),
  );
}

class OwnerResponse {
  final int status;
  final Json body;
  final List<String> cookies;
  OwnerResponse(this.status, this.body, {this.cookies = const []});
}

abstract class OwnerTransport {
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  );
}

/// Default system trust/hostname verification only. Each request owns its socket,
/// including timeout cleanup. Redirects and responses over 4 MiB fail closed.
class HttpsOwnerTransport implements OwnerTransport {
  @override
  Future<OwnerResponse> send(
    Uri uri,
    String method,
    Map<String, String> headers,
    Json? body,
  ) async {
    if (uri.scheme != 'https' || uri.userInfo.isNotEmpty) {
      throw const CloudOwnerError('invalid_profile');
    }
    final http = HttpClient()..connectionTimeout = const Duration(seconds: 15);
    try {
      return await (() async {
        final request = await http.openUrl(method, uri);
        request.followRedirects = false;
        headers.forEach(request.headers.set);
        if (body != null) request.write(jsonEncode(body));
        final response = await request.close();
        if (response.statusCode >= 300 && response.statusCode < 400) {
          throw const CloudOwnerError('redirect_refused');
        }
        if (response.headers.contentType?.mimeType != 'application/json') {
          throw const CloudOwnerError('invalid_response');
        }
        final bytes = <int>[];
        await for (final part in response) {
          if (bytes.length + part.length > 4 * 1024 * 1024) {
            throw const CloudOwnerError('response_too_large');
          }
          bytes.addAll(part);
        }
        return OwnerResponse(
          response.statusCode,
          _map(jsonDecode(utf8.decode(bytes))),
          cookies: response.headers[HttpHeaders.setCookieHeader] ?? [],
        );
      })().timeout(const Duration(seconds: 35));
    } on CloudOwnerError {
      rethrow;
    } catch (_) {
      throw const CloudOwnerError('transport_uncertain');
    } finally {
      http.close(force: true);
    }
  }
}

/// Transports implement this only after native verification of the current
/// signed manifest. Same-node reconnect may advance its monotone revision.
abstract interface class VerifiedClusterTransport {
  ClusterBinding get verifiedCluster;
}

class CloudOwnerClient {
  final CloudProfile profile;
  final CloudOwnerStore store;
  final OwnerTransport transport;
  final DateTime Function() now;
  Json? session, catalog, operation, reference;
  Json? combined, combinedReference;
  bool combinedUncertain = false;
  Json? _labPrincipal;
  Json? _devicePrincipal;
  final Json? expectedDevicePrincipal;
  bool uncertain = false;
  bool notSubmitted = false;
  bool _verified = false, _busy = false;
  int _generation = 0;
  String? _cookie, _csrf;
  Completer<void>? _idle;
  CloudOwnerClient(
    this.profile, {
    CloudOwnerStore? store,
    OwnerTransport? transport,
    DateTime Function()? now,
    this.expectedDevicePrincipal,
  }) : store = store ?? CloudOwnerStore(),
       transport = transport ?? HttpsOwnerTransport(),
       now = now ?? DateTime.now;
  bool get busy => _busy;
  bool get identityVerified => _verified;
  bool get openLab => _verified && _labPrincipal != null;
  bool get deviceKey => _verified && _devicePrincipal != null;
  bool get _tokenless => openLab || deviceKey;
  bool get operationsReady => _tokenless || authenticated;
  int? _authorityEpoch;
  bool _authorityAvailable = true;
  bool get clusterMode => profile.cluster != null;
  ClusterBinding? get clusterBinding => !clusterMode
      ? null
      : transport is VerifiedClusterTransport
      ? (transport as VerifiedClusterTransport).verifiedCluster
      : profile.cluster;
  bool get canPrepare =>
      operationsReady &&
      !busy &&
      (!clusterMode || _authorityAvailable) &&
      reference == null &&
      combinedReference == null;
  String? get authorityMessage => !clusterMode
      ? null
      : !_authorityAvailable
      ? 'Cluster authority is unavailable. Saved operations are preserved.'
      : operation != null && !_currentReviewEpoch(operation!['review'])
      ? 'The leader changed. This review is stale; check the same operation.'
      : 'Cluster authority epoch ${_authorityEpoch ?? profile.cluster!.epoch ?? "unknown"}. Status observations do not grant execution.';
  bool _currentReviewEpoch(dynamic review) =>
      !clusterMode ||
      review is Json &&
          review['cluster'] is Json &&
          review['cluster']['authority_epoch'] ==
              (_authorityEpoch ?? profile.cluster!.epoch);

  void _retainAuthority(Json value) {
    if (!clusterMode) return;
    final authority = value['authority'], cluster = clusterBinding!;
    if (authority is! Json ||
        authority.length != 6 ||
        authority['mode'] != 'cluster' ||
        authority['cluster_id'] != cluster.pin.clusterId ||
        authority['generation'] != cluster.pin.generation ||
        authority['served_by'] != cluster.nodeId ||
        authority['observation_only'] != true ||
        authority['epoch'] != null &&
            (authority['epoch'] is! int || authority['epoch'] < 1)) {
      throw const CloudOwnerError('identity_changed');
    }
    if (_authorityEpoch != null &&
        authority['epoch'] != null &&
        authority['epoch'] < _authorityEpoch) {
      throw const CloudOwnerError('identity_changed');
    }
    _authorityEpoch = authority['epoch'];
    _authorityAvailable = _authorityEpoch != null;
  }

  bool _reviewIdentity(dynamic review) {
    if (review is! Json || review['border'] is! Json) return false;
    if (!clusterMode) {
      return review['border']['installation_id'] == profile.installationId &&
          !review.containsKey('cluster');
    }
    final c = review['cluster'], binding = clusterBinding!;
    if (c is! Json ||
        c.length != 5 ||
        c['cluster_id'] != binding.pin.clusterId ||
        c['generation'] != binding.pin.generation ||
        c['manifest_revision'] is! int ||
        c['manifest_revision'] < 1 ||
        c['manifest_revision'] > binding.pin.revision ||
        c['authority_epoch'] is! int ||
        c['authority_epoch'] < 1) {
      return false;
    }
    return binding.nodes.any(
      (n) =>
          n['node_id'] == c['issuer_node_id'] &&
          n['installation_id'] == review['border']['installation_id'] &&
          n['key_id'] == review['border']['key_id'] &&
          n['identity'] == review['border']['identity'],
    );
  }

  Json? get principal => deviceKey
      ? _devicePrincipal
      : openLab
      ? _labPrincipal
      : session?['principal'];

  static Json? _runtimePrincipal(
    Json runtime, {
    String? installationId,
    Json? expectedDevicePrincipal,
  }) {
    final capabilities = runtime['capabilities'], access = runtime['access'];
    if (!_uuid(runtime['installationId']) ||
        installationId != null && runtime['installationId'] != installationId ||
        runtime['role'] != 'border' ||
        capabilities is! Json ||
        [
          'protectedProfile',
          'protectedOperations',
          'protectedProduction',
        ].any((key) => capabilities[key] != true)) {
      throw const CloudOwnerError('identity_changed');
    }
    if (expectedDevicePrincipal != null) {
      if (!validDevicePrincipal(expectedDevicePrincipal) ||
          access is! Json ||
          access['mode'] != 'device-key' ||
          !validDevicePrincipal(access['principal']) ||
          !_samePrincipal(access['principal'], expectedDevicePrincipal)) {
        throw const CloudOwnerError('identity_changed');
      }
      return Map<String, dynamic>.from(access['principal']);
    }
    // Absent access is the existing protected owner-session contract. Never
    // infer lab access from a failed authentication response or unknown mode.
    if (!runtime.containsKey('access')) return null;
    if (access is! Json ||
        access['mode'] != 'open-lab' ||
        !_principal(access['principal'], lab: true)) {
      throw const CloudOwnerError('identity_changed');
    }
    return Map<String, dynamic>.from(access['principal']);
  }

  void _current(int generation) {
    if (generation != _generation) throw const CloudOwnerError('suspended');
  }

  bool get authenticated =>
      _verified &&
      session != null &&
      (session!['expires_ms'] as int) > now().millisecondsSinceEpoch &&
      _cookie != null &&
      _csrf != null;
  String get _cookieName => '__Host-nc_owner_${profile.installationId}';

  Future<void> _exclusive(Future<void> Function() action) async {
    if (_busy) throw const CloudOwnerError('busy');
    _busy = true;
    _idle = Completer<void>();
    try {
      await action();
    } finally {
      _busy = false;
      _idle!.complete();
    }
  }

  void _requireAccess() {
    if (!operationsReady) throw const CloudOwnerError('session_required');
  }

  Future<OwnerResponse> _request(
    String path, {
    String method = 'GET',
    Json? body,
    bool bootstrap = false,
    bool discovery = false,
  }) async {
    if (!discovery && !_verified) {
      throw const CloudOwnerError('identity_changed');
    }
    final generation = _generation;
    final headers = <String, String>{
      'Accept': 'application/json',
      'X-NetClaw-Installation': profile.installationId,
      if (clusterMode) 'X-NetClaw-Cluster-ID': clusterBinding!.pin.clusterId,
      if (clusterMode)
        'X-NetClaw-Cluster-Generation': clusterBinding!.pin.generation,
    };
    if (method != 'GET') {
      headers['Origin'] = profile.origin;
      headers['Content-Type'] = 'application/json';
      if (bootstrap) {
        headers['X-NetClaw-Owner-Bootstrap'] = '1';
      } else {
        _requireAccess();
        if (!_tokenless) headers['X-NetClaw-CSRF'] = _csrf!;
      }
    }
    if (!_tokenless && !discovery && !bootstrap && _cookie != null) {
      headers['Cookie'] = '$_cookieName=$_cookie';
    }
    final result = await transport.send(
      Uri.parse('${profile.origin}$path'),
      method,
      headers,
      body,
    );
    if (generation != _generation) throw const CloudOwnerError('suspended');
    if (result.status < 200 || result.status >= 300) {
      if (clusterMode &&
          [
            'no_quorum',
            'authority_unavailable',
            'stale_authority',
            'recovery_fenced',
            'node_retired',
          ].contains(result.body['code'])) {
        _authorityAvailable = false;
        throw CloudOwnerError(result.body['code']);
      }
      if (result.status == 401 ||
          result.body['code'] == 'installation_changed') {
        if (_tokenless) {
          _verified = false;
          _labPrincipal = null;
          _devicePrincipal = null;
          catalog = null;
          operation = null;
          combined = null;
          combinedUncertain = combinedReference != null;
          uncertain = reference != null;
          throw CloudOwnerError(
            result.body['code'] == 'installation_changed'
                ? 'identity_changed'
                : 'access_refused',
          );
        }
        session = null;
        _csrf = null;
        _cookie = null;
        await store.write('session.${profile.key}', null);
        throw CloudOwnerError(
          result.status == 401 ? 'session_required' : 'identity_changed',
        );
      }
      if (method == 'POST' &&
          [
            '/api/hud/operations',
            '/api/hud/operations/combined',
          ].contains(path) &&
          result.body['admission'] == 'not_submitted') {
        throw const CloudOwnerError('not_submitted', notSubmitted: true);
      }
      throw const CloudOwnerError('request_refused');
    }
    return result;
  }

  void _retainSession(Json value) {
    final principal = value['principal'];
    if (value['authenticated'] != true ||
        value['installation_id'] != profile.installationId ||
        !_token(value['csrf_token']) ||
        value['expires_ms'] is! int ||
        value['expires_ms'] <= now().millisecondsSinceEpoch ||
        principal is! Json ||
        principal['issuer'] != 'local' ||
        !_id(principal['subject']) ||
        principal['display_name'] is! String ||
        principal['roles'] is! List ||
        jsonEncode(principal['roles']) != '["owner"]') {
      throw const CloudOwnerError('invalid_response');
    }
    _csrf = value['csrf_token'];
    session = {...value}..remove('csrf_token');
  }

  Future<void> _initialize() async {
    final generation = _generation;
    _verified = false;
    _labPrincipal = null;
    _devicePrincipal = null;
    session = null;
    _csrf = null;
    _cookie = null;
    catalog = null;
    operation = null;
    combined = null;
    combinedUncertain = combinedReference != null;
    final savedReference = await store.reference(profile);
    _current(generation);
    reference = savedReference;
    notSubmitted = reference?['not_submitted'] == true;
    uncertain = reference != null && !notSubmitted;
    final runtime = (await _request('/api/runtime', discovery: true)).body;
    final accessPrincipal = _runtimePrincipal(
      runtime,
      installationId: profile.installationId,
      expectedDevicePrincipal: expectedDevicePrincipal,
    );
    if (expectedDevicePrincipal == null) {
      _labPrincipal = accessPrincipal;
    } else {
      _devicePrincipal = accessPrincipal;
    }
    _verified = true;
    if (clusterMode) {
      _authorityEpoch = clusterBinding!.epoch;
      _authorityAvailable = clusterBinding!.available;
    }
    await store.saveProfile(profile);
    _current(generation);
    if (_tokenless) {
      await _loadOwned();
      return;
    }
    final savedCookie = await store.read('session.${profile.key}');
    _current(generation);
    _cookie = savedCookie;
    if (_cookie == null) return;
    if (!_token(_cookie)) throw const CloudOwnerError('invalid_cookie');
    _retainSession((await _request('/api/hud/owner/session')).body);
    await _loadOwned();
  }

  Future<void> initialize() => _exclusive(_initialize);
  Future<void> resume() async {
    if (_busy) await _idle!.future;
    await initialize(); // GET only; no automatic prepare, approval or reconcile.
  }

  void suspend() {
    _generation++;
    _verified = false;
    _labPrincipal = null;
    _devicePrincipal = null;
    session = null;
    _csrf = null;
    _cookie = null;
    catalog = null;
    operation = null;
    combined = null;
    combinedUncertain = combinedReference != null;
    notSubmitted = false;
    uncertain = reference != null;
  }

  Future<void> login(String ticket) => _exclusive(() async {
    final generation = _generation;
    if (!_verified ||
        _tokenless ||
        expectedDevicePrincipal != null ||
        !_token(ticket)) {
      throw const CloudOwnerError('session_required');
    }
    final response = await _request(
      '/api/hud/owner/session',
      method: 'POST',
      body: {'ticket': ticket},
      bootstrap: true,
    );
    if (response.cookies.length != 1) {
      throw const CloudOwnerError('invalid_cookie');
    }
    final cookie = Cookie.fromSetCookieValue(response.cookies.single);
    if (cookie.name != _cookieName ||
        !_token(cookie.value) ||
        !cookie.secure ||
        !cookie.httpOnly ||
        cookie.path != '/' ||
        cookie.domain != null ||
        cookie.sameSite != SameSite.strict) {
      throw const CloudOwnerError('invalid_cookie');
    }
    _retainSession(response.body);
    await store.write('session.${profile.key}', cookie.value);
    _current(generation);
    _cookie = cookie.value;
    await _loadOwned();
  });

  Future<void> logout() => _exclusive(() async {
    if (_tokenless) {
      suspend();
      return;
    }
    try {
      if (authenticated) {
        await _request('/api/hud/owner/session', method: 'DELETE', body: {});
      }
    } finally {
      suspend();
      await store.write('session.${profile.key}', null);
    }
  });

  Future<void> _loadOwned() async {
    _requireAccess();
    catalog = (await _request('/api/hud/operations/catalog')).body;
    if (clusterMode) {
      _retainAuthority(catalog!);
      if (jsonEncode(catalog!['capabilities']) != '["cluster_execution_v2"]') {
        throw const CloudOwnerError('invalid_response');
      }
    }
    if (!_id(catalog!['revision']) || catalog!['members'] is! List) {
      catalog = null;
      throw const CloudOwnerError('invalid_response');
    }
    try {
      final members = catalog!['members'] as List;
      if (members.length > 64) throw const CloudOwnerError('invalid_response');
      for (final entry in members) {
        final member = _map(entry);
        if (member['member'] is! Json ||
            member['member']['member_id'] is! String ||
            member['model_profiles'] is! List ||
            member['tools'] is! List ||
            (member['model_profiles'] as List).length > 64 ||
            (member['tools'] as List).length > 64) {
          throw const CloudOwnerError('invalid_response');
        }
        for (final model in member['model_profiles']) {
          if (model is! Json || !_id(model['profile_id'])) {
            throw const CloudOwnerError('invalid_response');
          }
        }
        for (final tool in member['tools']) {
          if (tool is! Json ||
              ![
                'pyats_run_show_command',
                'netbox_get_object_by_id',
                'subnet_calculator',
                'subnet_calculator_v6',
              ].contains(tool['tool']) ||
              tool['arguments'] is! Json) {
            throw const CloudOwnerError('invalid_response');
          }
        }
      }
    } catch (_) {
      catalog = null;
      throw const CloudOwnerError('invalid_response');
    }
    if (reference != null && !notSubmitted) await _status();
    final generation = _generation;
    final savedCombined = await _readCombinedReference();
    _current(generation);
    _requireAccess();
    combinedReference = savedCombined;
    combinedUncertain =
        combinedReference != null &&
        combinedReference!['not_submitted'] != true;
    if (combinedReference != null &&
        combinedReference!['not_submitted'] != true) {
      await _combinedStatus();
    }
  }

  Future<void> _retainOperation(
    Json value, {
    bool allowHistorical = false,
  }) async {
    final generation = _generation;
    _requireAccess();
    final ref = reference;
    final review = value['review'];
    _retainAuthority(value);
    if (clusterMode && value['result_reference'] != null) {
      final result = value['result_reference'];
      if (result is! Json ||
          result.length != 6 ||
          !_digest(result['digest']) ||
          !_uuid(result['receipt_id']) ||
          !_uuid(result['artifact_id']) ||
          result['artifact_id'] != value['operation_id'] ||
          result['member'] is! Json ||
          utf8.decode(clusterCanonical(result['member'])) !=
              utf8.decode(clusterCanonical(review?['member'])) ||
          !['succeeded', 'failed', 'refused'].contains(result['outcome']) ||
          !['not_started', 'finished'].contains(result['effect_status']) ||
          result['outcome'] == 'succeeded' &&
              result['effect_status'] != 'finished') {
        throw const CloudOwnerError('invalid_response');
      }
    }
    if (ref == null ||
        !_id(value['operation_id']) ||
        value['client_nonce'] != ref['client_nonce'] ||
        ref['operation_id'] != null &&
            value['operation_id'] != ref['operation_id'] ||
        value['revision'] is! int ||
        value['revision'] < 0 ||
        !_digest(value['review_digest']) ||
        review is! Json ||
        review['border'] is! Json ||
        !_reviewIdentity(review) ||
        review['principal'] is! Json ||
        !(_samePrincipal(review['principal'], principal) ||
            openLab &&
                allowHistorical &&
                _principal(review['principal'], lab: false)) ||
        [
          'member',
          'model_profile',
          'tool_call',
          'limits',
        ].any((key) => review[key] is! Json) ||
        value['allowed_actions'] is! List) {
      throw const CloudOwnerError('invalid_response');
    }
    final next = <String, dynamic>{
      'client_nonce': value['client_nonce'],
      'operation_id': value['operation_id'],
      if (ref['decision_sent'] == true) 'decision_sent': true,
    };
    await store.saveReference(profile, next);
    _current(generation);
    _requireAccess();
    reference = next;
    operation = value;
    uncertain = false;
    notSubmitted = false;
  }

  Future<void> prepare(int memberIndex, int modelIndex, int toolIndex) =>
      _exclusive(() async {
        final generation = _generation;
        _requireAccess();
        if (clusterMode && !_authorityAvailable) {
          throw const CloudOwnerError('authority_unavailable');
        }
        if (combinedReference != null ||
            reference != null ||
            await store.reference(profile) != null) {
          throw const CloudOwnerError('reference_required');
        }
        _current(generation);
        final member = _map((catalog?['members'] as List)[memberIndex]);
        final model = _map((member['model_profiles'] as List)[modelIndex]);
        final tool = _map((member['tools'] as List)[toolIndex]);
        final nonce = base64Url
            .encode(List.generate(32, (_) => Random.secure().nextInt(256)))
            .replaceAll('=', '');
        final ref = <String, dynamic>{'client_nonce': nonce};
        await store.saveReference(
          profile,
          ref,
        ); // Fail before sending if persistence fails.
        _current(generation);
        reference = ref;
        operation = null;
        combined = null;
        combinedUncertain = combinedReference != null;
        uncertain = true;
        notSubmitted = false;
        try {
          await _retainOperation(
            (await _request(
              '/api/hud/operations',
              method: 'POST',
              body: {
                'client_nonce': nonce,
                'catalog_revision': catalog!['revision'],
                'member_id': member['member']['member_id'],
                'model_profile_id': model['profile_id'],
                'tool': tool['tool'],
                'arguments': tool['arguments'],
              },
            )).body,
          );
        } on CloudOwnerError catch (error) {
          if (error.notSubmitted) {
            final proven = <String, dynamic>{...ref, 'not_submitted': true};
            await store.saveReference(profile, proven);
            _current(generation);
            reference = proven;
            notSubmitted = true;
            uncertain = false;
          }
          rethrow;
        }
      });

  Future<void> _status() async {
    _requireAccess();
    final ref = reference;
    if (ref == null) throw const CloudOwnerError('reference_required');
    if (ref['not_submitted'] == true) {
      throw const CloudOwnerError('not_submitted', notSubmitted: true);
    }
    uncertain = true;
    final suffix = ref['operation_id'] != null
        ? '/${Uri.encodeComponent(ref['operation_id'])}'
        : '?client_nonce=${Uri.encodeQueryComponent(ref['client_nonce'])}';
    await _retainOperation(
      (await _request('/api/hud/operations$suffix')).body,
      allowHistorical: true,
    );
  }

  Future<void> status() => _exclusive(_status);
  bool canDecide(String decision) {
    final op = operation,
        expiry = operation?['review']?['limits']?['expires_at_ms'];
    return operationsReady &&
        (!clusterMode ||
            _authorityAvailable && _currentReviewEpoch(op?['review'])) &&
        !busy &&
        !uncertain &&
        reference?['decision_sent'] != true &&
        op != null &&
        _samePrincipal(op['review']?['principal'], principal) &&
        ['approve', 'deny'].contains(decision) &&
        (op['allowed_actions'] as List).contains(decision) &&
        (decision != 'approve' ||
            expiry is int && expiry > now().millisecondsSinceEpoch);
  }

  Future<void> decide(
    String decision, {
    required int revision,
    required String reviewDigest,
  }) async {
    if (!canDecide(decision) ||
        operation!['revision'] != revision ||
        operation!['review_digest'] != reviewDigest) {
      throw const CloudOwnerError('review_unavailable');
    }
    await _exclusive(() async {
      final generation = _generation;
      final marked = <String, dynamic>{...reference!, 'decision_sent': true};
      await store.saveReference(profile, marked);
      _current(generation);
      reference = marked;
      uncertain = true;
      await _retainOperation(
        (await _request(
          '/api/hud/operations/${Uri.encodeComponent(reference!['operation_id'])}/decision',
          method: 'POST',
          body: {
            'revision': revision,
            'review_digest': reviewDigest,
            'decision': decision,
          },
        )).body,
      );
    });
  }

  Future<void> reconcile() => _exclusive(() async {
    _requireAccess();
    if (reference?['operation_id'] == null) {
      throw const CloudOwnerError('reference_required');
    }
    uncertain = true;
    await _retainOperation(
      (await _request(
        '/api/hud/operations/${Uri.encodeComponent(reference!['operation_id'])}/reconcile',
        method: 'POST',
        body: {},
      )).body,
      allowHistorical: true,
    );
  });

  bool get canRemove {
    final op = operation;
    if (uncertain || busy) return false;
    if (notSubmitted &&
        reference?['not_submitted'] == true &&
        reference?['operation_id'] == null) {
      return true;
    }
    if (op == null || op['reconciliation_required'] != false) return false;
    if (['refused', 'denied', 'revoked'].contains(op['state']) &&
        op['attempt_count'] == 0 &&
        op['may_have_executed'] == false &&
        op['result'] == null) {
      return true;
    }
    return ['completed', 'failed', 'cancelled'].contains(op['state']) &&
        op['result']?['verified'] == true &&
        op['result']?['durable_ack'] == true &&
        op['result']?['ack_delivery_pending'] == false;
  }

  Future<void> removeResolvedReference() async {
    if (!canRemove) throw const CloudOwnerError('reference_required');
    await _exclusive(() async {
      await store.saveReference(profile, null);
      reference = null;
      operation = null;
      combined = null;
      combinedUncertain = combinedReference != null;
      uncertain = false;
      notSubmitted = false;
    });
  }

  String get _combinedKey {
    _requireAccess();
    return 'combined.${profile.key}.${principal!['issuer']}.${principal!['subject']}';
  }

  Json _validCombinedReference(dynamic value) {
    final ref = _map(value);
    if (!_id(ref['client_nonce']) ||
        ref.keys.any(
          (k) => ![
            'client_nonce',
            'parent_id',
            'children',
            'cancel_sent',
            'not_submitted',
          ].contains(k),
        ) ||
        ref.containsKey('parent_id') && !_id(ref['parent_id']) ||
        ref.containsKey('cancel_sent') &&
            (ref['cancel_sent'] != true || ref['parent_id'] == null) ||
        ref.containsKey('not_submitted') &&
            (ref['not_submitted'] != true ||
                ref['parent_id'] != null ||
                ref['children'] != null ||
                ref['cancel_sent'] != null)) {
      throw const CloudOwnerError('storage_invalid');
    }
    final children = ref['children'];
    if (ref['parent_id'] != null && children == null ||
        children != null &&
            (ref['parent_id'] == null ||
                children is! List ||
                children.length != 2 ||
                children.any(
                  (c) =>
                      c is! Json ||
                      !_id(c['operation_id']) ||
                      c.keys.any(
                        (k) => !['operation_id', 'decision_sent'].contains(k),
                      ) ||
                      c.containsKey('decision_sent') &&
                          c['decision_sent'] != true,
                ) ||
                children[0]['operation_id'] == children[1]['operation_id'])) {
      throw const CloudOwnerError('storage_invalid');
    }
    return ref;
  }

  Future<Json?> _readCombinedReference() async {
    final raw = await store.read(_combinedKey);
    if (raw == null) return null;
    if (raw.length > 2048) throw const CloudOwnerError('storage_invalid');
    try {
      return _validCombinedReference(jsonDecode(raw));
    } catch (_) {
      throw const CloudOwnerError('storage_invalid');
    }
  }

  Future<void> _saveCombinedReference(Json value) async {
    final generation = _generation,
        ref = _validCombinedReference(value),
        old = combinedReference;
    if (old != null &&
        (old['client_nonce'] != ref['client_nonce'] ||
            old['parent_id'] != null && old['parent_id'] != ref['parent_id'] ||
            old['cancel_sent'] == true && ref['cancel_sent'] != true ||
            old['children'] is List &&
                [0, 1].any(
                  (i) =>
                      old['children'][i]['operation_id'] !=
                          ref['children']?[i]['operation_id'] ||
                      old['children'][i]['decision_sent'] == true &&
                          ref['children'][i]['decision_sent'] != true,
                ))) {
      throw const CloudOwnerError('identity_changed');
    }
    await store.write(_combinedKey, jsonEncode(ref));
    _current(generation);
    _requireAccess();
    combinedReference = ref;
  }

  Map<int, List<Json>> combinedChoices() {
    final choices = <int, List<Json>>{4: [], 6: []};
    if (catalog?['capabilities'] is! List ||
        !(catalog!['capabilities'] as List).contains(
          'calculator_combined_v1',
        )) {
      return choices;
    }
    for (final member in catalog!['members']) {
      for (final family in [4, 6]) {
        for (final model in member['model_profiles']) {
          if (model['profile_id'] != 'ollama-cpu-ipv$family' ||
              model['provider'] != 'ollama' ||
              !_id(model['profile_revision'])) {
            continue;
          }
          for (final tool in member['tools']) {
            if (tool['tool'] !=
                    (family == 4
                        ? 'subnet_calculator'
                        : 'subnet_calculator_v6') ||
                tool['arguments'] is! Json ||
                tool['arguments'].length != 1 ||
                tool['arguments']['cidr'] is! String ||
                (tool['arguments']['cidr'] as String).length > 100) {
              continue;
            }
            choices[family]!.add({
              'family': family,
              'member_id': member['member']['member_id'],
              'profile_revision': model['profile_revision'],
              'cidr': tool['arguments']['cidr'],
            });
            if (choices[family]!.length > 100) {
              throw const CloudOwnerError('invalid_response');
            }
          }
        }
      }
    }
    return choices;
  }

  Future<void> _retainCombined(Json value) async {
    _requireAccess();
    final ref = combinedReference, children = value['children'];
    if (ref == null ||
        value['schemaVersion'] != 1 ||
        !_id(value['parent_id']) ||
        value['client_nonce'] != ref['client_nonce'] ||
        ref['parent_id'] != null && ref['parent_id'] != value['parent_id'] ||
        value['expires_at_ms'] is! int ||
        ![
          'awaiting_decisions',
          'running',
          'complete',
          'partial',
          'failed',
          'cancelled',
          'unknown',
        ].contains(value['state']) ||
        children is! List ||
        children.length != 2) {
      throw const CloudOwnerError('invalid_response');
    }
    for (final i in [0, 1]) {
      final c = _map(children[i]), r = c['review'];
      if (c['index'] != i ||
          c['family'] != [4, 6][i] ||
          !_id(c['operation_id']) ||
          !_id(c['client_nonce']) ||
          ref['children'] != null &&
              ref['children'][i]['operation_id'] != c['operation_id'] ||
          c['revision'] is! int ||
          !_digest(c['review_digest']) ||
          r is! Json ||
          r['border']?['installation_id'] != profile.installationId ||
          !_samePrincipal(r['principal'], principal) ||
          [
            'member',
            'model_profile',
            'tool_call',
            'limits',
          ].any((k) => r[k] is! Json) ||
          c['allowed_actions'] is! List) {
        throw const CloudOwnerError('identity_changed');
      }
    }
    if (children[0]['operation_id'] == children[1]['operation_id']) {
      throw const CloudOwnerError('invalid_response');
    }
    await _saveCombinedReference({
      ...ref,
      'parent_id': value['parent_id'],
      'children': [
        for (final i in [0, 1])
          {
            'operation_id': children[i]['operation_id'],
            if (ref['children']?[i]['decision_sent'] == true)
              'decision_sent': true,
          },
      ],
    });
    combined = value;
    combinedUncertain = false;
  }

  Future<void> prepareCombined(List<Json> children) => _exclusive(() async {
    _requireAccess();
    final generation = _generation;
    if (reference != null ||
        combinedReference != null ||
        await _readCombinedReference() != null) {
      throw const CloudOwnerError('reference_required');
    }
    _current(generation);
    final choices = combinedChoices();
    if (children.length != 2 ||
        [0, 1].any(
          (i) =>
              children[i]['family'] != [4, 6][i] ||
              !choices[[4, 6][i]]!.any(
                (v) =>
                    v.length == children[i].length &&
                    v.keys.every((k) => v[k] == children[i][k]),
              ),
        )) {
      throw const CloudOwnerError('review_unavailable');
    }
    final nonce = base64Url
        .encode(List.generate(32, (_) => Random.secure().nextInt(256)))
        .replaceAll('=', '');
    final ref = <String, dynamic>{'client_nonce': nonce};
    await _saveCombinedReference(ref);
    combinedUncertain = true;
    try {
      await _retainCombined(
        (await _request(
          '/api/hud/operations/combined',
          method: 'POST',
          body: {'client_nonce': nonce, 'children': children},
        )).body,
      );
    } on CloudOwnerError catch (error) {
      if (error.notSubmitted) {
        await _saveCombinedReference({...ref, 'not_submitted': true});
        combinedUncertain = false;
      }
      rethrow;
    }
  });

  Future<void> _combinedStatus() async {
    _requireAccess();
    final ref = combinedReference;
    if (ref == null || ref['not_submitted'] == true) {
      throw const CloudOwnerError('reference_required');
    }
    combinedUncertain = true;
    final suffix = ref['parent_id'] != null
        ? '/${Uri.encodeComponent(ref['parent_id'])}'
        : '?client_nonce=${Uri.encodeQueryComponent(ref['client_nonce'])}';
    await _retainCombined(
      (await _request('/api/hud/operations/combined$suffix')).body,
    );
  }

  Future<void> combinedStatus() => _exclusive(_combinedStatus);

  bool canDecideCombined(int index, String decision) {
    if (![0, 1].contains(index) ||
        !operationsReady ||
        busy ||
        combinedUncertain ||
        combined == null ||
        combinedReference?['cancel_sent'] == true ||
        combinedReference?['children']?[index]['decision_sent'] == true) {
      return false;
    }
    final c = combined!['children'][index],
        expiry = c['review']['limits']['expires_at_ms'];
    return c['state'] == 'review_pending' &&
        ['approve', 'deny'].contains(decision) &&
        (c['allowed_actions'] as List).contains(decision) &&
        (decision != 'approve' ||
            expiry is int &&
                expiry > now().millisecondsSinceEpoch &&
                combined!['expires_at_ms'] > now().millisecondsSinceEpoch);
  }

  Future<void> decideCombined(
    int index,
    String decision, {
    required int revision,
    required String reviewDigest,
  }) async {
    if (!canDecideCombined(index, decision)) {
      throw const CloudOwnerError('review_unavailable');
    }
    await _exclusive(() async {
      await _combinedStatus();
      final c = combined!['children'][index];
      if (c['revision'] != revision ||
          c['review_digest'] != reviewDigest ||
          !(c['allowed_actions'] as List).contains(decision) ||
          combinedReference!['children'][index]['decision_sent'] == true ||
          combinedReference!['cancel_sent'] == true ||
          c['state'] != 'review_pending' ||
          decision == 'approve' &&
              (c['review']['limits']['expires_at_ms'] <=
                      now().millisecondsSinceEpoch ||
                  combined!['expires_at_ms'] <= now().millisecondsSinceEpoch)) {
        throw const CloudOwnerError('review_unavailable');
      }
      final marked = _map(jsonDecode(jsonEncode(combinedReference)));
      marked['children'][index]['decision_sent'] = true;
      await _saveCombinedReference(marked);
      combinedUncertain = true;
      await _request(
        '/api/hud/operations/${Uri.encodeComponent(c['operation_id'])}/decision',
        method: 'POST',
        body: {
          'revision': revision,
          'review_digest': reviewDigest,
          'decision': decision,
        },
      );
      await _combinedStatus();
    });
  }

  Future<void> cancelCombined() => _exclusive(() async {
    final ref = combinedReference;
    if (ref?['parent_id'] == null || ref?['cancel_sent'] == true) {
      throw const CloudOwnerError('reference_required');
    }
    await _saveCombinedReference({...ref!, 'cancel_sent': true});
    combinedUncertain = true;
    await _request(
      '/api/hud/operations/combined/${Uri.encodeComponent(ref['parent_id'])}/cancel',
      method: 'POST',
      body: {},
    );
    await _combinedStatus();
  });
  bool get canRemoveCombined =>
      !busy &&
      !combinedUncertain &&
      combinedReference != null &&
      (combinedReference!['not_submitted'] == true ||
          combined != null &&
              [
                'complete',
                'partial',
                'failed',
                'cancelled',
              ].contains(combined!['state']) &&
              (combined!['children'] as List).every(
                (c) =>
                    c['reconciliation_required'] == false &&
                    (c['may_have_executed'] != true ||
                        c['result']?['verified'] == true &&
                            c['result']?['durable_ack'] == true &&
                            c['result']?['ack_delivery_pending'] == false),
              ));
  Future<void> removeCombinedReference() async {
    if (!canRemoveCombined) throw const CloudOwnerError('reference_required');
    await _exclusive(() async {
      await store.write(_combinedKey, null);
      combinedReference = null;
      combined = null;
      combinedUncertain = false;
    });
  }
}
