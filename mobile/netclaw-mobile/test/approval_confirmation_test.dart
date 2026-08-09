import 'package:flutter_test/flutter_test.dart';

import 'package:netclaw_mobile/ncfed/approval_client.dart';
import 'package:netclaw_mobile/ncfed/approval_confirmation.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';

/// 099/FR-015/FR-016 (Story 6 verification, research.md R1): this is the ONE
/// shared confirm-then-resolve path both the in-app Approve/Deny buttons and
/// the notification-action handler in `main.dart` route through
/// (`contracts/notification-actions.md`). `approvals_screen_test.dart`-style
/// coverage already exercises two of these paths through the UI
/// (`approval_client_test.dart`); this file exercises `confirmAndResolve`
/// itself directly, including the two paths nothing else covers yet: an
/// already-resolved reply, and `resolve()` throwing.
class _RecordingEdgeRpcSource implements EdgeRpcSource {
  final List<(String method, Map<String, dynamic> params)> calls = [];
  Map<String, dynamic> Function(Map<String, dynamic> params)? onCall;

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return onCall?.call(params) ?? {'approval_id': params['approval_id'], 'resolved': true};
  }
}

void main() {
  ApprovalClient seededClient(_RecordingEdgeRpcSource source, {int approvalId = 42}) {
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

  test('successful authentication resolves the approval', () async {
    final source = _RecordingEdgeRpcSource();
    final client = seededClient(source);

    final message = await confirmAndResolve(
      client: client,
      approvalId: 42,
      targetName: 'reboot-router',
      action: 'approve',
      authenticate: (reason) async => true,
    );

    expect(message, isNull);
    expect(source.calls, hasLength(1));
    expect(source.calls.single.$2['action'], 'approve');
    expect(client.currentPending, isEmpty);
  });

  test('cancelled/failed authentication never calls resolve()', () async {
    final source = _RecordingEdgeRpcSource();
    final client = seededClient(source);

    final message = await confirmAndResolve(
      client: client,
      approvalId: 42,
      targetName: 'reboot-router',
      action: 'deny',
      authenticate: (reason) async => false,
    );

    expect(message, isNull);
    expect(source.calls, isEmpty);
    expect(client.currentPending, hasLength(1)); // still pending -- nothing resolved
  });

  test('an authenticate() that throws is treated as a failed attempt, never calls resolve()',
      () async {
    final source = _RecordingEdgeRpcSource();
    final client = seededClient(source);

    final message = await confirmAndResolve(
      client: client,
      approvalId: 42,
      targetName: 'reboot-router',
      action: 'approve',
      authenticate: (reason) async => throw StateError('biometry unavailable'),
    );

    expect(message, isNull);
    expect(source.calls, isEmpty);
  });

  test('an already-resolved reply from the Border surfaces as a message, not a silent no-op',
      () async {
    final source = _RecordingEdgeRpcSource()
      ..onCall = (params) => {'approval_id': params['approval_id'], 'already_resolved': true};
    final client = seededClient(source);

    final message = await confirmAndResolve(
      client: client,
      approvalId: 42,
      targetName: 'reboot-router',
      action: 'approve',
      authenticate: (reason) async => true,
    );

    expect(message, 'Already resolved');
    expect(source.calls, hasLength(1)); // the call IS made -- the Border decides "already"
  });

  test('resolve() throwing surfaces as a message rather than an unhandled error', () async {
    final source = _RecordingEdgeRpcSource()
      ..onCall = (params) => throw EdgeClientException('timeout', 'no reply');
    final client = seededClient(source);

    final message = await confirmAndResolve(
      client: client,
      approvalId: 42,
      targetName: 'reboot-router',
      action: 'approve',
      authenticate: (reason) async => true,
    );

    expect(message, startsWith('Could not resolve:'));
  });

  test('passes the watch-relay confirmationMethod through untouched', () async {
    final source = _RecordingEdgeRpcSource();
    final client = seededClient(source);

    await confirmAndResolve(
      client: client,
      approvalId: 42,
      targetName: 'reboot-router',
      action: 'approve',
      confirmationMethod: 'watch_passcode',
      authenticate: (reason) async => true,
    );

    expect(source.calls.single.$2['confirmation_method'], 'watch_passcode');
  });
}
