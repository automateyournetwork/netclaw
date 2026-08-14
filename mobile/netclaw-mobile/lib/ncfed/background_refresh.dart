import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:path_provider/path_provider.dart';

import 'device_heartbeat.dart';
import 'edge_client.dart';
import 'edge_identity.dart';
import 'enrollment_store.dart';
import 'local_notifications.dart';
import 'message_feed.dart';
import 'pending_approval_store.dart';

const _channel = MethodChannel('ca.automateyournetwork.netclaw/background_refresh');

/// Entry point for the headless `FlutterEngine` `AppDelegate.swift` spins up
/// when iOS grants a `BGAppRefreshTask` window (103/US3, FR-013). Runs with
/// NO widget tree — reconnects using the same persisted enrollment/identity a
/// cold foreground launch would (`EnrollmentStore`/`EdgeIdentity`, same as
/// `main.dart`'s `EnrollmentGate._init`), lets the Border's queue replay land,
/// and reports back over [_channel] so native can call `task.setTaskCompleted`
/// before the OS's budget expires.
///
/// Per the Border's own design note (BORDER-STATUS.md, replying to
/// MAC-STATUS.md): this does NOT assume a push woke it — it reconnects and
/// drains unconditionally on every grant, since APNs is best-effort and
/// silently drops notifications for a long-offline device. The queue is the
/// durable floor; push is a latency improvement on top of it, not a
/// precondition for this to run.
@pragma('vm:entry-point')
Future<void> backgroundRefreshMain() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    final dir = await getApplicationDocumentsDirectory();
    final stored = await EnrollmentStore(dir).load();
    if (stored == null) {
      await _finish(notified: false);
      return;
    }

    try {
      await Firebase.initializeApp();
    } catch (_) {
      // Same "no Firebase project in this build" case main.dart already
      // tolerates (push_registration.dart's classifyPushError) — this window
      // doesn't touch push registration itself, so a failure here is inert.
    }

    final client = await EdgeClient.reconnect(
      stored.toPayload(),
      memberId: stored.memberId,
      keyFingerprint: stored.keyFingerprint,
      identity: const EdgeIdentity(),
    ).timeout(const Duration(seconds: 10));

    final feedStore = MessageFeedStore(dir);
    await feedStore.load();
    final approvalStore = PendingApprovalStore(dir);

    var messageCount = 0;
    var approvalCount = 0;
    // wireMessageFeed's handler doesn't await onApproval's return value (it's
    // a void callback, fired synchronously from an async RPC handler), so the
    // actual disk write for each approval is tracked here and awaited before
    // this isolate tears down -- otherwise a write could be silently
    // abandoned mid-flight if iOS reclaims the process the instant the RPC
    // reply goes out.
    final pendingWrites = <Future<void>>[];

    wireMessageFeed(
      client,
      feedStore,
      onApproval: (params) {
        approvalCount++;
        pendingWrites.add(approvalStore.append(params));
      },
      onMessage: (message) {
        messageCount++;
        // 103/US4: a device heartbeat landing in this window must update the
        // same durable store the watch relay reads from -- otherwise a
        // heartbeat delivered while backgrounded would never reach the
        // watch until the next foreground launch happened to receive a
        // fresh one too.
        if (looksLikeDeviceHeartbeat(message)) {
          pendingWrites
              .add(DeviceHeartbeatStore(dir).save(DeviceHeartbeatStatus.fromMessage(message)));
        }
      },
    );

    // The Border settles for N2N_EDGE_REPLAY_SETTLE_S (3s default) after
    // accept before replaying a queue (BORDER-STATUS.md) -- this window
    // covers that plus margin for a message pushed live mid-window.
    await Future<void>.delayed(const Duration(seconds: 5));
    await Future.wait(pendingWrites);
    await client.close();

    if (messageCount > 0 || approvalCount > 0) {
      final notifications = LocalNotifications();
      await notifications.initialize(onResponse: (_) {});
      await notifications.postFeedNotification(
        identifier: 'bg-refresh-${DateTime.now().toIso8601String()}',
        preview: summarizeBackgroundRefresh(messageCount, approvalCount),
        badgeCount: feedStore.unreadCount,
      );
    }
    await _finish(notified: messageCount > 0 || approvalCount > 0);
  } catch (e) {
    await _finish(notified: false, error: '$e');
  }
}

/// The single local-notification preview text for a background-refresh
/// window's findings (FR-013: "posts ONE local notification summarizing what
/// arrived", not one per item). Pure and public specifically so it's
/// unit-testable without a live `EdgeClient`.
String summarizeBackgroundRefresh(int messageCount, int approvalCount) {
  final parts = <String>[];
  if (messageCount > 0) {
    parts.add(messageCount == 1 ? '1 new message' : '$messageCount new messages');
  }
  if (approvalCount > 0) {
    parts.add(approvalCount == 1 ? '1 approval request' : '$approvalCount approval requests');
  }
  return parts.join(', ');
}

Future<void> _finish({required bool notified, String? error}) async {
  try {
    await _channel.invokeMethod<void>('done', {
      'success': error == null,
      'notified': notified,
      'error': ?error,
    });
  } catch (_) {
    // Nothing more to do if even the completion signal fails -- native's own
    // task.expirationHandler is the safety net that force-completes the OS
    // task regardless.
  }
}
