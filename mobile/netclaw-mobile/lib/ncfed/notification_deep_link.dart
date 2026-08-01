import 'dart:convert';

import 'package:firebase_messaging/firebase_messaging.dart';

import 'conversation_store.dart';
import 'message_feed.dart';

/// Finds the pushed message a notification's `data` payload refers to, by
/// `pushed_at` — `push_notify.py`'s FCM/APNs `data` field always includes
/// every field of the pushed content, including `pushed_at`
/// (`{k: str(v) for k, v in content.items()}`), so this is always present
/// for a notification NCFED itself sent. Pulled out as a pure function so
/// the matching logic is testable without Firebase (T032).
EdgeMessage? findMessageForNotificationData(
  List<EdgeMessage> messages,
  Map<String, dynamic> data,
) {
  final pushedAt = data['pushed_at'];
  if (pushedAt == null) return null;
  for (final m in messages) {
    if (m.pushedAt.toIso8601String() == pushedAt) return m;
  }
  return null;
}

/// Parses a locally-posted notification's JSON payload string
/// (contracts/watch-relay-extensions.md §4) into its `type`/`identifier` --
/// returns `null` for anything missing or unparseable rather than throwing,
/// since a malformed payload must never crash the tap handler.
Map<String, String>? parseLocalNotificationPayload(String? payload) {
  if (payload == null) return null;
  try {
    final decoded = jsonDecode(payload) as Map<String, dynamic>;
    final type = decoded['type'] as String?;
    final identifier = decoded['identifier'] as String?;
    if (type == null || identifier == null) return null;
    return {'type': type, 'identifier': identifier};
  } catch (_) {
    return null;
  }
}

/// Finds the conversation turn a chat notification's identifier (a
/// `taskId`) refers to -- the chat counterpart to
/// [findMessageForNotificationData].
ConversationTurn? findTurnForIdentifier(List<ConversationTurn> turns, String taskId) {
  for (final t in turns) {
    if (t.taskId == taskId) return t;
  }
  return null;
}

/// Notification-tap deep-linking (T032, extended by 073/FR-006/research D4):
/// when the operator taps a delivered notification -- Firebase remote push
/// (feed-only, the original path) OR a locally-posted one (feed/chat, new)
/// -- opens the app directly to the corresponding item, not just its tab.
class NotificationDeepLink {
  final MessageFeedStore store;
  final void Function(EdgeMessage message) openMessage;
  final ConversationStore? conversationStore;
  final void Function(ConversationTurn turn)? openChatTurn;

  NotificationDeepLink({
    required this.store,
    required this.openMessage,
    this.conversationStore,
    this.openChatTurn,
  });

  Future<void> wire() async {
    FirebaseMessaging.onMessageOpenedApp.listen(_handleRemote);
    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) await _handleRemote(initial);
  }

  Future<void> _handleRemote(RemoteMessage message) async {
    await store.load();
    final match = findMessageForNotificationData(store.messages, message.data);
    if (match != null) openMessage(match);
  }

  /// Handles a tap on a locally-posted notification -- the counterpart to
  /// [wire]'s Firebase remote-tap handling, fed by
  /// `flutter_local_notifications`' `onDidReceiveNotificationResponse`
  /// instead. An `approval` payload has nothing further to deep-link to:
  /// tapping the banner already opens the app, and approvals render as a
  /// live list with no per-item "open" concept (FR-006 covers Feed/Chat
  /// only).
  Future<void> handleLocalNotificationTap(String? payload) async {
    final parsed = parseLocalNotificationPayload(payload);
    if (parsed == null) return;
    switch (parsed['type']) {
      case 'feed':
        await store.load();
        final match =
            findMessageForNotificationData(store.messages, {'pushed_at': parsed['identifier']});
        if (match != null) openMessage(match);
      case 'chat':
        final convoStore = conversationStore;
        if (convoStore == null) return;
        await convoStore.load();
        final turn = findTurnForIdentifier(convoStore.turns, parsed['identifier']!);
        if (turn != null) openChatTurn?.call(turn);
    }
  }
}
