import 'dart:convert';
import 'dart:io';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/ncfed/approval_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/local_notifications.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/ncfed/notification_deep_link.dart';

/// 099/FR-014/015/016 (Story 6 verification): `handleNotificationResponse`
/// (extracted from `main.dart`'s `_handleNotificationResponse`, which never
/// touched instance state, so pulling it out cost nothing) is the routing
/// this app relies on for every notification-action tap. This pins the
/// contract in `contracts/notification-actions.md`: an approve/deny action
/// routes through `confirmAndResolve` (never `ApprovalClient.resolve()`
/// directly -- `approval_confirmation_test.dart` covers that function's own
/// behavior), and anything else falls through to the deep-link handler.
class _RecordingEdgeRpcSource implements EdgeRpcSource {
  final List<(String method, Map<String, dynamic> params)> calls = [];

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return {'approval_id': params['approval_id'], 'resolved': true};
  }
}

void main() {
  late Directory dir;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('notification_routing_test_');
  });
  tearDown(() => dir.delete(recursive: true));

  ApprovalClient seededApprovalClient(_RecordingEdgeRpcSource source, {int approvalId = 42}) {
    final client = ApprovalClient(source);
    client.receiveApproval({
      'approval_id': approvalId,
      'target_type': 'skill',
      'target_name': 'reboot-router',
      'requesting_agent': 'risk/netclaw-core',
      'pushed_at': '2026-07-23T14:00:00Z',
    });
    return client;
  }

  test('an approve action routes through confirmAndResolve and resolves on success', () async {
    final source = _RecordingEdgeRpcSource();
    final approvalClient = seededApprovalClient(source);
    final deepLink = NotificationDeepLink(store: MessageFeedStore(dir), openMessage: (_) {});

    final response = NotificationResponse(
      notificationResponseType: NotificationResponseType.selectedNotificationAction,
      actionId: approveActionId,
      payload: jsonEncode({'type': 'approval', 'identifier': '42'}),
    );

    await handleNotificationResponse(
      response,
      approvalClient: approvalClient,
      deepLink: deepLink,
      authenticate: (reason) async => true, // simulated successful Face ID
    );

    // Reaching the wire call at all only happens via confirmAndResolve's
    // authenticate-then-resolve path -- a wrong-routing fallthrough to
    // deepLink (which has no 'approval' case) would leave this empty too,
    // which is exactly what the injected authenticate() distinguishes.
    expect(source.calls, hasLength(1));
    expect(source.calls.single.$2['action'], 'approve');
    expect(approvalClient.currentPending, isEmpty);
  });

  test('an approve action with failed authentication never resolves', () async {
    final source = _RecordingEdgeRpcSource();
    final approvalClient = seededApprovalClient(source);
    final deepLink = NotificationDeepLink(store: MessageFeedStore(dir), openMessage: (_) {});

    final response = NotificationResponse(
      notificationResponseType: NotificationResponseType.selectedNotificationAction,
      actionId: approveActionId,
      payload: jsonEncode({'type': 'approval', 'identifier': '42'}),
    );

    await handleNotificationResponse(
      response,
      approvalClient: approvalClient,
      deepLink: deepLink,
      authenticate: (reason) async => false, // simulated cancelled/failed Face ID
    );

    expect(source.calls, isEmpty);
    expect(approvalClient.currentPending, hasLength(1));
  });

  test('a plain tap (no action id) falls through to the deep-link handler', () async {
    final source = _RecordingEdgeRpcSource();
    final approvalClient = seededApprovalClient(source);
    EdgeMessage? opened;
    final feedStore = MessageFeedStore(dir);
    await feedStore.append(EdgeMessage(
      contentType: MessageContentType.text,
      content: 'hello',
      designatedBy: 'agent',
      pushedAt: DateTime.utc(2026, 7, 23, 14),
    ));
    final deepLink = NotificationDeepLink(
      store: feedStore,
      openMessage: (m) => opened = m,
    );

    final response = NotificationResponse(
      notificationResponseType: NotificationResponseType.selectedNotification,
      payload: jsonEncode({'type': 'feed', 'identifier': '2026-07-23T14:00:00.000Z'}),
    );

    await handleNotificationResponse(response, approvalClient: approvalClient, deepLink: deepLink);

    expect(opened, isNotNull);
    expect(opened!.content, 'hello');
    expect(source.calls, isEmpty); // never touched the approval path
  });

  test('an approve/deny action with a missing identifier is a silent no-op', () async {
    final source = _RecordingEdgeRpcSource();
    final approvalClient = seededApprovalClient(source);
    final deepLink = NotificationDeepLink(store: MessageFeedStore(dir), openMessage: (_) {});

    final response = NotificationResponse(
      notificationResponseType: NotificationResponseType.selectedNotificationAction,
      actionId: approveActionId,
      payload: jsonEncode({'type': 'approval'}), // no identifier
    );

    await handleNotificationResponse(response, approvalClient: approvalClient, deepLink: deepLink);

    expect(source.calls, isEmpty);
    expect(approvalClient.currentPending, hasLength(1)); // untouched
  });
}
