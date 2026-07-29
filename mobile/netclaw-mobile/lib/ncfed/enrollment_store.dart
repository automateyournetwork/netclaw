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

  const StoredEnrollment({
    required this.memberId,
    required this.keyFingerprint,
    required this.borderHost,
    required this.borderPort,
    required this.clawDomain,
  });

  EnrollmentQrPayload toPayload({String enrollmentToken = ''}) => EnrollmentQrPayload(
        borderHost: borderHost,
        borderPort: borderPort,
        clawDomain: clawDomain,
        enrollmentToken: enrollmentToken,
      );

  Map<String, dynamic> toJson() => {
        'member_id': memberId,
        'key_fingerprint': keyFingerprint,
        'border_host': borderHost,
        'border_port': borderPort,
        'claw_domain': clawDomain,
      };

  factory StoredEnrollment.fromJson(Map<String, dynamic> json) => StoredEnrollment(
        memberId: json['member_id'] as String,
        keyFingerprint: json['key_fingerprint'] as String,
        borderHost: json['border_host'] as String,
        borderPort: json['border_port'] as int,
        clawDomain: json['claw_domain'] as String,
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

  Future<void> save(StoredEnrollment enrollment) async {
    await _file().writeAsString(jsonEncode(enrollment.toJson()), flush: true);
  }

  Future<void> clear() async {
    final file = _file();
    if (await file.exists()) await file.delete();
  }
}
