import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'enrollment_qr_payload.dart';

/// What's needed to reconnect without re-scanning a QR: the fixed identity
/// this device enrolled under, the Border-issued key fingerprint
/// `EdgeClient.reconnect`/`reconnectInPlace` prove possession of, and the
/// connection details (no `enrollment_token` — that's single-use and long
/// since consumed).
class StoredEnrollment {
  final String memberId;
  final String keyFingerprint;
  final String borderHost;
  final int borderPort;
  final String clawDomain;
  final String wsPath;
  final String? installationId;
  final String? deviceSubject;
  final bool pending;
  final int endpointRevision;
  final String? protectedOrigin;
  bool get protected => deviceSubject != null || wsPath == '/mobile/ws';

  const StoredEnrollment({
    required this.memberId,
    required this.keyFingerprint,
    required this.borderHost,
    required this.borderPort,
    required this.clawDomain,
    this.wsPath = '/',
    this.installationId,
    this.deviceSubject,
    this.pending = false,
    this.endpointRevision = 0,
    this.protectedOrigin,
  });

  EnrollmentQrPayload toPayload({String enrollmentToken = ''}) =>
      EnrollmentQrPayload(
        borderHost: borderHost,
        borderPort: borderPort,
        clawDomain: clawDomain,
        enrollmentToken: enrollmentToken,
        wsPath: wsPath,
        installationId: installationId,
        expectedDeviceSubject: deviceSubject,
      );

  Map<String, dynamic> toJson() => {
    'member_id': memberId,
    'key_fingerprint': keyFingerprint,
    'border_host': borderHost,
    'border_port': borderPort,
    'claw_domain': clawDomain,
    if (wsPath != '/') 'ws_path': wsPath,
    if (installationId != null) 'installation_id': installationId,
    if (deviceSubject != null) 'device_subject': deviceSubject,
    if (pending) 'pending': true,
    if (endpointRevision != 0) 'endpoint_revision': endpointRevision,
    if (protectedOrigin != null) 'protected_origin': protectedOrigin,
  };

  factory StoredEnrollment.fromJson(Map<String, dynamic> json) =>
      StoredEnrollment(
        memberId: json['member_id'] as String,
        keyFingerprint: json['key_fingerprint'] as String,
        borderHost: json['border_host'] as String,
        borderPort: json['border_port'] as int,
        clawDomain: json['claw_domain'] as String,
        wsPath: json['ws_path'] as String? ?? '/',
        installationId: json['installation_id'] as String?,
        deviceSubject: json['device_subject'] as String?,
        pending: json['pending'] == true,
        endpointRevision: json['endpoint_revision'] as int? ?? 0,
        protectedOrigin: json['protected_origin'] as String?,
      );
}

/// Persists the single active enrollment across app restarts (feature 068
/// polish) — without this, every cold start regenerated a fresh `memberId`
/// and re-showed the QR scanner, federating a brand-new edge member every
/// single launch instead of reconnecting as the same one. Production
/// callers construct this with `await getApplicationDocumentsDirectory()`;
/// tests pass a temp directory directly (mirrors `ConversationStore`/
/// `MessageFeedStore`'s existing pattern).
class EnrollmentStore {
  static final _writers = <String, Future<void>>{};
  final Directory directory;

  EnrollmentStore(this.directory);

  File _file() => File('${directory.path}/ncfed_enrollment.json');

  Future<StoredEnrollment?> load() async {
    final file = _file();
    if (!await file.exists()) return null;
    final text = await file.readAsString();
    if (text.trim().isEmpty) return null;
    return StoredEnrollment.fromJson(jsonDecode(text) as Map<String, dynamic>);
  }

  Future<T> _write<T>(Future<T> Function() action) async {
    final path = _file().absolute.path;
    final previous = _writers[path] ?? Future<void>.value();
    final complete = Completer<void>();
    _writers[path] = complete.future;
    await previous;
    try {
      return await action();
    } finally {
      complete.complete();
      if (identical(_writers[path], complete.future)) _writers.remove(path);
    }
  }

  Future<void> _save(
    StoredEnrollment enrollment, {
    bool Function()? isCurrent,
  }) async {
    final temporary = File('${_file().path}.pending');
    await temporary.writeAsString(jsonEncode(enrollment.toJson()), flush: true);
    if (isCurrent?.call() == false) {
      await temporary.delete();
      throw StateError('Recovery was suspended before endpoint commit');
    }
    // No await between the lifecycle check and the atomic commit: suspension
    // in this isolate either precedes this rename or observes a committed update.
    temporary.renameSync(_file().path);
  }

  Future<void> save(StoredEnrollment enrollment) =>
      _write(() => _save(enrollment));

  /// Commit only the exact enrollment that the operator reviewed and probed.
  Future<void> replaceEndpoint(
    StoredEnrollment expected,
    StoredEnrollment next, {
    bool Function()? isCurrent,
  }) => _write(() async {
    if (isCurrent?.call() == false) throw StateError('Recovery was suspended');
    final current = await load();
    if (current == null ||
        jsonEncode(current.toJson()) != jsonEncode(expected.toJson())) {
      throw StateError('Enrollment changed during endpoint verification');
    }
    await _save(next, isCurrent: isCurrent);
  });

  Future<void> clear() => _write(() async {
    final file = _file();
    if (await file.exists()) await file.delete();
  });
}
