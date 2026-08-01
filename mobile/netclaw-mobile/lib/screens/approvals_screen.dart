import 'package:flutter/material.dart';

import '../ncfed/approval_client.dart';
import '../ncfed/approval_confirmation.dart';
import 'empty_state.dart';

/// Pending approvals with biometric approve/deny (feature 068, US1/T010).
/// `n2n/edge/approval_resolve` is sent ONLY after `LocalAuthentication.
/// authenticate()` succeeds — a failed, cancelled, or unavailable biometric
/// attempt never calls `resolve()` at all (FR-002). The actual
/// confirm-then-resolve logic lives in `approval_confirmation.dart` (073),
/// shared with the notification action handler in `main.dart` — this screen
/// never imports `EdgeIdentity` or anything Keystore/Secure-Enclave-related
/// (research D7/FR-003).
class ApprovalsScreen extends StatefulWidget {
  final ApprovalClient approvalClient;
  final Future<bool> Function(String reason)? authenticate;

  const ApprovalsScreen({super.key, required this.approvalClient, this.authenticate});

  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  List<PendingApproval> _approvals = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _approvals = widget.approvalClient.currentPending;
    widget.approvalClient.pending.listen((list) {
      if (mounted) setState(() => _approvals = list);
    });
  }

  Future<void> _resolve(PendingApproval approval, String action) async {
    setState(() => _error = null);
    // The approval stays in `_approvals` either way if this reports an error
    // (ApprovalClient only removes it after a successful resolve) -- this
    // just makes a failed/already-resolved attempt visible instead of
    // looking identical to doing nothing.
    final error = await confirmAndResolve(
      client: widget.approvalClient,
      approvalId: approval.approvalId,
      targetName: approval.targetName,
      action: action,
      authenticate: widget.authenticate,
    );
    if (error != null && mounted) setState(() => _error = error);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (_error != null)
          Container(
            width: double.infinity,
            color: Colors.red.shade50,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Text(_error!, style: TextStyle(color: Colors.red.shade900)),
          ),
        Expanded(child: _body()),
      ],
    );
  }

  Widget _body() {
    if (_approvals.isEmpty) {
      return const EmptyState(
        asset: 'assets/illustrations/empty_approvals.png',
        text: 'No pending approvals.',
      );
    }
    return ListView.builder(
      itemCount: _approvals.length,
      itemBuilder: (context, index) {
        final approval = _approvals[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${approval.targetType}: ${approval.targetName}',
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text('Requested by ${approval.requestingAgent}'
                    '${approval.riskName != null ? " (${approval.riskName})" : ""}'),
                const SizedBox(height: 8),
                Row(
                  children: [
                    ElevatedButton(
                      onPressed: () => _resolve(approval, 'approve'),
                      child: const Text('Approve'),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton(
                      onPressed: () => _resolve(approval, 'deny'),
                      child: const Text('Deny'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
