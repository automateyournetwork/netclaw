import 'dart:async';

import 'edge_client.dart';

/// A pending approval pushed from the Border (feature 068, US1) — arrives
/// as an `n2n/edge/message` with `content_type='approval'` (research D5),
/// dispatched here by `wireMessageFeed`'s `onApproval` callback, never by
/// registering a second handler on the same method.
class PendingApproval {
  final int approvalId;
  final String targetType;
  final String targetName;
  final String requestingAgent;
  final String? riskName;
  final DateTime pushedAt;

  const PendingApproval({
    required this.approvalId,
    required this.targetType,
    required this.targetName,
    required this.requestingAgent,
    this.riskName,
    required this.pushedAt,
  });

  factory PendingApproval.fromWire(Map<String, dynamic> params) => PendingApproval(
        approvalId: params['approval_id'] as int,
        targetType: params['target_type'] as String? ?? '',
        targetName: params['target_name'] as String? ?? '',
        requestingAgent: params['requesting_agent'] as String? ?? '',
        riskName: params['risk_name'] as String?,
        pushedAt:
            DateTime.tryParse(params['pushed_at'] as String? ?? '') ?? DateTime.now().toUtc(),
      );
}

/// Tracks pending approvals and resolves them via `n2n/edge/approval_resolve`
/// (feature 068, US1). This class has NO biometric code of its own and never
/// imports `EdgeIdentity` — biometric gating lives entirely in
/// `approvals_screen.dart`'s UI layer, which MUST call `local_auth.authenticate()`
/// and only call `resolve()` on success (research D7/FR-002/FR-003: this
/// class trusts its caller to have already gated the decision; it enforces
/// nothing about HOW resolve() came to be called).
class ApprovalClient {
  final EdgeRpcSource client;
  final _pending = <int, PendingApproval>{};
  final _updates = StreamController<List<PendingApproval>>.broadcast();

  ApprovalClient(this.client);

  Stream<List<PendingApproval>> get pending => _updates.stream;
  List<PendingApproval> get currentPending => List.unmodifiable(_pending.values);

  /// Called by `wireMessageFeed`'s `onApproval` callback — NOT registered
  /// directly on the edge connection (avoids clobbering the message-feed
  /// handler on the same wire method).
  void receiveApproval(Map<String, dynamic> params) {
    final approval = PendingApproval.fromWire(params);
    _pending[approval.approvalId] = approval;
    _updates.add(currentPending);
  }

  /// Resolves an approval. The caller MUST have already completed a
  /// successful confirmation step before calling this — there is no
  /// enforcement of that here (FR-002/FR-003; see `approval_confirmation.dart`
  /// for where that confirmation actually happens). [confirmationMethod]
  /// defaults to `"biometric"` (the existing phone path, via Face ID/Touch ID)
  /// and is omitted from the wire request in that case, so the phone's own
  /// call site produces byte-for-byte the same request it always has. The
  /// watch relay (feature 072) passes `"watch_passcode"` instead, since no
  /// biometric sensor exists there (research D4) — the Border must never see
  /// a watch-confirmed approval mislabeled as biometric.
  ///
  /// Returns whether the Border reports this approval as already resolved
  /// by something else (073/FR-005, research D6) — `false` on a normal,
  /// first-time resolution.
  Future<bool> resolve(int approvalId, String action,
      {String confirmationMethod = 'biometric'}) async {
    final reply = await client.call('n2n/edge/approval_resolve', {
      'approval_id': approvalId,
      'action': action,
      if (confirmationMethod != 'biometric') 'confirmation_method': confirmationMethod,
    });
    _pending.remove(approvalId);
    _updates.add(currentPending);
    return reply['already_resolved'] as bool? ?? false;
  }

  void dispose() {
    _updates.close();
  }
}
