import 'package:local_auth/local_auth.dart';

import 'approval_client.dart';

/// The one shared "confirm, then resolve" path for approvals — used by
/// `approvals_screen.dart`'s in-app Approve/Deny buttons AND the notification
/// action handler wired in `main.dart` (073/FR-004, research D2). Both MUST
/// route through here rather than calling `ApprovalClient.resolve()`
/// directly, so a notification-banner tap is a second *entry point* into the
/// exact same fresh, never-cached authentication check — never a weaker or
/// separate one. This is the app's one place biometric code (`local_auth`)
/// exists, superseding the narrower claim in `approvals_screen.dart`'s
/// original comment that it alone held that role.
///
/// Returns `null` on success. Returns a short, user-displayable message when
/// nothing happened: authentication was cancelled/failed (never sent to the
/// Border at all, FR-003/FR-004), the approval was already resolved
/// elsewhere (FR-005), or the resolve call itself failed.
Future<String?> confirmAndResolve({
  required ApprovalClient client,
  required int approvalId,
  required String targetName,
  required String action,
  String confirmationMethod = 'biometric',
  Future<bool> Function(String reason)? authenticate,
}) async {
  final reason = action == 'approve'
      ? 'Confirm approval of $targetName'
      : 'Confirm denial of $targetName';
  final auth =
      authenticate ?? (String r) => LocalAuthentication().authenticate(localizedReason: r);
  final bool authenticated;
  try {
    authenticated = await auth(reason);
  } catch (_) {
    return null; // unavailable/errored -- send nothing, same as a failed attempt (FR-003/FR-004)
  }
  if (!authenticated) return null; // cancelled/failed -- send nothing (FR-003/FR-004)
  try {
    final alreadyResolved =
        await client.resolve(approvalId, action, confirmationMethod: confirmationMethod);
    return alreadyResolved ? 'Already resolved' : null;
  } catch (e) {
    return 'Could not resolve: $e';
  }
}
