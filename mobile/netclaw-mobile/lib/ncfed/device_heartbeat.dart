import 'dart:convert';
import 'dart:io';

import 'message_feed.dart';

/// The Border-composed device status heartbeat (spec 103 US5/FR-008-FR-010)
/// rides the SAME `n2n/edge/message` push as any other text message —
/// confirmed against `scripts/edge-heartbeat.py`'s `compose()`/`_post` call,
/// there is no dedicated `content_type` or structured field. The only
/// distinguishing markers are textual: every heartbeat's content begins with
/// `"NetClaw "` (`compose()`'s first line is always
/// `f"NetClaw {identity} — {HH:MM %Z}"`), and an active Slack-delivery-failure
/// alarm (FR-010) appears as a line containing `"⚠ SLACK HEARTBEAT FAILING"`.
bool looksLikeDeviceHeartbeat(EdgeMessage message) =>
    message.contentType == MessageContentType.text && message.content.startsWith('NetClaw ');

/// The single line worth showing on a watch-sized screen (US4/FR-015): the
/// alarm line verbatim if one is present, otherwise a fixed all-clear summary
/// — the full multi-line posture/daemon/peer report is useful on the phone's
/// Feed tab but not on a wrist.
String heartbeatSummary(String content) {
  final alarmLine = content
      .split('\n')
      .firstWhere((line) => line.contains('⚠ SLACK HEARTBEAT FAILING'), orElse: () => '');
  return alarmLine.isNotEmpty ? alarmLine.trim() : 'All systems normal';
}

bool heartbeatIsAlarm(String content) => content.contains('⚠ SLACK HEARTBEAT FAILING');

/// The latest device heartbeat's status. Persisted (not just held in memory)
/// so a heartbeat received during a headless `BGAppRefreshTask` window
/// (US3) is still there the next time the watch — or a fresh foreground
/// launch — asks, and so "the phone is unreachable" (US4 acceptance scenario
/// 3) can still show a real last-known value instead of nothing.
class DeviceHeartbeatStatus {
  final String summary;
  final DateTime pushedAt;
  final bool isAlarm;

  const DeviceHeartbeatStatus({
    required this.summary,
    required this.pushedAt,
    required this.isAlarm,
  });

  factory DeviceHeartbeatStatus.fromMessage(EdgeMessage message) => DeviceHeartbeatStatus(
        summary: heartbeatSummary(message.content),
        pushedAt: message.pushedAt,
        isAlarm: heartbeatIsAlarm(message.content),
      );

  Map<String, dynamic> toJson() => {
        'summary': summary,
        'pushed_at': pushedAt.toIso8601String(),
        'is_alarm': isAlarm,
      };

  factory DeviceHeartbeatStatus.fromJson(Map<String, dynamic> json) => DeviceHeartbeatStatus(
        summary: json['summary'] as String,
        pushedAt: DateTime.parse(json['pushed_at'] as String),
        isAlarm: json['is_alarm'] as bool,
      );
}

/// Same single-file JSON pattern as `EnrollmentStore` — production callers
/// construct this with `await getApplicationDocumentsDirectory()`; tests pass
/// a temp directory directly.
class DeviceHeartbeatStore {
  final Directory directory;
  DeviceHeartbeatStore(this.directory);

  File _file() => File('${directory.path}/ncfed_latest_heartbeat.json');

  Future<DeviceHeartbeatStatus?> load() async {
    final file = _file();
    if (!await file.exists()) return null;
    final text = await file.readAsString();
    if (text.trim().isEmpty) return null;
    return DeviceHeartbeatStatus.fromJson(jsonDecode(text) as Map<String, dynamic>);
  }

  Future<void> save(DeviceHeartbeatStatus status) async {
    await _file().writeAsString(jsonEncode(status.toJson()), flush: true);
  }
}
