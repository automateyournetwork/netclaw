import 'package:flutter/material.dart';

import '../ncfed/dashboard_data.dart';

/// At-a-glance federation status (099/FR-012) -- Border connection health,
/// this device's identity/enrollment status, and current unread/pending
/// counts, all from a snapshot the caller already assembled from existing
/// state (no data of its own, see `dashboard_data.dart`).
class DashboardScreen extends StatelessWidget {
  final DashboardSnapshot snapshot;

  /// 109/FR-017: navigates to Feed. Invoked when tapping "Unread" resolves
  /// to Feed (unread Feed messages exist, taking priority over unread Chat).
  final VoidCallback onOpenFeed;

  /// 109/FR-017: navigates to Chat. Invoked when tapping "Unread" resolves
  /// to Chat (no unread Feed messages, but unread Chat turns exist).
  final VoidCallback onOpenChat;

  /// 109/FR-018: navigates to Approvals. Always valid, unlike Unread —
  /// reviewing an empty Approvals tab is not an error.
  final VoidCallback onOpenApprovals;

  const DashboardScreen({
    super.key,
    required this.snapshot,
    required this.onOpenFeed,
    required this.onOpenChat,
    required this.onOpenApprovals,
  });

  @override
  Widget build(BuildContext context) {
    final identity = snapshot.identity;
    final harness = snapshot.border['harness'] as Map?;
    final type = harness?['type'] is String ? harness!['type'] as String : 'unknown';
    final version = harness?['version'] is String ? harness!['version'] as String : 'unknown';
    final model = snapshot.border['model'];
    final capabilities = snapshot.border['capabilities'] as Map?;


    if (!identity.enrolled) {
      // FR-013/Edge Cases: a clear "not yet enrolled" state, never a blank
      // or errored pane.
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.link_off, size: 48),
              SizedBox(height: 12),
              Text('Not yet enrolled', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Text(
                'Scan your Border\'s QR code to connect this device.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return ListView(
      children: [
        ListTile(
          // FR-013: a genuinely stale/disconnected state is never presented
          // as current -- this is the live `_connected` flag, not a cached
          // "last known good" value.
          leading: Icon(
            snapshot.connected ? Icons.check_circle : Icons.error_outline,
            color: snapshot.connected ? Colors.green : Colors.orange,
          ),
          title: Text(snapshot.connected ? 'Connected to Border' : 'Reconnecting…'),
          subtitle: Text(identity.clawDomain),
        ),
        ListTile(
          leading: const Icon(Icons.memory),
          title: Text('Border type: $type'),
          subtitle: Text('Harness version: $version\nModel: ${model is String && model.isNotEmpty ? model : 'unknown'}${snapshot.connected ? '' : '\nLast received; reconnecting'}'),
        ),
        if (capabilities != null)
          ListTile(
            leading: const Icon(Icons.chat_outlined),
            title: const Text('Ask Border capabilities'),
            subtitle: Text('Text: ${capabilities['text'] == true ? 'available' : 'unknown'} • Voice text: ${capabilities['voice_text'] == true ? 'available' : 'unknown'}\nPhoto/video: ${capabilities['attachments'] == false ? 'unavailable' : capabilities['attachments'] == true ? 'available' : 'unknown'}'),
          ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.badge_outlined),
          title: const Text('Device identity'),
          subtitle: Text(identity.memberId),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.mark_email_unread_outlined),
          title: const Text('Unread'),
          trailing: Text('${snapshot.unreadPending.totalUnread}'),
          // 109/FR-017: Feed takes priority when both have unread items,
          // consistent with the bottom-navigation Feed badge being the
          // app's one pre-existing "go to unread" affordance. Zero unread
          // anywhere -- nothing to navigate to, no-op.
          onTap: snapshot.unreadPending.unreadFeed > 0
              ? onOpenFeed
              : (snapshot.unreadPending.unreadChat > 0 ? onOpenChat : null),
        ),
        ListTile(
          leading: const Icon(Icons.verified_user_outlined),
          title: const Text('Pending approvals'),
          trailing: Text('${snapshot.unreadPending.pendingApprovals}'),
          // 109/FR-018: always a valid destination, unlike Unread above.
          onTap: onOpenApprovals,
        ),
      ],
    );
  }
}
