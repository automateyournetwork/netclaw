import 'package:flutter/material.dart';

import '../ncfed/dashboard_data.dart';

/// At-a-glance federation status (099/FR-012) -- Border connection health,
/// this device's identity/enrollment status, and current unread/pending
/// counts, all from a snapshot the caller already assembled from existing
/// state (no data of its own, see `dashboard_data.dart`).
class DashboardScreen extends StatelessWidget {
  final DashboardSnapshot snapshot;

  const DashboardScreen({super.key, required this.snapshot});

  @override
  Widget build(BuildContext context) {
    final identity = snapshot.identity;

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
        ),
        ListTile(
          leading: const Icon(Icons.verified_user_outlined),
          title: const Text('Pending approvals'),
          trailing: Text('${snapshot.unreadPending.pendingApprovals}'),
        ),
      ],
    );
  }
}
