import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

typedef Json = Map<String, dynamic>;
bool _id(dynamic value) =>
    value is String && RegExp(r'^[A-Za-z0-9_.:-]{1,200}$').hasMatch(value);
bool _token(dynamic value) =>
    value is String && RegExp(r'^[A-Za-z0-9_-]{43}$').hasMatch(value);
bool _digest(dynamic value) =>
    value is String && RegExp(r'^[a-f0-9]{64}$').hasMatch(value);
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
  const CloudProfile._(this.origin, this.installationId);
  factory CloudProfile(String origin, String installationId) {
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
    return CloudProfile._(origin, installationId);
  }
  String get key => base64Url
      .encode(utf8.encode('$origin|$installationId'))
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

class CloudOwnerClient {
  final CloudProfile profile;
  final CloudOwnerStore store;
  final OwnerTransport transport;
  final DateTime Function() now;
  Json? session, catalog, operation, reference;
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
  }) : store = store ?? CloudOwnerStore(),
       transport = transport ?? HttpsOwnerTransport(),
       now = now ?? DateTime.now;
  bool get busy => _busy;
  bool get identityVerified => _verified;
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

  void _requireSession() {
    if (!authenticated) throw const CloudOwnerError('session_required');
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
    };
    if (method != 'GET') {
      headers['Origin'] = profile.origin;
      headers['Content-Type'] = 'application/json';
      if (bootstrap) {
        headers['X-NetClaw-Owner-Bootstrap'] = '1';
      } else {
        _requireSession();
        headers['X-NetClaw-CSRF'] = _csrf!;
      }
    }
    if (!discovery && !bootstrap && _cookie != null) {
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
      if (result.status == 401 ||
          result.body['code'] == 'installation_changed') {
        session = null;
        _csrf = null;
        _cookie = null;
        await store.write('session.${profile.key}', null);
        throw CloudOwnerError(
          result.status == 401 ? 'session_required' : 'identity_changed',
        );
      }
      if (method == 'POST' &&
          path == '/api/hud/operations' &&
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
    session = null;
    _csrf = null;
    catalog = null;
    operation = null;
    final savedReference = await store.reference(profile);
    _current(generation);
    reference = savedReference;
    notSubmitted = reference?['not_submitted'] == true;
    uncertain = reference != null && !notSubmitted;
    final runtime = (await _request('/api/runtime', discovery: true)).body;
    final capabilities = runtime['capabilities'];
    if (runtime['installationId'] != profile.installationId ||
        runtime['role'] != 'border' ||
        capabilities is! Json ||
        [
          'protectedProfile',
          'protectedOperations',
          'protectedProduction',
        ].any((key) => capabilities[key] != true)) {
      throw const CloudOwnerError('identity_changed');
    }
    _verified = true;
    await store.saveProfile(profile);
    _current(generation);
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
    session = null;
    _csrf = null;
    _cookie = null;
    catalog = null;
    operation = null;
    notSubmitted = false;
    uncertain = reference != null;
  }

  Future<void> login(String ticket) => _exclusive(() async {
    final generation = _generation;
    if (!_verified || !_token(ticket)) {
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
    _requireSession();
    catalog = (await _request('/api/hud/operations/catalog')).body;
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
  }

  Future<void> _retainOperation(Json value) async {
    final generation = _generation;
    _requireSession();
    final ref = reference;
    final review = value['review'];
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
        review['border']['installation_id'] != profile.installationId ||
        review['principal'] is! Json ||
        review['principal']['subject'] != session?['principal']?['subject'] ||
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
    _requireSession();
    reference = next;
    operation = value;
    uncertain = false;
    notSubmitted = false;
  }

  Future<void> prepare(int memberIndex, int modelIndex, int toolIndex) =>
      _exclusive(() async {
        final generation = _generation;
        _requireSession();
        if (reference != null || await store.reference(profile) != null) {
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
    _requireSession();
    final ref = reference;
    if (ref == null) throw const CloudOwnerError('reference_required');
    if (ref['not_submitted'] == true) {
      throw const CloudOwnerError('not_submitted', notSubmitted: true);
    }
    uncertain = true;
    final suffix = ref['operation_id'] != null
        ? '/${Uri.encodeComponent(ref['operation_id'])}'
        : '?client_nonce=${Uri.encodeQueryComponent(ref['client_nonce'])}';
    await _retainOperation((await _request('/api/hud/operations$suffix')).body);
  }

  Future<void> status() => _exclusive(_status);
  bool canDecide(String decision) {
    final op = operation,
        expiry = operation?['review']?['limits']?['expires_at_ms'];
    return authenticated &&
        !busy &&
        !uncertain &&
        reference?['decision_sent'] != true &&
        op != null &&
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
    _requireSession();
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
      uncertain = false;
      notSubmitted = false;
    });
  }
}
