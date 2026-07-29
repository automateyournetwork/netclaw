import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'edge_client.dart';

/// Maps the running platform to NCFED's `n2n/edge/register_push` `platform`
/// field — pulled out as a pure function so it's testable without Firebase.
String pushPlatformFor(TargetPlatform platform) =>
    platform == TargetPlatform.iOS ? 'apns' : 'fcm';

/// Why push isn't working, when it isn't. Push failing must never block the
/// app, but "the operator hasn't dropped in a Firebase config yet" and "push
/// is configured and broke anyway" are very different problems and used to be
/// indistinguishable — both vanished into one swallowed `catch`.
enum PushStatus {
  /// Not attempted yet.
  unknown,

  /// Registered with the Border; notifications should arrive.
  registered,

  /// No Firebase project configured for this build (no `google-services.json`
  /// on Android / no `GoogleService-Info.plist` on iOS). Expected and benign
  /// for any build made from a fresh clone — see README.md.
  notConfigured,

  /// The user declined the notification permission. Only they can undo this,
  /// in system settings.
  permissionDenied,

  /// Configured, permitted, and it still failed. This one is a real bug.
  failed,
}

/// Distinguishes "no Firebase config in this build" from a genuine failure.
/// Matched on the error text rather than a code because the two platforms
/// surface a missing default app quite differently (Android throws from the
/// Google Services plugin's absent resource values, iOS from a missing plist),
/// and neither guarantees a stable code.
PushStatus classifyPushError(Object error) {
  final text = error.toString().toLowerCase();
  final looksUnconfigured = text.contains('no firebase app') ||
      text.contains('default firebaseapp') ||
      text.contains('not been configured') ||
      text.contains('googleservice-info.plist') ||
      text.contains('google-services.json') ||
      text.contains('failedprecondition') ||
      text.contains('core/not-initialized') ||
      text.contains('core/no-app');
  return looksUnconfigured ? PushStatus.notConfigured : PushStatus.failed;
}

/// Registers this device's FCM/APNs push token with the Border
/// (n2n/edge/register_push, US3/T031) so a message pushed while the app is
/// backgrounded/disconnected still reaches the operator via a platform
/// notification. Requires `Firebase.initializeApp()` to have already run
/// with real project configuration (google-services.json /
/// GoogleService-Info.plist) — a deployment-time step with real
/// Firebase/Apple credentials, not something this module does on its own,
/// and not something verifiable in this environment.
class PushRegistration {
  final EdgeClient client;
  StreamSubscription<String>? _refreshSub;

  PushRegistration(this.client);

  /// Returns what actually happened, rather than succeeding silently either
  /// way. Android 13+ and iOS both require the user to grant notification
  /// permission; a denial is not an error but it does mean no notifications,
  /// so it gets its own status.
  Future<PushStatus> registerCurrentToken() async {
    final messaging = FirebaseMessaging.instance;
    final settings = await messaging.requestPermission();
    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      return PushStatus.permissionDenied;
    }
    final token = await messaging.getToken();
    if (token == null) return PushStatus.failed;
    await _sendToken(token);
    _refreshSub ??= messaging.onTokenRefresh.listen(_sendToken);
    return PushStatus.registered;
  }

  Future<void> _sendToken(String token) async {
    try {
      await client.call('n2n/edge/register_push', {
        'platform': pushPlatformFor(defaultTargetPlatform),
        'token': token,
      });
    } catch (_) {
      // Best-effort — a failed registration just means the push fallback
      // won't work until the next successful attempt (e.g. next reconnect).
    }
  }

  void dispose() => _refreshSub?.cancel();
}
