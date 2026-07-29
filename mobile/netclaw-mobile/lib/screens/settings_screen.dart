import 'package:flutter/material.dart';

import '../ncfed/capability_registration.dart';
import '../ncfed/push_registration.dart';

/// Human-readable explanation of why notifications are or aren't working.
/// Push failing is silent by design — the app is fully usable without it — so
/// without this the only symptom is notifications that never arrive.
({String title, String detail, IconData icon}) describePushStatus(
  PushStatus status,
) =>
    switch (status) {
      PushStatus.registered => (
          title: 'Notifications on',
          detail: 'Answers arrive even when the app is closed.',
          icon: Icons.notifications_active_outlined,
        ),
      PushStatus.notConfigured => (
          title: 'Notifications unavailable',
          detail: 'This build has no push configuration. '
              'Answers only arrive while the app is open.',
          icon: Icons.notifications_off_outlined,
        ),
      PushStatus.permissionDenied => (
          title: 'Notifications blocked',
          detail: 'You declined the notification permission. '
              'Turn it on in your device settings to be notified.',
          icon: Icons.notifications_paused_outlined,
        ),
      PushStatus.failed => (
          title: 'Notifications failed',
          detail: 'Push is configured but registration failed. '
              'Report this — it is a bug, not a setting.',
          icon: Icons.error_outline,
        ),
      PushStatus.unknown => (
          title: 'Notifications starting…',
          detail: 'Still registering.',
          icon: Icons.hourglass_empty,
        ),
    };

/// Per-type capture toggles (feature 068, US3/T019/FR-007a) — disabling a
/// type here means the Border can never even discover it as a possibility,
/// not merely have a request for it refused.
class SettingsScreen extends StatefulWidget {
  final CapabilityRegistration capabilities;
  final PushStatus pushStatus;

  const SettingsScreen({
    super.key,
    required this.capabilities,
    this.pushStatus = PushStatus.unknown,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  static const _labels = {
    'camera.capture': 'Photo capture',
    'camera.record_video': 'Video capture',
    'audio.record': 'Audio recording',
  };

  String? _error;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        if (_error != null)
          Container(
            width: double.infinity,
            color: Colors.red.shade50,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Text(_error!, style: TextStyle(color: Colors.red.shade900)),
          ),
        for (final capability in kAllCaptureCapabilities)
          SwitchListTile(
            title: Text(_labels[capability] ?? capability),
            subtitle: const Text('The Border can request this while disconnected too'),
            value: widget.capabilities.enabled.contains(capability),
            onChanged: (value) async {
              setState(() => _error = null);
              try {
                await widget.capabilities.setEnabled(capability, value);
              } catch (e) {
                if (mounted) setState(() => _error = 'Could not update: $e');
              }
              if (mounted) setState(() {});
            },
          ),
        const Divider(),
        Builder(builder: (context) {
          final push = describePushStatus(widget.pushStatus);
          return ListTile(
            leading: Icon(push.icon),
            title: Text(push.title),
            subtitle: Text(push.detail),
          );
        }),
      ],
    );
  }
}
