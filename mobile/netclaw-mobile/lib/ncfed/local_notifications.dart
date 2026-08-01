import 'dart:convert';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// The one notification category approvals use, carrying the two
/// authenticated actions (073/FR-003/FR-004, research D2). iOS/macOS gate
/// each action behind `authenticationRequired`; Android has no OS-level
/// equivalent, so the same guarantee is enforced entirely in Dart -- the
/// action handler always routes through the existing biometric-confirmation-
/// then-resolve() path regardless of platform, never a direct resolve() call.
const approvalCategoryId = 'approval';
const approveActionId = 'approve';
const denyActionId = 'deny';

/// Reserved notification id used ONLY to carry a silent badge-count update.
/// `flutter_local_notifications` has no standalone "just set the badge"
/// API -- the badge is a property of an actual (possibly invisible)
/// notification. Reusing this one fixed id means repeated badge-only
/// updates replace the same entry rather than stacking up new ones.
const _badgeOnlyNotificationId = -1;

/// Combined badge count: unacknowledged Feed messages + unacknowledged chat
/// answers. Approvals are explicitly excluded (spec Assumptions) -- they
/// already render as a live, always-visible pending list.
int combinedBadgeCount({required int unreadFeed, required int unreadChat}) =>
    unreadFeed + unreadChat;

/// One-line preview a Feed/Chat notification's payload identifies its
/// target by (research D4, contracts/watch-relay-extensions.md §4).
String notificationPayload({required String type, required String identifier}) =>
    jsonEncode({'type': type, 'identifier': identifier});

/// Tracks which notification identifiers have already been posted this
/// session, so a reconnect-triggered replay of an already-notified Feed
/// message/chat answer/approval never posts a second notification for the
/// same item (FR-007). Deliberately a pure, plugin-free class so it's
/// testable without a platform channel -- `LocalNotifications` consults it
/// before ever calling the real plugin.
class NotificationDedup {
  final Set<String> _posted = {};

  /// Returns `true` (and remembers `identifier`) the first time it's seen;
  /// `false` every time after.
  bool shouldPost(String identifier) => _posted.add(identifier);
}

/// Wraps `flutter_local_notifications` for real local push notifications
/// while the app process is alive (073, distinct from feature 066's
/// credential-blocked remote FCM/APNs path). The watch inherits every
/// notification and badge update posted here via standard watchOS mirroring
/// -- there is no watch-side counterpart to this file (FR-010).
class LocalNotifications {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  final NotificationDedup _dedup;

  LocalNotifications({NotificationDedup? dedup}) : _dedup = dedup ?? NotificationDedup();

  Future<void> initialize({
    required void Function(NotificationResponse response) onResponse,
  }) async {
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    // Permission is requested explicitly via [requestPermission] below,
    // mirroring `push_registration.dart`'s explicit
    // `messaging.requestPermission()` style -- not implicitly during
    // initialize(), so the caller gets a clear granted/denied result to act
    // on (FR-020) rather than a fire-and-forget prompt.
    final darwinInit = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
      notificationCategories: [
        DarwinNotificationCategory(
          approvalCategoryId,
          actions: [
            DarwinNotificationAction.plain(
              approveActionId,
              'Approve',
              options: const {
                DarwinNotificationActionOption.authenticationRequired,
                DarwinNotificationActionOption.foreground,
              },
            ),
            DarwinNotificationAction.plain(
              denyActionId,
              'Deny',
              options: const {
                DarwinNotificationActionOption.authenticationRequired,
                DarwinNotificationActionOption.destructive,
                DarwinNotificationActionOption.foreground,
              },
            ),
          ],
        ),
      ],
    );
    await _plugin.initialize(
      settings: InitializationSettings(android: androidInit, iOS: darwinInit, macOS: darwinInit),
      onDidReceiveNotificationResponse: onResponse,
    );
  }

  /// Explicitly requests notification permission, returning whether it was
  /// granted (FR-020) -- mirrors `push_registration.dart`'s
  /// `requestPermission()` style. A denial is not an error; every other
  /// capability in the app must keep working regardless (FR-020), this just
  /// lets the caller make that limitation discoverable.
  Future<bool> requestPermission() async {
    final ios = _plugin
        .resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>();
    if (ios != null) {
      return await ios.requestPermissions(alert: true, badge: true, sound: true) ?? false;
    }
    final android = _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    if (android != null) {
      return await android.requestNotificationsPermission() ?? true;
    }
    return true; // no platform-specific permission model -- nothing to deny
  }

  /// Posts a Feed notification with a one-line content preview (FR-001).
  /// `identifier` is the message's `pushedAt` ISO string. `badgeCount` is
  /// carried on this SAME visible notification (not just the separate
  /// silent [setBadgeCount] update) -- confirmed on real hardware that an
  /// intentionally-invisible (`presentAlert: false`) notification never
  /// reaches the watch's mirroring pipeline at all, so a badge set only via
  /// [setBadgeCount] updates the phone's own icon but never the watch's
  /// (FR-009). Piggybacking the badge on a real, visible notification is
  /// what actually works end to end.
  Future<void> postFeedNotification({
    required String identifier,
    required String preview,
    required int badgeCount,
  }) {
    final payload = notificationPayload(type: 'feed', identifier: identifier);
    if (!_dedup.shouldPost(payload)) return Future.value();
    return _show(
        id: identifier.hashCode,
        title: 'New message',
        body: preview,
        payload: payload,
        badgeCount: badgeCount);
  }

  /// Posts a chat-answer notification (FR-002). `identifier` is the turn's
  /// `taskId`. See [postFeedNotification] for why `badgeCount` rides on this
  /// same visible notification rather than only the silent path.
  Future<void> postChatNotification({
    required String identifier,
    required String preview,
    required int badgeCount,
  }) {
    final payload = notificationPayload(type: 'chat', identifier: identifier);
    if (!_dedup.shouldPost(payload)) return Future.value();
    return _show(
        id: identifier.hashCode,
        title: 'Answer ready',
        body: preview,
        payload: payload,
        badgeCount: badgeCount);
  }

  /// Posts an approval notification with inline, authenticated Approve/Deny
  /// actions (FR-003/FR-004). `identifier` is the `approval_id`. Never
  /// includes a badge number -- approvals are excluded from badge tracking.
  Future<void> postApprovalNotification({
    required String identifier,
    required String targetName,
    required String requestingAgent,
  }) {
    final payload = notificationPayload(type: 'approval', identifier: identifier);
    if (!_dedup.shouldPost(payload)) return Future.value();
    return _plugin.show(
      id: identifier.hashCode,
      title: 'Approval needed',
      body: '$targetName — requested by $requestingAgent',
      notificationDetails: NotificationDetails(
        iOS: const DarwinNotificationDetails(
          categoryIdentifier: approvalCategoryId,
          presentBadge: false,
        ),
        macOS: const DarwinNotificationDetails(
          categoryIdentifier: approvalCategoryId,
          presentBadge: false,
        ),
        android: const AndroidNotificationDetails(
          'approvals',
          'Approvals',
          actions: [
            AndroidNotificationAction(approveActionId, 'Approve'),
            AndroidNotificationAction(denyActionId, 'Deny'),
          ],
        ),
      ),
      payload: payload,
    );
  }

  Future<void> _show({
    required int id,
    required String title,
    required String body,
    required String payload,
    required int badgeCount,
  }) {
    return _plugin.show(
      id: id,
      title: title,
      body: body,
      notificationDetails: NotificationDetails(
        iOS: DarwinNotificationDetails(badgeNumber: badgeCount),
        macOS: DarwinNotificationDetails(badgeNumber: badgeCount),
        android: const AndroidNotificationDetails('messages', 'Messages'),
      ),
      payload: payload,
    );
  }

  /// Sets the combined app-icon badge to an explicit count (FR-008),
  /// computed by the caller from `MessageFeedStore.unreadCount` +
  /// `ConversationStore.unreadCount` (research D3). Never posts a visible
  /// alert of its own -- confirmed on real hardware that this keeps the
  /// PHONE's own icon correct (e.g. after an acknowledge/delete with no new
  /// arrival) but does NOT reach the watch (FR-009's mirroring only follows
  /// a genuinely visible notification, per [postFeedNotification]'s note).
  Future<void> setBadgeCount(int count) {
    return _plugin.show(
      id: _badgeOnlyNotificationId,
      notificationDetails: NotificationDetails(
        iOS: DarwinNotificationDetails(
          presentAlert: false,
          presentBanner: false,
          presentSound: false,
          presentBadge: true,
          badgeNumber: count,
        ),
        macOS: DarwinNotificationDetails(
          presentAlert: false,
          presentBanner: false,
          presentSound: false,
          presentBadge: true,
          badgeNumber: count,
        ),
      ),
    );
  }
}
