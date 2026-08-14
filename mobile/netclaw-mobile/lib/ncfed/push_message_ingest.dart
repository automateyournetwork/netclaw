import 'message_feed.dart';

/// What happened to one push payload.
enum PushIngestOutcome {
  /// New message, written to the feed.
  stored,

  /// Already had it. Expected, not an error (contract §2.4) — the live channel
  /// and this path both carry the same message by design.
  duplicate,

  /// An approval request, handed to the approvals path. Never enters the feed.
  approval,

  /// Unusable payload. Deliberately terminal-but-harmless: spec 106 guarantees
  /// the Border still replays the message over the live channel, so rejecting
  /// costs latency, never the message.
  rejected,
}

/// Records a message straight from its push payload, so it is readable without
/// waiting for — or even having — a live connection to the Border (spec 107,
/// User Story 2).
///
/// The sender already includes the full content as a push data payload beside
/// the banner (`send_fcm`: a `notification` block plus
/// `data: {k: str(v) for k, v in content.items()}`). Until spec 107 nothing on
/// the device consumed it: the only writer to [MessageFeedStore] was the live
/// channel handler, so a push while disconnected drew a banner and left the feed
/// empty. That was the production report of 2026-08-13.
///
/// This path is an **acceleration**, not a guarantee (research R5). Background
/// execution for a data-carrying push is at the operating system's discretion on
/// both platforms; building as though it were guaranteed would reintroduce
/// exactly the silent-loss class spec 106 removed. Spec 106's queue-and-replay
/// remains the guarantee.
///
/// Deduplication is what makes this safe to add at all. Without it, every
/// message recorded here would appear a second time when replay delivered it —
/// see [MessageFeedStore.append], which is the single enforcement point.
Future<PushIngestOutcome> ingestPushPayload(
  Map<String, dynamic> data, {
  required MessageFeedStore store,
  void Function(Map<String, dynamic> params)? onApproval,
  void Function(EdgeMessage message)? onMessage,
}) async {
  // Approvals are a live, time-sensitive list with no per-item history view, so
  // they route to the approvals path and never to the feed (FR-009,
  // contract §3.2) — the same discriminator the live channel handler uses.
  if (data['content_type'] == 'approval') {
    onApproval?.call(data);
    return PushIngestOutcome.approval;
  }

  // Strict parse: a malformed payload must not corrupt the feed (FR-010), and a
  // missing `pushed_at` must be rejected rather than defaulted — see
  // EdgeMessage.tryFromWire for why defaulting would silently defeat dedup.
  final message = EdgeMessage.tryFromWire(data);
  if (message == null) return PushIngestOutcome.rejected;

  try {
    final stored = await store.append(message);
    // Only announce a genuinely new message (contract §2.3).
    if (stored) onMessage?.call(message);
    return stored ? PushIngestOutcome.stored : PushIngestOutcome.duplicate;
  } catch (_) {
    // A write failure here is not worth crashing over, and must not leave the
    // caller believing the message was recorded. Replay covers it.
    return PushIngestOutcome.rejected;
  }
}
