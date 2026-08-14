import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/ncfed/push_message_ingest.dart';

/// Spec 107/US2, contract §3. Records a pushed message straight from its
/// payload, so it is readable without a live channel.
///
/// Every value in these payloads is a String on purpose — the sender stringifies
/// the whole content map (`{k: str(v) for k, v in content.items()}`), so a client
/// that assumes types survived would fail in production and pass a naive test.

Directory _tmp() => Directory.systemTemp.createTempSync('ncfed_ingest_test');

/// Exactly the shape the sender emits: all values stringified.
Map<String, dynamic> _payload({
  String contentType = 'text',
  String content = 'spec 107 wake-signal test',
  String pushedAt = '2026-08-13T16:45:34.000Z',
  String designatedBy = 'agent',
}) =>
    {
      'content_type': contentType,
      'content': content,
      'pushed_at': pushedAt,
      'designated_by': designatedBy,
    };

void main() {
  test('a fully stringified payload reconstructs and stores (§3.1, FR-007)', () async {
    final store = MessageFeedStore(_tmp());
    final outcome = await ingestPushPayload(_payload(), store: store);

    expect(outcome, PushIngestOutcome.stored);
    expect(store.messages, hasLength(1));
    expect(store.messages.single.content, 'spec 107 wake-signal test');
    expect(store.messages.single.contentType, MessageContentType.text);
    expect(store.messages.single.pushedAt.toUtc().toIso8601String(),
        '2026-08-13T16:45:34.000Z');
  });

  test('survives a restart, so the message is readable with no connection (SC-004)', () async {
    final dir = _tmp();
    await ingestPushPayload(_payload(), store: MessageFeedStore(dir));

    final reopened = MessageFeedStore(dir);
    await reopened.load();
    expect(reopened.messages, hasLength(1));
  });

  test('the same message from push then replay yields ONE entry (SC-005)', () async {
    // The check that proves ingest and dedup work together. Without dedup this
    // is where every pushed message would double.
    final store = MessageFeedStore(_tmp());
    final data = _payload();

    expect(await ingestPushPayload(data, store: store), PushIngestOutcome.stored);
    // Now the Border replays the identical message over the live channel.
    final replayed = EdgeMessage.fromWire({...data, 'replayed': 'true'});
    expect(await store.append(replayed), isFalse, reason: 'declined as duplicate');

    expect(store.messages, hasLength(1));
  });

  test('a duplicate push reports duplicate and does not re-announce (§2.3)', () async {
    final store = MessageFeedStore(_tmp());
    final announced = <EdgeMessage>[];

    await ingestPushPayload(_payload(), store: store, onMessage: announced.add);
    final second =
        await ingestPushPayload(_payload(), store: store, onMessage: announced.add);

    expect(second, PushIngestOutcome.duplicate);
    expect(store.messages, hasLength(1));
    expect(announced, hasLength(1),
        reason: 'a second badge/notification for a message already seen is the '
            'same bug one layer up');
  });

  test("content_type 'approval' routes to approvals, never the feed (FR-009, §3.2)",
      () async {
    final store = MessageFeedStore(_tmp());
    final approvals = <Map<String, dynamic>>[];
    final feedAnnounced = <EdgeMessage>[];

    final outcome = await ingestPushPayload(
      _payload(contentType: 'approval'),
      store: store,
      onApproval: approvals.add,
      onMessage: feedAnnounced.add,
    );

    expect(outcome, PushIngestOutcome.approval);
    expect(approvals, hasLength(1));
    expect(store.messages, isEmpty, reason: 'approvals must never enter the feed');
    expect(feedAnnounced, isEmpty);
  });

  group('malformed payloads are rejected without corrupting the store (FR-010, §3.4)', () {
    test('missing pushed_at', () async {
      final store = MessageFeedStore(_tmp());
      final data = _payload()..remove('pushed_at');
      expect(await ingestPushPayload(data, store: store), PushIngestOutcome.rejected);
      expect(store.messages, isEmpty);
    });

    test('unparseable pushed_at is rejected, NOT defaulted to now (§3.3)', () async {
      // Defaulting would mint a fresh identity per delivery attempt and so
      // silently defeat dedup — the one failure mode that reintroduces duplicates.
      final store = MessageFeedStore(_tmp());
      expect(
        await ingestPushPayload(_payload(pushedAt: 'yesterday'), store: store),
        PushIngestOutcome.rejected,
      );
      expect(store.messages, isEmpty);
    });

    test('unknown content_type', () async {
      final store = MessageFeedStore(_tmp());
      expect(
        await ingestPushPayload(_payload(contentType: 'hologram'), store: store),
        PushIngestOutcome.rejected,
      );
      expect(store.messages, isEmpty);
    });

    test('missing content', () async {
      final store = MessageFeedStore(_tmp());
      final data = _payload()..remove('content');
      expect(await ingestPushPayload(data, store: store), PushIngestOutcome.rejected);
      expect(store.messages, isEmpty);
    });

    test('an empty payload', () async {
      final store = MessageFeedStore(_tmp());
      expect(await ingestPushPayload({}, store: store), PushIngestOutcome.rejected);
      expect(store.messages, isEmpty);
    });

    test('a rejection leaves already-stored messages intact', () async {
      final store = MessageFeedStore(_tmp());
      await ingestPushPayload(_payload(), store: store);
      await ingestPushPayload(_payload(pushedAt: 'garbage'), store: store);

      expect(store.messages, hasLength(1),
          reason: 'a bad payload must not truncate or corrupt the feed');
    });
  });

  test('missing designated_by falls back rather than rejecting', () async {
    // Not identity-bearing, so absence is tolerable — unlike pushed_at.
    final store = MessageFeedStore(_tmp());
    final data = _payload()..remove('designated_by');
    expect(await ingestPushPayload(data, store: store), PushIngestOutcome.stored);
    expect(store.messages.single.designatedBy, 'agent');
  });

  test('voice and image content types both ingest', () async {
    for (final type in ['voice', 'image']) {
      final store = MessageFeedStore(_tmp());
      final outcome = await ingestPushPayload(
        _payload(contentType: type, content: 'YmFzZTY0'),
        store: store,
      );
      expect(outcome, PushIngestOutcome.stored, reason: 'content_type $type');
    }
  });
}
