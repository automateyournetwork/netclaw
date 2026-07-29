import 'package:firebase_messaging/firebase_messaging.dart';

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

/// Notification-tap deep-linking (T032): when the operator taps a delivered
/// push notification (or cold-starts the app from one), opens the app
/// directly to the corresponding pushed message.
class NotificationDeepLink {
  final MessageFeedStore store;
  final void Function(EdgeMessage message) openMessage;

  NotificationDeepLink({required this.store, required this.openMessage});

  Future<void> wire() async {
    FirebaseMessaging.onMessageOpenedApp.listen(_handle);
    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) await _handle(initial);
  }

  Future<void> _handle(RemoteMessage message) async {
    await store.load();
    final match = findMessageForNotificationData(store.messages, message.data);
    if (match != null) openMessage(match);
  }
}
