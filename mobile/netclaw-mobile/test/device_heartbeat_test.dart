import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/device_heartbeat.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';

EdgeMessage _message(String content) => EdgeMessage(
      contentType: MessageContentType.text,
      content: content,
      designatedBy: 'agent',
      pushedAt: DateTime.utc(2026, 8, 10, 16, 33),
    );

void main() {
  group('looksLikeDeviceHeartbeat', () {
    test('a heartbeat push (starts with "NetClaw ") is recognized', () {
      expect(
        looksLikeDeviceHeartbeat(_message('NetClaw risk/foo — 16:33 EDT\nAll peers healthy.')),
        isTrue,
      );
    });

    test('an ordinary agent-authored message is not mistaken for a heartbeat', () {
      expect(
        looksLikeDeviceHeartbeat(_message('Toronto branch WAN outage detected.')),
        isFalse,
      );
    });

    test('a non-text push is never a heartbeat, even with matching text content', () {
      final voice = EdgeMessage(
        contentType: MessageContentType.voice,
        content: 'NetClaw risk/foo — 16:33 EDT',
        designatedBy: 'agent',
        pushedAt: DateTime.utc(2026, 8, 10, 16, 33),
      );
      expect(looksLikeDeviceHeartbeat(voice), isFalse);
    });
  });

  group('heartbeatSummary / heartbeatIsAlarm (FR-010)', () {
    test('a routine heartbeat with no alarm line summarizes as all-clear', () {
      const content = 'NetClaw risk/foo — 16:33 EDT\nAll peers healthy.\n2 agents up.';
      expect(heartbeatIsAlarm(content), isFalse);
      expect(heartbeatSummary(content), 'All systems normal');
    });

    test('an alarm-bearing heartbeat surfaces the alarm line verbatim', () {
      const content = 'NetClaw risk/foo — 16:33 EDT\n'
          '⚠ SLACK HEARTBEAT FAILING — 3 delivery failure(s), run `openclaw channels status`\n'
          'All peers healthy.';
      expect(heartbeatIsAlarm(content), isTrue);
      expect(
        heartbeatSummary(content),
        '⚠ SLACK HEARTBEAT FAILING — 3 delivery failure(s), run `openclaw channels status`',
      );
    });
  });

  group('DeviceHeartbeatStatus.fromMessage', () {
    test('captures summary, timestamp, and alarm flag from the raw push', () {
      final message = _message(
        'NetClaw risk/foo — 16:33 EDT\n⚠ SLACK HEARTBEAT FAILING — 1 delivery failure(s)',
      );
      final status = DeviceHeartbeatStatus.fromMessage(message);
      expect(status.isAlarm, isTrue);
      expect(status.pushedAt, message.pushedAt);
      expect(status.summary, contains('SLACK HEARTBEAT FAILING'));
    });
  });

  group('DeviceHeartbeatStore', () {
    test('a heartbeat saved survives a simulated app restart', () async {
      final dir = await Directory.systemTemp.createTemp('ncfed_heartbeat_test_');
      addTearDown(() => dir.delete(recursive: true));

      final status = DeviceHeartbeatStatus(
        summary: 'All systems normal',
        pushedAt: DateTime.utc(2026, 8, 10, 16, 33),
        isAlarm: false,
      );
      await DeviceHeartbeatStore(dir).save(status);

      final reloaded = await DeviceHeartbeatStore(dir).load();
      expect(reloaded, isNotNull);
      expect(reloaded!.summary, status.summary);
      expect(reloaded.pushedAt, status.pushedAt);
      expect(reloaded.isAlarm, status.isAlarm);
    });

    test('a later save overwrites the earlier one -- only the latest heartbeat matters', () async {
      final dir = await Directory.systemTemp.createTemp('ncfed_heartbeat_test_');
      addTearDown(() => dir.delete(recursive: true));

      final store = DeviceHeartbeatStore(dir);
      await store.save(DeviceHeartbeatStatus(
        summary: 'All systems normal',
        pushedAt: DateTime.utc(2026, 8, 10, 16, 3),
        isAlarm: false,
      ));
      await store.save(DeviceHeartbeatStatus(
        summary: '⚠ SLACK HEARTBEAT FAILING — 1 delivery failure(s)',
        pushedAt: DateTime.utc(2026, 8, 10, 16, 33),
        isAlarm: true,
      ));

      final reloaded = await store.load();
      expect(reloaded!.isAlarm, isTrue);
      expect(reloaded.pushedAt, DateTime.utc(2026, 8, 10, 16, 33));
    });

    test('a store never written to loads as null, not an error', () async {
      final dir = await Directory.systemTemp.createTemp('ncfed_heartbeat_test_');
      addTearDown(() => dir.delete(recursive: true));

      expect(await DeviceHeartbeatStore(dir).load(), isNull);
    });
  });
}
