import 'dart:convert';
import 'dart:io';

import 'edge_client.dart';

enum MessageContentType { text, voice, image }

/// A message's identity, as an instant (spec 107, research R2, data-model.md).
///
/// Instant-based rather than raw `DateTime` equality on purpose: Dart's
/// `DateTime.==` also requires both operands to agree on `isUtc`, so the same
/// moment expressed as UTC and as local time compares unequal. Every path here
/// happens to produce UTC today, but a dedup key that silently depends on that
/// is a trap — two delivery paths disagreeing about zone would each store their
/// own copy, which is precisely the bug dedup exists to prevent.
///
/// **Known limit, stated rather than hidden**: the Border stamps `pushed_at` at
/// whole-second granularity (`%Y-%m-%dT%H:%M:%SZ`), so two genuinely distinct
/// messages sent inside the same second collapse into one. Accepted because this
/// path carries operator- and agent-initiated pushes, not a high-rate stream. If
/// that stops being true the fix is a sender-assigned unique id — a Border
/// change, and therefore a different spec. Do not work around it by adding a
/// second, client-local identifier: that would break dedup *across* delivery
/// paths, which is the entire point.
int messageIdentity(DateTime pushedAt) => pushedAt.toUtc().microsecondsSinceEpoch;

/// One message the Border explicitly pushed (US2/FR-008,
/// contracts/edge-enrollment-and-push.md §3). `content` is plain text for
/// `text`, base64-encoded media for `voice`/`image`.
class EdgeMessage {
  final MessageContentType contentType;
  final String content;
  final String designatedBy;
  final DateTime pushedAt;
  // Mutable, mirroring ConversationTurn's state/answerText pattern -- a
  // message's acknowledged flag changes in place after creation (073/FR-012).
  bool acknowledged;

  EdgeMessage({
    required this.contentType,
    required this.content,
    required this.designatedBy,
    required this.pushedAt,
    this.acknowledged = false,
  });

  factory EdgeMessage.fromWire(Map<String, dynamic> params) => EdgeMessage(
        contentType: MessageContentType.values.byName(params['content_type'] as String),
        content: params['content'] as String,
        designatedBy: params['designated_by'] as String? ?? 'agent',
        pushedAt: DateTime.tryParse(params['pushed_at'] as String? ?? '') ?? DateTime.now().toUtc(),
      );

  /// Strict counterpart to [fromWire], for the **untrusted** push-payload path
  /// (spec 107, contract §3.3). Returns null instead of throwing or defaulting.
  ///
  /// Two differences from [fromWire], both load-bearing:
  ///
  /// 1. **A missing or unparseable `pushed_at` is rejected, not defaulted.**
  ///    [fromWire] falls back to `DateTime.now()`, which is fine for the
  ///    authenticated live channel (the Border always sets the field) but fatal
  ///    here: a fresh `now()` on every delivery attempt mints a *new identity*
  ///    each time, so the same message arriving twice would dedup against
  ///    nothing and appear twice. Rejecting is safe — spec 106 guarantees replay
  ///    will deliver it again over the live path.
  /// 2. **Every value may have arrived as a String** (contract §3.1). The sender
  ///    stringifies the whole content map (`{k: str(v) for k, v in ...}`), so no
  ///    field can be assumed to have survived with its original type.
  static EdgeMessage? tryFromWire(Map<String, dynamic> params) {
    final rawPushedAt = params['pushed_at'];
    if (rawPushedAt is! String) return null;
    final pushedAt = DateTime.tryParse(rawPushedAt);
    if (pushedAt == null) return null;

    final rawType = params['content_type'];
    if (rawType is! String) return null;
    final contentType = MessageContentType.values
        .where((t) => t.name == rawType)
        .firstOrNull;
    if (contentType == null) return null;

    final rawContent = params['content'];
    if (rawContent is! String) return null;

    final rawDesignatedBy = params['designated_by'];
    return EdgeMessage(
      contentType: contentType,
      content: rawContent,
      designatedBy: rawDesignatedBy is String && rawDesignatedBy.isNotEmpty
          ? rawDesignatedBy
          : 'agent',
      pushedAt: pushedAt,
    );
  }

  Map<String, dynamic> toJson() => {
        'content_type': contentType.name,
        'content': content,
        'designated_by': designatedBy,
        'pushed_at': pushedAt.toIso8601String(),
        'acknowledged': acknowledged,
      };

  /// A message written before 073 has no `acknowledged` key at all -- a
  /// missing key MUST default to `true` (already-acknowledged), never
  /// `false`, or every message ever received before this feature shipped
  /// would suddenly appear unread the moment an operator upgrades
  /// (research D5). Only a message explicitly serialized as `false` since
  /// this feature shipped is actually unread.
  factory EdgeMessage.fromJson(Map<String, dynamic> json) => EdgeMessage(
        contentType: MessageContentType.values.byName(json['content_type'] as String),
        content: json['content'] as String,
        designatedBy: json['designated_by'] as String,
        pushedAt: DateTime.parse(json['pushed_at'] as String),
        acknowledged: json['acknowledged'] as bool? ?? true,
      );
}

/// Local, on-device store for messages the Border has explicitly pushed —
/// append-only, persisted as JSON Lines so a restart never loses history
/// (T029). Production callers construct this with
/// `await getApplicationDocumentsDirectory()`; tests pass a temp directory
/// directly, so this never touches `path_provider`'s platform channel
/// itself (which has no implementation under `flutter test`).
class MessageFeedStore {
  final Directory directory;
  final List<EdgeMessage> _messages = [];
  bool _loaded = false;

  MessageFeedStore(this.directory);

  List<EdgeMessage> get messages => List.unmodifiable(_messages);

  /// Count of messages not yet acknowledged -- feeds the combined app badge
  /// (073/FR-008).
  int get unreadCount => _messages.where((m) => !m.acknowledged).length;

  File _file() => File('${directory.path}/ncfed_message_feed.jsonl');

  Future<void> load() async {
    if (_loaded) return;
    _loaded = true;
    final file = _file();
    if (!await file.exists()) return;
    final lines = await file.readAsLines();
    _messages.clear();
    for (final line in lines) {
      if (line.trim().isEmpty) continue;
      _messages.add(EdgeMessage.fromJson(jsonDecode(line) as Map<String, dynamic>));
    }
  }

  /// True if a message with this identity is already stored.
  bool contains(DateTime pushedAt) {
    final wanted = messageIdentity(pushedAt);
    return _messages.any((m) => messageIdentity(m.pushedAt) == wanted);
  }

  /// Appends [message] unless one with the same identity is already stored.
  ///
  /// Returns **true if stored, false if declined** as a duplicate. Declining is
  /// the expected outcome whenever two delivery paths carry the same message,
  /// not an error (contract §2.4).
  ///
  /// This is the single enforcement point for message identity (spec 107,
  /// research R3, contract §2.1) — callers must NOT pre-check. As of spec 107
  /// there are two writers (the live channel handler and the push-payload ingest
  /// path); putting the check here means a future third writer inherits it
  /// without having to know it exists. Two implementations that must agree
  /// forever is the drift pattern this repo already guards against elsewhere.
  ///
  /// A declined duplicate leaves the stored message completely untouched,
  /// including its `acknowledged` state (FR-006, contract §2.2) — re-delivery
  /// must never make a message the operator already read look unread again.
  ///
  /// The return value matters beyond bookkeeping: without it a caller would fire
  /// its "arrived" side effect (unread badge, local notification) for every
  /// replayed duplicate, so fixing double *entries* would leave double
  /// *notifications* — a visibly identical bug one layer up (contract §2.3).
  Future<bool> append(EdgeMessage message) async {
    await load();
    if (contains(message.pushedAt)) return false;
    _messages.add(message);
    await _file().writeAsString(
      '${jsonEncode(message.toJson())}\n',
      mode: FileMode.append,
      flush: true,
    );
    return true;
  }

  /// Rewrites the whole file from the in-memory list -- unlike [append],
  /// used by [acknowledge]/[delete], which mutate or remove an existing
  /// line rather than add a new one.
  Future<void> _rewrite() async {
    final buffer = _messages.map((m) => jsonEncode(m.toJson())).join('\n');
    await _file().writeAsString(buffer.isEmpty ? '' : '$buffer\n');
  }

  /// Marks the message with this [pushedAt] identity as acknowledged --
  /// clears its unread state but leaves it visible in [messages] (073/FR-012).
  Future<void> acknowledge(DateTime pushedAt) async {
    await load();
    for (final m in _messages) {
      if (m.pushedAt == pushedAt) {
        m.acknowledged = true;
        break;
      }
    }
    await _rewrite();
  }

  /// Permanently removes the message with this [pushedAt] identity
  /// (073/FR-013) -- unlike [clear], which removes everything.
  Future<void> delete(DateTime pushedAt) async {
    await load();
    _messages.removeWhere((m) => m.pushedAt == pushedAt);
    await _rewrite();
  }

  /// Deletes every Border-pushed message held on this device. On-device only —
  /// the Border's own audit trail is untouched, and a message cleared here
  /// cannot be re-fetched (the Border never re-pushes spontaneously), so this
  /// is destructive from the phone's point of view and should be confirmed.
  Future<void> clear() async {
    await load();
    _messages.clear();
    final file = _file();
    if (await file.exists()) await file.delete();
  }
}

/// Registers the SINGLE `n2n/edge/message` handler for the whole app —
/// `EdgeClient.on()` only ever keeps the LAST handler registered per
/// method, so this must be the only place that calls `client.on('n2n/edge/
/// message', ...)`. Every Border-initiated push with `content_type`
/// text/voice/image is appended to `store` (066, contracts/
/// edge-enrollment-and-push.md §3); a push with `content_type='approval'`
/// (068, research D5) is instead handed to `onApproval` — never both.
/// [onMessage] fires after a non-approval push has been persisted, so the UI
/// can surface that something arrived (unread badge, repaint). Without it a
/// push lands silently in the feed and the operator has no way to know —
/// observed with a real tester, where a successfully delivered push went
/// completely unnoticed because they were sitting on the Chat tab.
void wireMessageFeed(
  EdgeMethodSource client,
  MessageFeedStore store, {
  void Function(Map<String, dynamic> params)? onApproval,
  void Function(EdgeMessage message)? onMessage,
}) {
  client.on('n2n/edge/message', (params) async {
    if (params['content_type'] == 'approval') {
      onApproval?.call(params);
      return {'received': true};
    }
    final message = EdgeMessage.fromWire(params);
    // Spec 107: only announce it if it was actually new. A replayed message the
    // push-ingest path already stored is declined here, and firing [onMessage]
    // anyway would raise an unread badge and post a local notification for
    // something the operator has already seen (contract §2.3).
    final stored = await store.append(message);
    if (stored) onMessage?.call(message);
    return {'received': true};
  });
}
