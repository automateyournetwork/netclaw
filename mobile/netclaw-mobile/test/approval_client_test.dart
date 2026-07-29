import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/approval_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/screens/approvals_screen.dart';

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
  test('receiveApproval tracks a pushed approval and resolve() sends the wire call', () async {
    final source = _RecordingEdgeRpcSource();
    final client = ApprovalClient(source);
    client.receiveApproval({
      'approval_id': 42,
      'target_type': 'skill',
      'target_name': 'reboot-router',
      'requesting_agent': 'risk/netclaw-core',
      'risk_name': 'acme-ops',
      'pushed_at': '2026-07-23T14:00:00Z',
    });
    expect(client.currentPending, hasLength(1));

    await client.resolve(42, 'approve');

    expect(source.calls, hasLength(1));
    expect(source.calls.single.$1, 'n2n/edge/approval_resolve');
    expect(source.calls.single.$2, {'approval_id': 42, 'action': 'approve'});
    expect(client.currentPending, isEmpty);
  });

  testWidgets(
      'a failed/cancelled biometric attempt never triggers n2n/edge/approval_resolve (T013/FR-002)',
      (tester) async {
    final source = _RecordingEdgeRpcSource();
    final client = ApprovalClient(source);
    client.receiveApproval({
      'approval_id': 42,
      'target_type': 'skill',
      'target_name': 'reboot-router',
      'requesting_agent': 'risk/netclaw-core',
      'pushed_at': '2026-07-23T14:00:00Z',
    });

    await tester.pumpWidget(MaterialApp(
      home: ApprovalsScreen(
        approvalClient: client,
        authenticate: (reason) async => false, // simulated failed/cancelled biometric
      ),
    ));
    await tester.pump();

    await tester.tap(find.text('Approve'));
    await tester.pump();

    expect(source.calls, isEmpty); // resolve() never called -- approval stays pending
    expect(client.currentPending, hasLength(1));
  });

  testWidgets('a successful biometric attempt resolves the approval (approve)', (tester) async {
    final source = _RecordingEdgeRpcSource();
    final client = ApprovalClient(source);
    client.receiveApproval({
      'approval_id': 42,
      'target_type': 'skill',
      'target_name': 'reboot-router',
      'requesting_agent': 'risk/netclaw-core',
      'pushed_at': '2026-07-23T14:00:00Z',
    });

    await tester.pumpWidget(MaterialApp(
      home: ApprovalsScreen(
        approvalClient: client,
        authenticate: (reason) async => true, // simulated successful biometric
      ),
    ));
    await tester.pump();

    await tester.tap(find.text('Approve'));
    await tester.pump();

    expect(source.calls, hasLength(1));
    expect(source.calls.single.$2['action'], 'approve');
  });
}
